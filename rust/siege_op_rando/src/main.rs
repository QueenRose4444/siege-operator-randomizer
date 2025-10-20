// This line hides the console window on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::{HashMap, HashSet};
use std::fs;
// This is needed for creating a windowless process on Windows
#[cfg(windows)]
use std::os::windows::process::CommandExt;

use eframe::{
    egui::{self, Color32, RichText, TextureFilter, TextureOptions, Ui},
    emath::Align2,
    epaint::{Pos2, Vec2},
};
use global_hotkey::{
    hotkey::{Code, HotKey, Modifiers},
    GlobalHotKeyEvent, GlobalHotKeyManager,
};
use poll_promise::Promise;
use rand::{seq::SliceRandom, thread_rng};
use rust_embed::Embed;

// --- Compile-Time Constants ---
const VERSION: &str = env!("CARGO_PKG_VERSION");
const GITHUB_REPO_URL: &str = "https://github.com/QueenRose4444/siege-operator-randomizer";

// --- Asset Bundling ---
#[derive(Embed)]
#[folder = "assets/"]
struct Asset;

// --- GitHub Updater Data Structures ---
#[derive(serde::Deserialize, Debug, Clone)]
struct GitHubReleaseAsset {
    name: String,
    browser_download_url: String,
}

#[derive(serde::Deserialize, Debug, Clone)]
struct GitHubRelease {
    tag_name: String,
    name: String,
    body: Option<String>,
    html_url: String,
    assets: Vec<GitHubReleaseAsset>,
}

#[derive(Debug, Clone)]
enum UpdateStatus {
    Idle,
    Checking,
    UpdateAvailable {
        version: String,
        download_url: String,
        changelog: Option<String>,
        release_url: String,
        release_name: String,
        asset_name: String,
    },
    Downloading {
        progress: f32,
    },
    #[allow(dead_code)]
    Installing,
    UpToDate,
    Error(String),
}

// --- Operator Data Structures ---
#[derive(serde::Deserialize)]
struct OperatorData {
    #[serde(rename = "ATTACKERS")]
    attackers: Vec<String>,
    #[serde(rename = "DEFENDERS")]
    defenders: Vec<String>,
}

// --- App Settings ---
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
struct AppSettings {
    hotkeys: HashMap<HotkeyAction, [Option<HotKey>; 2]>,
    just_generate_count: usize,
    just_generate_backup: bool,
    disabled_operators: HashSet<String>,
    allow_insufficient_ops: bool,
}

impl Default for AppSettings {
    fn default() -> Self {
        let mut hotkeys = HashMap::new();
        hotkeys.insert(
            HotkeyAction::Generate,
            [Some(HotKey::new(None, Code::Home)), None],
        );
        Self {
            hotkeys,
            just_generate_count: 1,
            just_generate_backup: false,
            disabled_operators: HashSet::new(),
            allow_insufficient_ops: false,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct RecordingState {
    action: HotkeyAction,
    slot: usize,
}

// --- Main Application State ---
struct R6OperatorRandomizerApp {
    attackers: Vec<String>,
    defenders: Vec<String>,
    generated_rounds: (Vec<String>, Vec<String>),
    generated_backups: (Vec<String>, Vec<String>),
    textures: HashMap<String, egui::TextureHandle>,
    disable_window_open: bool,
    settings_window_open: bool,
    update_window_open: bool,
    active_disable_tab: OperatorType,
    last_mode: Option<GameMode>,
    status_message: String,
    update_status: UpdateStatus,
    update_promise: Option<Promise<Result<UpdateCheckResult, String>>>,
    clipboard: arboard::Clipboard,
    settings: AppSettings,
    hotkey_manager: GlobalHotKeyManager,
    hotkey_receiver: crossbeam_channel::Receiver<GlobalHotKeyEvent>,
    recording_hotkey_for: Option<RecordingState>,
    hotkey_id_map: HashMap<u32, HotkeyAction>,
}

#[derive(Debug, Clone)]
struct UpdateCheckResult {
    current_version: String,
    latest_version: String,
    download_url: String,
    is_newer: bool,
    changelog: Option<String>,
    release_url: String,
    release_name: String,
    asset_name: String,
}

impl R6OperatorRandomizerApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let settings: AppSettings = if let Some(storage) = cc.storage {
            eframe::get_value(storage, eframe::APP_KEY).unwrap_or_default()
        } else {
            Default::default()
        };

        let (attackers, defenders) = load_operators();
        let hotkey_manager = GlobalHotKeyManager::new().expect("Failed to create hotkey manager");
        let receiver = GlobalHotKeyEvent::receiver();
        let mut hotkey_id_map = HashMap::new();

        for (action, slots) in &settings.hotkeys {
            for hotkey in slots.iter().flatten() {
                if let Err(e) = hotkey_manager.register(*hotkey) {
                    eprintln!("Failed to register loaded hotkey for {:?}: {}", action, e);
                }
                hotkey_id_map.insert(hotkey.id(), *action);
            }
        }

        Self {
            attackers,
            defenders,
            generated_rounds: (Vec::new(), Vec::new()),
            generated_backups: (Vec::new(), Vec::new()),
            textures: HashMap::new(),
            disable_window_open: false,
            settings_window_open: false,
            update_window_open: false,
            active_disable_tab: OperatorType::Attacker,
            last_mode: None,
            status_message: "".to_string(),
            update_status: UpdateStatus::Idle,
            update_promise: None,
            clipboard: arboard::Clipboard::new().expect("Failed to initialize clipboard"),
            settings,
            hotkey_manager,
            hotkey_receiver: receiver.clone(),
            recording_hotkey_for: None,
            hotkey_id_map,
        }
    }
}

// --- Enums for Clarity ---
#[derive(Clone, Copy, PartialEq, Debug)]
enum GameMode {
    Ranked,
    Unranked,
    Quick,
    JustGenerate,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
enum HotkeyAction {
    Generate,
    GenerateBackup,
    Ranked,
    Unranked,
    Quick,
    JustGenerate,
}

#[derive(Clone, Copy, PartialEq)]
enum OperatorType {
    Attacker,
    Defender,
}

impl GameMode {
    fn round_count(&self, settings: &AppSettings) -> usize {
        match self {
            GameMode::Ranked | GameMode::Unranked => 9,
            GameMode::Quick => 5,
            GameMode::JustGenerate => settings.just_generate_count,
        }
    }
}

// --- Core Application Logic ---
impl eframe::App for R6OperatorRandomizerApp {
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(storage, eframe::APP_KEY, &self.settings);
    }

    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        if self.textures.is_empty() {
            self.load_all_textures(ctx);
        }

        // Check for update promise completion
        if let Some(promise) = &self.update_promise {
            if let Some(result) = promise.ready() {
                match result {
                    Ok(check_result) => {
                        if check_result.is_newer {
                            self.update_status = UpdateStatus::UpdateAvailable {
                                version: check_result.latest_version.clone(),
                                download_url: check_result.download_url.clone(),
                                changelog: check_result.changelog.clone(),
                                release_url: check_result.release_url.clone(),
                                release_name: check_result.release_name.clone(),
                                asset_name: check_result.asset_name.clone(),
                            };
                            // Show the update pop-up instead of auto-downloading
                            self.update_window_open = true;
                        } else {
                            self.update_status = UpdateStatus::UpToDate;
                            self.status_message = format!(
                                "You're up to date! Current: v{}, Latest: v{}",
                                check_result.current_version, check_result.latest_version
                            );
                        }
                    }
                    Err(e) => {
                        self.update_status = UpdateStatus::Error(e.clone());
                        self.status_message = format!("Update check failed: {}", e);
                    }
                }
                self.update_promise = None;
            }
        }

        if let Ok(event) = self.hotkey_receiver.try_recv() {
            if event.state == global_hotkey::HotKeyState::Pressed {
                if let Some(action) = self.hotkey_id_map.get(&event.id) {
                    match action {
                        HotkeyAction::Generate => {
                            if let Some(mode) = self.last_mode {
                                self.generate_new_set(mode);
                            }
                        }
                        HotkeyAction::GenerateBackup => self.generate_new_backups(),
                        HotkeyAction::Ranked => self.generate_new_set(GameMode::Ranked),
                        HotkeyAction::Unranked => self.generate_new_set(GameMode::Unranked),
                        HotkeyAction::Quick => self.generate_new_set(GameMode::Quick),
                        HotkeyAction::JustGenerate => self.generate_new_set(GameMode::JustGenerate),
                    }
                }
            }
        }
        ctx.request_repaint();

        // --- Main Window ---
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("R6 Operator Randomizer");
            ui.separator();

            self.ui_operator_display(ui, "Round", &self.generated_rounds);
            ui.add_space(10.0);

            ui.vertical_centered(|ui| {
                ui.horizontal(|ui| {
                    if ui.button("Ranked").clicked() { self.generate_new_set(GameMode::Ranked); }
                    if ui.button("Unranked").clicked() { self.generate_new_set(GameMode::Unranked); }
                    if ui.button("Quick").clicked() { self.generate_new_set(GameMode::Quick); }
                    if ui.button("Just Generate").clicked() { self.generate_new_set(GameMode::JustGenerate); }
                });
            });
            ui.separator();

            if !self.generated_backups.0.is_empty() {
                self.ui_operator_display(ui, "Backup", &self.generated_backups);
                ui.separator();
            }

            ui.horizontal(|ui| {
                if ui.button("📋 Copy").clicked() { self.copy_to_clipboard(); }
                if ui.button("🔄 Generate Backup").clicked() { self.generate_new_backups(); }
                if ui.button("🚫 Disable Ops").clicked() { self.disable_window_open = true; }
                if ui.button("⚙ Settings").clicked() { self.settings_window_open = true; }
                self.ui_update_button(ui);
            });

            // Show update status
            self.ui_update_status(ui);

            if !self.status_message.is_empty() {
                ui.label(RichText::new(&self.status_message).color(Color32::from_rgb(255, 165, 0)));
            }
        });

        // --- Child Windows ---
        self.show_disable_window(ctx);
        self.show_settings_window(ctx);
        self.show_update_window(ctx);
    }
}

// --- UI Rendering Methods ---
impl R6OperatorRandomizerApp {
    fn ui_update_status(&self, ui: &mut Ui) {
        match &self.update_status {
            UpdateStatus::Checking => {
                ui.label(RichText::new("🔍 Checking for updates...").color(Color32::LIGHT_BLUE));
            }
            UpdateStatus::Downloading { progress } => {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("⬇ Downloading update...").color(Color32::LIGHT_GREEN));
                    ui.add(egui::ProgressBar::new(*progress).show_percentage());
                });
            }
            UpdateStatus::Installing => {
                ui.label(RichText::new("⚙ Installing update...").color(Color32::LIGHT_GREEN));
            }
            UpdateStatus::Error(e) => {
                ui.label(RichText::new(format!("❌ Error: {}", e)).color(Color32::RED));
            }
            _ => {}
        }
    }

    fn ui_operator_display(&self, ui: &mut Ui, title_prefix: &str, data: &(Vec<String>, Vec<String>)) {
        let (attackers, defenders) = data;
        if attackers.is_empty() { return; }

        egui::Grid::new(title_prefix.to_lowercase() + "_grid")
            .striped(true)
            .spacing([10.0, 10.0])
            .show(ui, |ui| {
                ui.label("");
                for i in 0..attackers.len() {
                    ui.vertical_centered(|ui| {
                        ui.label(RichText::new(format!("{} {}", title_prefix, i + 1)).strong());
                    });
                }
                ui.end_row();

                ui.label(RichText::new("Attacker").color(Color32::LIGHT_RED).strong());
                for op_name in attackers { self.ui_operator_icon(ui, op_name); }
                ui.end_row();

                ui.label(RichText::new("Defender").color(Color32::LIGHT_BLUE).strong());
                for op_name in defenders { self.ui_operator_icon(ui, op_name); }
                ui.end_row();
            });
    }

    fn ui_operator_icon(&self, ui: &mut Ui, op_name: &str) {
        ui.vertical_centered(|ui| {
            ui.set_max_width(75.0);
            if let Some(texture) = self.textures.get(op_name) {
                ui.image((texture.id(), Vec2::new(64.0, 64.0)));
            } else {
                ui.label("?");
            }
            ui.label(op_name);
        });
    }
    
    fn ui_disable_window(&mut self, ui: &mut Ui) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.active_disable_tab, OperatorType::Attacker, "Attackers");
            ui.selectable_value(&mut self.active_disable_tab, OperatorType::Defender, "Defenders");
            ui.separator();
            self.ui_op_counter(ui);
        });
        ui.separator();

        let operators_to_display = match self.active_disable_tab {
            OperatorType::Attacker => self.attackers.clone(),
            OperatorType::Defender => self.defenders.clone(),
        };
        
        const MAX_COLS: usize = 10;
        egui::ScrollArea::vertical().show(ui, |ui| {
            egui::Grid::new("disable_op_grid")
                .spacing([10.0, 10.0])
                .show(ui, |ui| {
                    for (i, op_name) in operators_to_display.iter().enumerate() {
                        let is_disabled = self.settings.disabled_operators.contains(op_name);
                        if self.ui_disable_icon(ui, op_name, is_disabled).clicked() {
                            if is_disabled { self.settings.disabled_operators.remove(op_name); } 
                            else { self.settings.disabled_operators.insert(op_name.clone()); }
                        }

                        if (i + 1) % MAX_COLS == 0 {
                            ui.end_row();
                        }
                    }
                });
        });

        ui.separator();
        ui.horizontal(|ui| {
             if ui.button("Reset Page").clicked() {
                let ops_to_reset = match self.active_disable_tab {
                    OperatorType::Attacker => self.attackers.clone(),
                    OperatorType::Defender => self.defenders.clone(),
                };
                for op in ops_to_reset { self.settings.disabled_operators.remove(&op); }
            }
            ui.checkbox(&mut self.settings.allow_insufficient_ops, "Allow insufficient operators");
        });
    }
    
    fn ui_settings_window(&mut self, ui: &mut Ui) {
        ui.heading("Settings");
        ui.separator();
        
        egui::Grid::new("settings_grid").num_columns(2).spacing([40.0, 4.0]).show(ui, |ui| {
            ui.label("Just Generate Count:");
            ui.add(egui::DragValue::new(&mut self.settings.just_generate_count).clamp_range(1..=9));
            ui.end_row();

            ui.label("Just Generate Backup:");
            ui.checkbox(&mut self.settings.just_generate_backup, "");
            ui.end_row();
        });
        
        ui.separator();
        ui.heading("Hotkeys");
        ui.label("Click a button to set a new hotkey. Press Escape to cancel.");
        
        egui::Grid::new("hotkeys_grid")
            .num_columns(3)
            .spacing([20.0, 8.0])
            .striped(true)
            .show(ui, |ui| {
                ui.label("");
                ui.vertical_centered(|ui| { ui.strong("Primary"); });
                ui.vertical_centered(|ui| { ui.strong("Secondary"); });
                ui.end_row();

                self.ui_hotkey_row(ui, HotkeyAction::Generate, "Generate Last Mode");
                self.ui_hotkey_row(ui, HotkeyAction::GenerateBackup, "Generate Backups");
                self.ui_hotkey_row(ui, HotkeyAction::Ranked, "Generate Ranked");
                self.ui_hotkey_row(ui, HotkeyAction::Unranked, "Generate Unranked");
                self.ui_hotkey_row(ui, HotkeyAction::Quick, "Generate Quick");
                self.ui_hotkey_row(ui, HotkeyAction::JustGenerate, "Generate 'Just Generate'");
            });

        ui.with_layout(egui::Layout::bottom_up(egui::Align::Center), |ui| {
            ui.horizontal(|ui| {
                ui.label(format!("v{}", VERSION));
                ui.hyperlink_to("GitHub repo", GITHUB_REPO_URL);
            });
        });
    }

    fn ui_update_window(&mut self, ui: &mut Ui) {
        if let UpdateStatus::UpdateAvailable { version, changelog, release_url, release_name, .. } = self.update_status.clone() {
            ui.heading(release_name);
            ui.add_space(5.0);
            ui.label(format!("Version {} is ready to install!", version));
            ui.separator();
    
            ui.label(RichText::new("Changelog:").strong());
            egui::ScrollArea::vertical()
                .max_height(180.0)
                .show(ui, |ui| {
                    ui.label(changelog.unwrap_or_else(|| "No changelog provided.".to_string()));
            });
    
            ui.with_layout(egui::Layout::bottom_up(egui::Align::Center), |ui| {
                 ui.horizontal(|ui| {
                    if ui.button("Open Download Page").clicked() {
                        if let Err(e) = open::that(&release_url) {
                            self.status_message = format!("Failed to open browser: {}", e);
                        }
                        self.update_window_open = false;
                    }
                    
                    if ui.button("Auto-Update & Restart").clicked() {
                        self.start_update_download();
                        self.update_window_open = false;
                    }
                });
            });
        }
    }

    fn ui_hotkey_row(&mut self, ui: &mut Ui, action: HotkeyAction, label: &str) {
        ui.label(label);
        self.ui_single_hotkey_cell(ui, action, 0);
        self.ui_single_hotkey_cell(ui, action, 1);
        ui.end_row();
    }

    fn ui_single_hotkey_cell(&mut self, ui: &mut Ui, action: HotkeyAction, slot: usize) {
        ui.horizontal(|ui| {
            let hotkey_slot = self.settings.hotkeys.get(&action).and_then(|slots| slots[slot]);
            let is_recording = self.recording_hotkey_for == Some(RecordingState { action, slot });

            let button_text = if is_recording {
                "Press any key...".to_string()
            } else if let Some(hk) = hotkey_slot {
                format_hotkey(hk)
            } else {
                "Not Set".to_string()
            };
    
            let set_button = egui::Button::new(button_text).min_size(Vec2::new(120.0, 0.0));

            if ui.add(set_button).on_hover_text(format!("Slot {}", slot + 1)).clicked() {
                self.recording_hotkey_for = Some(RecordingState { action, slot });
            }
    
            if ui.button("Clear").clicked() {
                if let Some(old_hotkey) = self.settings.hotkeys.entry(action).or_default()[slot].take() {
                    let _ = self.hotkey_manager.unregister(old_hotkey);
                    self.rebuild_hotkey_id_map();
                    self.status_message = format!("Hotkey for {:?} (Slot {}) cleared.", action, slot + 1);
                }
                if is_recording {
                    self.recording_hotkey_for = None;
                }
            }
        });
    }

    fn ui_op_counter(&self, ui: &mut Ui) {
        let (total, role_name) = match self.active_disable_tab {
            OperatorType::Attacker => (self.attackers.len(), "Attackers"),
            OperatorType::Defender => (self.defenders.len(), "Defenders"),
        };
        let enabled_count = total - self.settings.disabled_operators
            .iter()
            .filter(|op| {
                (self.active_disable_tab == OperatorType::Attacker && self.attackers.contains(op)) ||
                (self.active_disable_tab == OperatorType::Defender && self.defenders.contains(op))
            })
            .count();
        
        ui.label(format!("{}: {}/{}", role_name, enabled_count, total));
    
        let ranked_req = GameMode::Ranked.round_count(&self.settings);
        let ranked_color = if enabled_count >= ranked_req { Color32::WHITE } else { Color32::RED };
        ui.label(RichText::new(format!("Ranked/Unranked: {}/{}", enabled_count, ranked_req)).color(ranked_color));

        let quick_req = GameMode::Quick.round_count(&self.settings);
        let quick_color = if enabled_count >= quick_req { Color32::WHITE } else { Color32::RED };
        ui.label(RichText::new(format!("Quick: {}/{}", enabled_count, quick_req)).color(quick_color));
    }
    
    fn ui_disable_icon(&self, ui: &mut Ui, op_name: &str, is_disabled: bool) -> egui::Response {
        let desired_size = Vec2::new(75.0, 85.0);
        let (rect, response) = ui.allocate_exact_size(desired_size, egui::Sense::click());
        if ui.is_rect_visible(rect) {
            let tint = if is_disabled { Color32::from_gray(80) } else { Color32::WHITE };
            let visuals = ui.style().interact_selectable(&response, false);

            ui.painter().rect(rect, visuals.rounding, visuals.bg_fill, visuals.bg_stroke);

            if let Some(texture) = self.textures.get(op_name) {
                let image_rect = egui::Rect::from_center_size(rect.center() - Vec2::new(0.0, 5.0), Vec2::new(64.0, 64.0));
                ui.painter().image(texture.id(), image_rect, egui::Rect::from_min_max(Pos2::ZERO, Pos2::new(1.0, 1.0)), tint);
            }
            
            ui.painter().text(
                rect.center() + Vec2::new(0.0, 32.0),
                Align2::CENTER_CENTER,
                op_name,
                egui::FontId::proportional(14.0),
                if is_disabled { Color32::GRAY } else { visuals.fg_stroke.color },
            );
        }
        response
    }

    fn ui_update_button(&mut self, ui: &mut Ui) {
        let button_enabled = matches!(self.update_status, UpdateStatus::Idle | UpdateStatus::UpToDate | UpdateStatus::Error(_));
        let button_text = match &self.update_status {
            UpdateStatus::Checking => "Checking...",
            UpdateStatus::Downloading { .. } => "Downloading...",
            UpdateStatus::Installing => "Installing...",
            _ => "Check for Updates",
        };

        if ui.add_enabled(button_enabled, egui::Button::new(button_text)).clicked() {
            self.start_update_check();
        }
    }

    fn start_update_check(&mut self) {
        self.update_status = UpdateStatus::Checking;
        self.status_message = "Checking for updates...".to_owned();
        self.update_promise = Some(Promise::spawn_thread("update_checker", || {
            check_for_updates()
        }));
    }

    fn start_update_download(&mut self) {
        if let UpdateStatus::UpdateAvailable { version, download_url, asset_name, .. } = &self.update_status {
            self.status_message = format!("Downloading update v{}...", version);
            let download_url = download_url.clone();
            let version = version.clone();
            let asset_name = asset_name.clone();
            
            // Start download and installation in background
            std::thread::spawn(move || {
                if let Err(e) = download_and_install_update(&download_url, &version, &asset_name) {
                    eprintln!("Update failed: {}", e);
                }
            });
            
            self.update_status = UpdateStatus::Downloading { progress: 0.0 };
        }
    }
}

// --- Window Management ---
impl R6OperatorRandomizerApp {
    fn show_disable_window(&mut self, ctx: &egui::Context) {
        if self.disable_window_open {
            let mut is_open = self.disable_window_open;

            const ICON_WIDTH: f32 = 75.0;
            const GRID_SPACING_X: f32 = 10.0;
            const GRID_COLS: usize = 10;
            const HORIZONTAL_PADDING: f32 = 30.0;
            let calculated_width = (ICON_WIDTH * GRID_COLS as f32) 
                               + (GRID_SPACING_X * (GRID_COLS - 1) as f32) 
                               + HORIZONTAL_PADDING;

            const ICON_HEIGHT: f32 = 85.0;
            const GRID_SPACING_Y: f32 = 10.0;
            const TOP_BAR_HEIGHT: f32 = 50.0;
            const BOTTOM_BAR_HEIGHT: f32 = 50.0;
            
            let op_count = match self.active_disable_tab {
                OperatorType::Attacker => self.attackers.len(),
                OperatorType::Defender => self.defenders.len(),
            };
            let num_rows = (op_count + GRID_COLS - 1) / GRID_COLS;

            let grid_height = (ICON_HEIGHT * num_rows as f32) + (GRID_SPACING_Y * (num_rows.saturating_sub(1)) as f32);
            let calculated_height = (TOP_BAR_HEIGHT + grid_height + BOTTOM_BAR_HEIGHT).max(250.0);

            ctx.show_viewport_immediate(
                egui::ViewportId::from_hash_of("disable_ops_window"),
                egui::ViewportBuilder::default()
                    .with_title("Disable Operators")
                    .with_inner_size([calculated_width, calculated_height])
                    .with_resizable(false),
                |ctx, _class| {
                    egui::CentralPanel::default().show(ctx, |ui| { self.ui_disable_window(ui); });
                    if ctx.input(|i| i.viewport().close_requested()) { is_open = false; }
                },
            );
            self.disable_window_open = is_open;
        }
    }
    
    fn show_settings_window(&mut self, ctx: &egui::Context) {
        if self.settings_window_open {
            let mut is_open = self.settings_window_open;
            ctx.show_viewport_immediate(
                egui::ViewportId::from_hash_of("settings_window"),
                egui::ViewportBuilder::default()
                    .with_title("Settings")
                    .with_inner_size([550.0, 420.0]),
                |ctx, _class| {
                    self.listen_for_new_hotkey_assignment(ctx);

                    egui::CentralPanel::default().show(ctx, |ui| { self.ui_settings_window(ui); });
                    if ctx.input(|i| i.viewport().close_requested()) {
                        is_open = false;
                        self.recording_hotkey_for = None;
                    }
                },
            );
            self.settings_window_open = is_open;
        }
    }

    fn show_update_window(&mut self, ctx: &egui::Context) {
        if self.update_window_open {
            let mut is_open = self.update_window_open;
            ctx.show_viewport_immediate(
                egui::ViewportId::from_hash_of("update_window"),
                egui::ViewportBuilder::default()
                    .with_title("Update Available!")
                    .with_inner_size([450.0, 350.0]),
                |ctx, _class| {
                    egui::CentralPanel::default().show(ctx, |ui| { self.ui_update_window(ui); });
                    if ctx.input(|i| i.viewport().close_requested()) {
                        is_open = false;
                    }
                },
            );
            self.update_window_open = is_open;
        }
    }
}

// --- Helper Functions ---
impl R6OperatorRandomizerApp {
    fn generate_new_set(&mut self, mode: GameMode) {
        self.last_mode = Some(mode);
        self.status_message.clear();
        let round_count = mode.round_count(&self.settings);

        let enabled_attackers: Vec<_> = self.attackers.iter().filter(|op| !self.settings.disabled_operators.contains(*op)).cloned().collect();
        let enabled_defenders: Vec<_> = self.defenders.iter().filter(|op| !self.settings.disabled_operators.contains(*op)).cloned().collect();

        if enabled_attackers.is_empty() || enabled_defenders.is_empty() {
            self.status_message = "Not enough enabled attackers or defenders.".to_string();
            return;
        }

        if !self.settings.allow_insufficient_ops && (enabled_attackers.len() < round_count || enabled_defenders.len() < round_count) {
            self.status_message = format!("Not enough operators for mode '{:?}'", mode);
            return;
        }
        
        let mut rng = thread_rng();
        self.generated_rounds.0 = sample_or_choices(&enabled_attackers, round_count, &mut rng);
        self.generated_rounds.1 = sample_or_choices(&enabled_defenders, round_count, &mut rng);

        let should_backup = match mode {
            GameMode::JustGenerate => self.settings.just_generate_backup,
            _ => true,
        };

        if should_backup {
             self.generated_backups = (
                generate_backups(&self.generated_rounds.0, &enabled_attackers, round_count, &mut rng),
                generate_backups(&self.generated_rounds.1, &enabled_defenders, round_count, &mut rng)
            );
        } else {
            self.generated_backups = (Vec::new(), Vec::new());
        }
    }

    fn generate_new_backups(&mut self) {
        if self.last_mode.is_none() || self.generated_rounds.0.is_empty() {
            self.status_message = "Generate a set of operators first!".to_string();
            return;
        }

        let mode = self.last_mode.unwrap();
        let round_count = mode.round_count(&self.settings);

        let enabled_attackers: Vec<_> = self.attackers.iter().filter(|op| !self.settings.disabled_operators.contains(*op)).cloned().collect();
        let enabled_defenders: Vec<_> = self.defenders.iter().filter(|op| !self.settings.disabled_operators.contains(*op)).cloned().collect();

        if enabled_attackers.is_empty() || enabled_defenders.is_empty() {
            self.status_message = "Not enough enabled attackers or defenders to generate backups.".to_string();
            return;
        }

        let mut rng = thread_rng();
        self.generated_backups = (
            generate_backups(&self.generated_rounds.0, &enabled_attackers, round_count, &mut rng),
            generate_backups(&self.generated_rounds.1, &enabled_defenders, round_count, &mut rng)
        );
    }

    fn copy_to_clipboard(&mut self) {
        let mut output = String::new();
        if !self.generated_rounds.0.is_empty() {
            for i in 0..self.generated_rounds.0.len() {
                output += &format!("Round {}\nA={}\nD={}\n\n", i + 1, self.generated_rounds.0[i], self.generated_rounds.1[i]);
            }
        }
        if !self.generated_backups.0.is_empty() {
             output += &format!("Backup\nA={}\nD={}", self.generated_backups.0.join(", "), self.generated_backups.1.join(", "));
        }
        if !output.is_empty() {
            if self.clipboard.set_text(output.trim()).is_ok() { self.status_message = "Copied to clipboard!".to_string(); } 
            else { self.status_message = "Failed to copy to clipboard.".to_string(); }
        } else { self.status_message = "Nothing to copy.".to_string(); }
    }
    
    fn load_all_textures(&mut self, ctx: &egui::Context) {
        self.textures.clear();
        let all_ops = self.attackers.iter().chain(self.defenders.iter());
        for op_name in all_ops {
            let filename = format!("images/{} icon.png", op_name.to_uppercase());
            
            if let Some(file) = Asset::get(&filename) {
                if let Ok(image) = image::load_from_memory(file.data.as_ref()) {
                    let image = image.to_rgba8();
                    let size = [image.width() as _, image.height() as _];
                    let pixels = image.into_raw();
                    let color_image = egui::ColorImage::from_rgba_unmultiplied(size, &pixels);
                    let texture = ctx.load_texture(
                        op_name, color_image,
                        TextureOptions {
                            magnification: TextureFilter::Linear,
                            minification: TextureFilter::Linear,
                            wrap_mode: egui::TextureWrapMode::ClampToEdge,
                        },
                    );
                    self.textures.insert(op_name.clone(), texture);
                }
            }
        }
    }
    
    fn listen_for_new_hotkey_assignment(&mut self, ctx: &egui::Context) {
        if let Some(state) = self.recording_hotkey_for {
            ctx.input_mut(|i| {
                for event in i.events.iter() {
                    if let egui::Event::Key { key, pressed: true, modifiers, .. } = event {
                        if *key == egui::Key::Escape {
                            self.recording_hotkey_for = None;
                            self.status_message = "Hotkey assignment cancelled.".to_string();
                            i.consume_key(*modifiers, *key);
                            return;
                        }

                        if let Some(code) = map_egui_key_to_hotkey_code(*key) {
                            let ghk_mods = map_egui_mods_to_ghk_mods(*modifiers);
                            let new_hotkey = HotKey::new(Some(ghk_mods), code);

                            let slots = self.settings.hotkeys.entry(state.action).or_default();

                            if let Some(old_hotkey) = slots[state.slot].take() {
                                let _ = self.hotkey_manager.unregister(old_hotkey);
                            }

                            if self.hotkey_manager.register(new_hotkey).is_ok() {
                                slots[state.slot] = Some(new_hotkey);
                                self.rebuild_hotkey_id_map();
                                self.status_message = format!("Hotkey for {:?} set to {}", state.action, format_hotkey(new_hotkey));
                            } else {
                                self.status_message = format!("Failed to set hotkey {}. May be in use.", format_hotkey(new_hotkey));
                            }
                            self.recording_hotkey_for = None;
                            i.consume_key(*modifiers, *key);
                            return;
                        } else {
                            self.status_message = format!("{:?} is not a supported key for global hotkeys.", key);
                            self.recording_hotkey_for = None;
                            i.consume_key(*modifiers, *key);
                            return;
                        }
                    }
                }
            });
        }
    }
    
    fn rebuild_hotkey_id_map(&mut self) {
        self.hotkey_id_map.clear();
        for (action, slots) in &self.settings.hotkeys {
            for hotkey in slots.iter().flatten() {
                self.hotkey_id_map.insert(hotkey.id(), *action);
            }
        }
    }
}

fn map_egui_mods_to_ghk_mods(mods: egui::Modifiers) -> Modifiers {
    let mut ghk_mods = Modifiers::empty();
    if mods.alt { ghk_mods |= Modifiers::ALT; }
    if mods.ctrl { ghk_mods |= Modifiers::CONTROL; }
    if mods.shift { ghk_mods |= Modifiers::SHIFT; }
    if mods.mac_cmd { ghk_mods |= Modifiers::SUPER; }
    ghk_mods
}

fn format_hotkey(hotkey: HotKey) -> String {
    let mut parts = Vec::new();
    if hotkey.mods.contains(Modifiers::CONTROL) { parts.push("Ctrl"); }
    if hotkey.mods.contains(Modifiers::ALT) { parts.push("Alt"); }
    if hotkey.mods.contains(Modifiers::SHIFT) { parts.push("Shift"); }
    if hotkey.mods.contains(Modifiers::SUPER) { parts.push("Win"); }
    let key_name = format!("{:?}", hotkey.key);
    parts.push(&key_name);
    parts.join(" + ")
}

fn map_egui_key_to_hotkey_code(key: egui::Key) -> Option<Code> {
    use egui::Key;
    Some(match key {
        Key::F1 => Code::F1, Key::F2 => Code::F2, Key::F3 => Code::F3, Key::F4 => Code::F4,
        Key::F5 => Code::F5, Key::F6 => Code::F6, Key::F7 => Code::F7, Key::F8 => Code::F8,
        Key::F9 => Code::F9, Key::F10 => Code::F10, Key::F11 => Code::F11, Key::F12 => Code::F12,
        Key::Home => Code::Home, Key::End => Code::End, Key::Insert => Code::Insert,
        Key::Delete => Code::Delete, Key::PageUp => Code::PageUp, Key::PageDown => Code::PageDown,
        Key::ArrowLeft => Code::ArrowLeft, Key::ArrowRight => Code::ArrowRight, 
        Key::ArrowUp => Code::ArrowUp, Key::ArrowDown => Code::ArrowDown,
        Key::Backspace => Code::Backspace, Key::Enter => Code::Enter, Key::Tab => Code::Tab,
        Key::Num0 => Code::Digit0, Key::Num1 => Code::Digit1, Key::Num2 => Code::Digit2,
        Key::Num3 => Code::Digit3, Key::Num4 => Code::Digit4, Key::Num5 => Code::Digit5,
        Key::Num6 => Code::Digit6, Key::Num7 => Code::Digit7, Key::Num8 => Code::Digit8,
        Key::Num9 => Code::Digit9,
        Key::A => Code::KeyA, Key::B => Code::KeyB, Key::C => Code::KeyC, Key::D => Code::KeyD,
        Key::E => Code::KeyE, Key::F => Code::KeyF, Key::G => Code::KeyG, Key::H => Code::KeyH,
        Key::I => Code::KeyI, Key::J => Code::KeyJ, Key::K => Code::KeyK, Key::L => Code::KeyL,
        Key::M => Code::KeyM, Key::N => Code::KeyN, Key::O => Code::KeyO, Key::P => Code::KeyP,
        Key::Q => Code::KeyQ, Key::R => Code::KeyR, Key::S => Code::KeyS, Key::T => Code::KeyT,
        Key::U => Code::KeyU, Key::V => Code::KeyV, Key::W => Code::KeyW, Key::X => Code::KeyX,
        Key::Y => Code::KeyY, Key::Z => Code::KeyZ,
        _ => return None,
    })
}

fn load_operators() -> (Vec<String>, Vec<String>) {
    if let Some(file) = Asset::get("operators_list.json") {
        let data: OperatorData = serde_json::from_slice(&file.data).expect("Failed to parse operators_list.json");
        (data.attackers, data.defenders)
    } else { panic!("Could not find embedded operators_list.json"); }
}

fn sample_or_choices(pool: &[String], k: usize, rng: &mut impl rand::Rng) -> Vec<String> {
    if pool.len() >= k {
        pool.choose_multiple(rng, k).cloned().collect()
    } else {
        (0..k).map(|_| pool.choose(rng).unwrap().clone()).collect()
    }
}

fn generate_backups(main_selection: &[String], pool: &[String], k: usize, rng: &mut impl rand::Rng) -> Vec<String> {
    let main_set: HashSet<_> = main_selection.iter().cloned().collect();
    let available_for_backup: Vec<_> = pool.iter().filter(|op| !main_set.contains(*op)).cloned().collect();
    let mut backups = if available_for_backup.len() >= k {
        available_for_backup.choose_multiple(rng, k).cloned().collect()
    } else {
        let mut temp = available_for_backup;
        let needed = k - temp.len();
        temp.extend(main_selection.choose_multiple(rng, needed).cloned());
        temp
    };
    backups.shuffle(rng);
    backups
}

// --- Version Comparison Helper ---
fn parse_version(version_str: &str) -> Result<(u32, u32, u32), String> {
    // Remove 'v' prefix if present and clean the string
    let clean_version = version_str.trim().trim_start_matches('v').trim_start_matches('V');
    
    // Check if it's actually a semantic version format
    if !clean_version.chars().next().map_or(false, |c| c.is_ascii_digit()) {
        return Err(format!("Invalid version format: {} (must start with a number)", version_str));
    }
    
    let parts: Vec<&str> = clean_version.split('.').collect();
    if parts.len() != 3 {
        return Err(format!("Invalid version format: {} (must be in format X.Y.Z)", version_str));
    }
    
    let major = parts[0].parse::<u32>().map_err(|_| format!("Invalid major version: {}", parts[0]))?;
    let minor = parts[1].parse::<u32>().map_err(|_| format!("Invalid minor version: {}", parts[1]))?;
    let patch = parts[2].parse::<u32>().map_err(|_| format!("Invalid patch version: {}", parts[2]))?;
    
    Ok((major, minor, patch))
}

fn is_version_newer(current: &str, latest: &str) -> Result<bool, String> {
    let (c_major, c_minor, c_patch) = parse_version(current)?;
    let (l_major, l_minor, l_patch) = parse_version(latest)?;
    
    if l_major > c_major {
        return Ok(true);
    } else if l_major < c_major {
        return Ok(false);
    }
    
    if l_minor > c_minor {
        return Ok(true);
    } else if l_minor < c_minor {
        return Ok(false);
    }
    
    Ok(l_patch > c_patch)
}

// --- Update Check Function ---
fn check_for_updates() -> Result<UpdateCheckResult, String> {
    const REPO_URL: &str = "https://api.github.com/repos/QueenRose4444/siege-operator-randomizer/releases/latest";
    const ASSET_PREFIX: &str = "r6_op_rando";
    const ASSET_SUFFIX: &str = ".exe";
    
    let client = reqwest::blocking::Client::builder()
        .user_agent("r6-randomizer-rust-updater")
        .build()
        .map_err(|e| e.to_string())?;
    
    let release: GitHubRelease = client
        .get(REPO_URL)
        .send()
        .map_err(|e| format!("Failed to fetch release info: {}", e))?
        .json()
        .map_err(|e| format!("Failed to parse release JSON: {}", e))?;
    
    let asset = release.assets.iter()
        .find(|a| a.name.starts_with(ASSET_PREFIX) && a.name.ends_with(ASSET_SUFFIX))
        .ok_or_else(|| format!("Could not find a matching .exe asset in release {}", release.tag_name))?;
    
    let current_version = VERSION.to_string();
    let latest_version = release.tag_name.clone();
    
    // Try to compare versions, but handle invalid format gracefully
    let is_newer = match is_version_newer(&current_version, &latest_version) {
        Ok(newer) => newer,
        Err(e) => {
            // If version comparison fails, don't auto-update
            eprintln!("Version comparison failed: {}", e);
            return Err(format!(
                "Cannot compare versions. Current: v{}, Latest: {} - Please ensure GitHub release uses semantic versioning (e.g., v1.2.0)",
                current_version, latest_version
            ));
        }
    };
    
    Ok(UpdateCheckResult {
        current_version,
        latest_version,
        download_url: asset.browser_download_url.clone(),
        is_newer,
        changelog: release.body,
        release_url: release.html_url,
        release_name: release.name,
        asset_name: asset.name.clone(),
    })
}

// --- Download and Install Update ---
fn download_and_install_update(download_url: &str, version: &str, asset_name: &str) -> Result<(), String> {
    // Get current executable path
    let current_exe = std::env::current_exe()
        .map_err(|e| format!("Failed to get current exe path: {}", e))?;
    
    let exe_dir = current_exe.parent()
        .ok_or_else(|| "Failed to get exe directory".to_string())?;

    // The new executable path will use the name from the release asset
    let new_exe_path = exe_dir.join(asset_name);
    
    // Download the new version
    let client = reqwest::blocking::Client::builder()
        .user_agent("r6-randomizer-rust-updater")
        .build()
        .map_err(|e| e.to_string())?;
    
    let response = client.get(download_url)
        .send()
        .map_err(|e| format!("Failed to download update: {}", e))?;
    
    let bytes = response.bytes()
        .map_err(|e| format!("Failed to read update bytes: {}", e))?;
    
    // Save to temporary file
    let temp_path = exe_dir.join(format!("r6_op_rando_v{}_temp.exe", version));
    fs::write(&temp_path, bytes)
        .map_err(|e| format!("Failed to write temporary file: {}", e))?;
    
    // On Windows, we need a batch script to replace the running exe
    #[cfg(target_os = "windows")]
    {
        // This flag prevents the command prompt from appearing
        const CREATE_NO_WINDOW: u32 = 0x08000000;

        let batch_script = format!(
            r#"@echo off
rem Wait a moment for the current application to exit
timeout /t 2 /nobreak > nul
rem Delete the old executable
del /f /q "{}"
rem Move the downloaded temp file to the new versioned name
move /y "{}" "{}"
rem Start the new executable
start "" "{}"
rem Clean up this batch script
del "%~f0"
"#,
            current_exe.display(), // The old executable to delete
            temp_path.display(),   // The temporary downloaded file
            new_exe_path.display(),// The newly named executable
            new_exe_path.display() // The new executable to start
        );
        
        let batch_path = exe_dir.join("update.bat");
        fs::write(&batch_path, batch_script)
            .map_err(|e| format!("Failed to create update script: {}", e))?;
        
        // Execute the batch script silently and detach it from our process
        std::process::Command::new("cmd")
            .args(&["/C", batch_path.to_str().unwrap()])
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|e| format!("Failed to start update script: {}", e))?;
        
        // Exit the application so it can be replaced
        std::process::exit(0);
    }
    
    // Logic for non-Windows systems
    #[cfg(not(target_os = "windows"))]
    {
        // Move the temp file to the new versioned name
        fs::rename(&temp_path, &new_exe_path)
            .map_err(|e| format!("Failed to replace executable: {}", e))?;
        
        // Remove the old executable
        if current_exe.exists() {
            fs::remove_file(&current_exe).ok(); // .ok() ignores errors
        }

        // Make sure the new file is executable (on Unix-like systems)
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(&new_exe_path)?.permissions();
        perms.set_mode(0o755); // rwxr-xr-x
        fs::set_permissions(&new_exe_path, perms)?;

        // Restart the application with the new executable
        std::process::Command::new(&new_exe_path)
            .spawn()
            .map_err(|e| format!("Failed to restart application: {}", e))?;
        
        std::process::exit(0);
    }
}

// --- Main Function ---
fn main() -> Result<(), eframe::Error> {
    let icon = {
        let icon_data = Asset::get("beep_boop_baap-rounded.png")
            .expect("Failed to load icon from assets. Make sure 'beep_boop_baap-rounded.png' is in the 'assets' folder.");
        let image = image::load_from_memory(&icon_data.data)
            .expect("Failed to decode icon PNG")
            .to_rgba8();
        let (width, height) = image.dimensions();
        eframe::egui::IconData {
            rgba: image.into_raw(),
            width,
            height,
        }
    };

    const MAIN_ICON_WIDTH: f32 = 75.0;
    const MAIN_GRID_SPACING: f32 = 10.0;
    const MAX_ROUNDS: usize = 9;
    const LABEL_COL_WIDTH: f32 = 80.0;
    const HORIZONTAL_PADDING: f32 = 10.0; 

    let calculated_width = LABEL_COL_WIDTH 
                       + (MAIN_ICON_WIDTH * MAX_ROUNDS as f32) 
                       + (MAIN_GRID_SPACING * MAX_ROUNDS as f32) 
                       + HORIZONTAL_PADDING;

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([calculated_width, 575.0])
            .with_resizable(true)
            .with_icon(icon),
        persist_window: true,
        ..Default::default()
    };
    eframe::run_native(
        "R6 Operator Randomizer",
        options,
        Box::new(|cc| Box::new(R6OperatorRandomizerApp::new(cc))),
    )
}


