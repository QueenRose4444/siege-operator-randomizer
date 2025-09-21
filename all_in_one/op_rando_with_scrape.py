# Import necessary libraries
import random
from tkinter import Tk, Frame, Label, Button, Toplevel, messagebox, BooleanVar, Checkbutton
import keyboard
import os
import sys
import math
import json
from PIL import Image, ImageTk, ImageOps
import threading
import time

# --- Optional imports for the scraper functionality ---
# The application can run without these, but the update feature will be disabled.
try:
    import requests
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService # <-- ADD THIS IMPORT
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import io
    SCRAPER_LIBS_AVAILABLE = True
except ImportError:
    SCRAPER_LIBS_AVAILABLE = False


# --- PYINSTALLER HELPER FUNCTION ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Get the directory of the script file, not the current working directory
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# --- Path Constants (using the helper function) ---
OPERATORS_FILE = resource_path('operators_list.json')
IMAGE_DIR = resource_path('images')


# --- SCRAPER HELPER FUNCTIONS ---
# These functions are from the original scrape_ops.py script

ATTACKER_URL = 'https://www.ubisoft.com/en-au/game/rainbow-six/siege/game-info/operators?role=attacker'
DEFENDER_URL = 'https://www.ubisoft.com/en-au/game/rainbow-six/siege/game-info/operators?role=defender'

def write_operator_lists(attackers, defenders):
    """Writes the given operator lists to the JSON file with custom formatting."""
    data = {"ATTACKERS": attackers, "DEFENDERS": defenders}
    with open(OPERATORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def setup_environment():
    """Creates the 'images' directory if it doesn't already exist."""
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

def create_driver():
    """Creates and configures a Chrome WebDriver instance."""
    if not SCRAPER_LIBS_AVAILABLE: return None
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    try:
        # --- MODIFICATION FOR PYINSTALLER ---
        # Use the resource_path to find chromedriver.exe when bundled
        service = ChromeService(executable_path=resource_path('chromedriver.exe'))
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # ------------------------------------

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except WebDriverException:
        return None

def create_session():
    """Creates a requests session with realistic browser headers for image downloads."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br', 'DNT': '1', 'Connection': 'keep-alive'
    })
    return session

def download_image(session, url, filepath):
    """Downloads a single image from a URL and saves it as a PNG to preserve transparency."""
    try:
        response = session.get(url, stream=True, timeout=15)
        response.raise_for_status()
        image_data = io.BytesIO(response.content)
        with Image.open(image_data) as img:
            filepath_png = os.path.splitext(filepath)[0] + ".png"
            img.save(filepath_png, 'PNG')
        return True
    except (requests.exceptions.RequestException, IOError):
        return False

def extract_operators_with_selenium(driver, url, role_name):
    """Extract operators from a URL using Selenium."""
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.oplist__card")))
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        op_cards = soup.find_all('a', class_='oplist__card')
        operator_names, missing_images = [], []
        for card in op_cards:
            name_span = card.find('span')
            if not name_span: continue
            operator_name = name_span.text.strip().upper() # Standardize to uppercase
            operator_names.append(operator_name)
            img = card.find('img', class_='oplist__card__icon')
            if img and img.get('src'):
                filename = f"{operator_name} icon.png" # Use the clean name for the file
                filepath = os.path.join(IMAGE_DIR, filename)
                if not os.path.exists(filepath):
                    missing_images.append({'url': img['src'], 'filepath': filepath, 'filename': filename})
        return operator_names, missing_images
    except (TimeoutException, Exception):
        return [], []


# --- GUI Styling Constants ---
FONT_STYLE = (None, 12, 'bold')
BG_COLOR = '#1C1C1C'
HEADER_TEXT_COLOR = "#FFFF00"
SIDE_LABEL_COLOR = '#FFFF00'
BUTTON_BG_COLOR = '#00A000'
BUTTON_TEXT_COLOR = "#FFFFFF"
ATTACKER_OP_COLOR = '#FF0000'
DEFENDER_OP_COLOR = '#00BFFF'
ACTIVE_TAB_COLOR = '#4A4A4A'
INACTIVE_TAB_COLOR = '#2A2A2A'

# --- Configuration Constants ---
ROUND_COUNT = {"Ranked": 9, "Unranked": 9, "Quick": 5, "Just Generate": 1}


class R6OperatorGenerator:
    def __init__(self):
        self.win = Tk()
        self.win.title("R6 Operator Randomizer")
        self.win.configure(background=BG_COLOR)
        self.win.attributes('-topmost', True)
        self.win.withdraw()

        self.last_mode = None
        self.generated_rounds = {"attackers": [], "defenders": []}
        self.generated_backups = {"attackers": [], "defenders": []}
        
        self.disabled_operators = set()
        self.operator_widgets = {} 
        self.operator_images_color = {}
        self.operator_images_grey = {}
        self.main_display_images = {}
        self.disable_window = None 
        self.op_grid_frame = None
        self.attacker_tab_button = None
        self.defender_tab_button = None
        self.active_disable_tab = 'attackers'
        
        # --- Variables for op counter and toggle ---
        self.allow_insufficient_ops = BooleanVar(value=False)
        self.op_counter_frame = None # Frame to hold multiple labels

        self.attackers = []
        self.defenders = []
        self.load_operators(OPERATORS_FILE)

        self.main_container = Frame(self.win, background=BG_COLOR, padx=10, pady=10)
        self.main_container.pack(expand=True, fill='both')
        
        self.output_frame = None
        self.button_frame = None
        self.backup_frame = None
        self.status_label = None 
        self.update_button = None
        
        self.create_widgets()
        self.setup_hotkeys()
        self.fix_window_size()
        self.win.deiconify()

    def load_operators(self, filepath):
        """Loads operator lists from a JSON file and sets them as instance attributes."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.attackers = [op.upper() for op in data.get("ATTACKERS", [])] # Standardize to uppercase
                self.defenders = [op.upper() for op in data.get("DEFENDERS", [])] # Standardize to uppercase
                if not isinstance(self.attackers, list) or not isinstance(self.defenders, list):
                    raise TypeError("ATTACKERS and DEFENDERS must be lists in the JSON file.")
        except FileNotFoundError:
            messagebox.showerror("Fatal Error", f"'{os.path.basename(filepath)}' not found. Please create it or run the update checker.")
            sys.exit(1)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            messagebox.showerror("Fatal Error", f"Error reading '{os.path.basename(filepath)}': {e}")
            sys.exit(1)

    def create_widgets(self):
        """Creates and organizes all the UI elements in the window."""
        self.output_frame = Frame(self.main_container, background=BG_COLOR)
        self.output_frame.pack(pady=5, expand=True, fill='x')
        self.button_frame = Frame(self.main_container, background=BG_COLOR)
        self.button_frame.pack(pady=(10, 5))
        self.status_label = Label(self.main_container, text="", bg=BG_COLOR, fg="orange", font=(None, 10, 'bold'))
        self.status_label.pack(pady=(0, 5))
        self.backup_frame = Frame(self.main_container, background=BG_COLOR)
        self.backup_frame.pack(pady=5, expand=True, fill='x')
        
        modes = ["Ranked", "Unranked", "Quick", "Just Generate", "Copy", "Disable Ops", "Check for Updates"]
        commands = {
            "Ranked": lambda: self.generate_new_set("Ranked"), "Unranked": lambda: self.generate_new_set("Unranked"),
            "Quick": lambda: self.generate_new_set("Quick"), "Just Generate": lambda: self.generate_new_set("Just Generate"),
            "Copy": self.copy_to_clipboard, "Disable Ops": self.open_disable_window, "Check for Updates": self.start_scraper_thread
        }

        for mode in modes:
            btn = Button(self.button_frame, text=mode, bg=BUTTON_BG_COLOR, fg=BUTTON_TEXT_COLOR, 
                         font=FONT_STYLE, relief='raised', padx=10, pady=5, command=commands[mode])
            btn.pack(side='left', padx=5)
            if mode == "Disable Ops": btn.config(bg='#B00020', fg='#FFFFFF')
            if mode == "Check for Updates":
                btn.config(bg='#007ACC')
                self.update_button = btn

    def fix_window_size(self):
        """Calculates and fixes the window size based on content."""
        if not self.attackers or not self.defenders: return
        self.win.update_idletasks()
        original_rounds, original_backups = self.generated_rounds.copy(), self.generated_backups.copy()
        
        longest_attacker = max(self.attackers, key=len)
        longest_defender = max(self.defenders, key=len)
        max_rounds = ROUND_COUNT["Ranked"]

        self.generated_rounds = {"attackers": [longest_attacker] * max_rounds, "defenders": [longest_defender] * max_rounds}
        self.generated_backups = {"attackers": [longest_attacker] * max_rounds, "defenders": [longest_defender] * max_rounds}
        
        self.display_round_operators()
        self.display_backup_operators()
        self.win.update_idletasks()
        
        width = self.main_container.winfo_reqwidth()
        height = self.main_container.winfo_reqheight()
        self.win.geometry(f"{width + 20}x{height + 20}")
        self.win.resizable(False, False)

        for widget in self.output_frame.winfo_children(): widget.destroy()
        for widget in self.backup_frame.winfo_children(): widget.destroy()

        self.generated_rounds, self.generated_backups = original_rounds, original_backups
        self.display_round_operators()
        self.display_backup_operators()

    def generate_new_set(self, mode, force_display=True):
        """Generates a new set of operators, respecting disabled list, and allowing reuse if needed."""
        self.status_label.config(text="")
        self.last_mode = mode
        round_count = ROUND_COUNT.get(mode, 0)

        enabled_attackers = [op for op in self.attackers if op not in self.disabled_operators]
        enabled_defenders = [op for op in self.defenders if op not in self.disabled_operators]

        if not enabled_attackers or not enabled_defenders:
            self.status_label.config(text="Cannot generate with zero enabled attackers or defenders.")
            self.generated_rounds, self.generated_backups = {"attackers": [], "defenders": []}, {"attackers": [], "defenders": []}
        else:
            sufficient_attackers = len(enabled_attackers) >= round_count
            sufficient_defenders = len(enabled_defenders) >= round_count

            if not self.allow_insufficient_ops.get() and (not sufficient_attackers or not sufficient_defenders):
                msg = f"Not enough enabled operators for mode '{mode}'!"
                self.status_label.config(text=msg)
                self.generated_rounds, self.generated_backups = {"attackers": [], "defenders": []}, {"attackers": [], "defenders": []}
            else:
                # Generate main list of operators
                attacker_sample_func = random.sample if sufficient_attackers else random.choices
                defender_sample_func = random.sample if sufficient_defenders else random.choices

                self.generated_rounds["attackers"] = attacker_sample_func(enabled_attackers, k=round_count)
                self.generated_rounds["defenders"] = defender_sample_func(enabled_defenders, k=round_count)
                
                # Generate backup list, prioritizing unique operators
                if mode != "Just Generate":
                    # Attacker Backups
                    main_attackers_set = set(self.generated_rounds["attackers"])
                    available_attackers_for_backup = [op for op in enabled_attackers if op not in main_attackers_set]
                    
                    backup_attackers = []
                    if len(available_attackers_for_backup) >= round_count:
                        backup_attackers = random.sample(available_attackers_for_backup, k=round_count)
                    else:
                        backup_attackers.extend(available_attackers_for_backup)
                        needed = round_count - len(backup_attackers)
                        borrowed = random.choices(self.generated_rounds["attackers"], k=needed)
                        backup_attackers.extend(borrowed)
                        random.shuffle(backup_attackers)
                    self.generated_backups["attackers"] = backup_attackers

                    # Defender Backups
                    main_defenders_set = set(self.generated_rounds["defenders"])
                    available_defenders_for_backup = [op for op in enabled_defenders if op not in main_defenders_set]

                    backup_defenders = []
                    if len(available_defenders_for_backup) >= round_count:
                        backup_defenders = random.sample(available_defenders_for_backup, k=round_count)
                    else:
                        backup_defenders.extend(available_defenders_for_backup)
                        needed = round_count - len(backup_defenders)
                        borrowed = random.choices(self.generated_rounds["defenders"], k=needed)
                        backup_defenders.extend(borrowed)
                        random.shuffle(backup_defenders)
                    self.generated_backups["defenders"] = backup_defenders
                else:
                    self.generated_backups = {"attackers": [], "defenders": []}
        
        if force_display:
            self.display_round_operators()
            self.display_backup_operators()

    def _load_image(self, op_name, size, cache, greyscale=False):
        """Internal helper to load, resize, and cache an image."""
        cache_key = (op_name, greyscale)
        if cache_key in cache: return cache[cache_key]
        
        try:
            image_path = os.path.join(IMAGE_DIR, f"{op_name} icon.png")
            with Image.open(image_path) as img:
                img = img.resize(size, Image.Resampling.LANCZOS)
                if greyscale: img = ImageOps.grayscale(img).convert('RGBA')
                photo = ImageTk.PhotoImage(img)
                cache[cache_key] = photo
                return photo
        except FileNotFoundError:
            placeholder = Image.new('RGB', size, 'black')
            if greyscale: placeholder = ImageOps.grayscale(placeholder)
            photo = ImageTk.PhotoImage(placeholder)
            cache[cache_key] = photo
            return photo

    def load_disable_window_images(self, op_name):
        color_img = self._load_image(op_name, (64, 64), self.operator_images_color, greyscale=False)
        grey_img = self._load_image(op_name, (64, 64), self.operator_images_grey, greyscale=True)
        return color_img, grey_img

    def load_main_display_image(self, op_name):
        return self._load_image(op_name, (48, 48), self.main_display_images, greyscale=False)

    def open_disable_window(self):
        """Opens a new Toplevel window to manage disabled operators."""
        if self.disable_window and self.disable_window.winfo_exists():
            self.disable_window.lift()
            return

        self.disable_window = Toplevel(self.win)
        self.disable_window.title("Disable Operators")
        self.disable_window.configure(bg=BG_COLOR)
        self.disable_window.attributes('-topmost', True)

        tab_frame = Frame(self.disable_window, bg=BG_COLOR)
        tab_frame.pack(pady=5, padx=10, fill='x')
        
        self.attacker_tab_button = Button(tab_frame, text="Attackers", font=FONT_STYLE, relief='flat', command=lambda: self.switch_disable_view('attackers'))
        self.attacker_tab_button.pack(side='left', expand=True, fill='x')
        self.defender_tab_button = Button(tab_frame, text="Defenders", font=FONT_STYLE, relief='flat', command=lambda: self.switch_disable_view('defenders'))
        self.defender_tab_button.pack(side='left', expand=True, fill='x')

        self.op_grid_frame = Frame(self.disable_window, bg=BG_COLOR)
        self.op_grid_frame.pack(pady=10, padx=10)

        # --- Bottom frame for counter and toggle ---
        bottom_frame = Frame(self.disable_window, bg=BG_COLOR)
        bottom_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 10))

        self.op_counter_frame = Frame(bottom_frame, bg=BG_COLOR)
        self.op_counter_frame.pack(side='left')

        # --- Frame for right-side controls ---
        right_controls_frame = Frame(bottom_frame, bg=BG_COLOR)
        right_controls_frame.pack(side='right')

        reset_button = Button(right_controls_frame, text="Reset Page", command=self.reset_disables_for_current_view,
                                bg='#D32F2F', fg='white', font=(None, 8, 'bold'), relief='raised', padx=5, pady=2)
        reset_button.pack(side='left', padx=(0, 10))

        toggle_button = Checkbutton(right_controls_frame, text="Allow insufficient ops", variable=self.allow_insufficient_ops, 
                                    bg=BG_COLOR, fg='white', selectcolor=BG_COLOR, activebackground=BG_COLOR, 
                                    activeforeground='white', font=(None, 9), relief='flat', highlightthickness=0, bd=0)
        toggle_button.pack(side='left')

        # --- Logic to prevent resizing ---
        longest_list = self.attackers if len(self.attackers) >= len(self.defenders) else self.defenders
        self.populate_operator_grid(longest_list)
        self.disable_window.update_idletasks()
        width = self.disable_window.winfo_reqwidth()
        height = self.disable_window.winfo_reqheight()
        self.disable_window.geometry(f"{width}x{height}")
        self.disable_window.resizable(False, False)

        self.switch_disable_view(self.active_disable_tab)

    def switch_disable_view(self, op_type):
        """Clears and repopulates the grid for the selected operator type."""
        self.active_disable_tab = op_type
        for widget in self.op_grid_frame.winfo_children(): widget.destroy()

        if op_type == 'attackers':
            self.attacker_tab_button.config(bg=ACTIVE_TAB_COLOR, fg=ATTACKER_OP_COLOR)
            self.defender_tab_button.config(bg=INACTIVE_TAB_COLOR, fg=DEFENDER_OP_COLOR)
            self.populate_operator_grid(self.attackers)
        else: # defenders
            self.attacker_tab_button.config(bg=INACTIVE_TAB_COLOR, fg=ATTACKER_OP_COLOR)
            self.defender_tab_button.config(bg=ACTIVE_TAB_COLOR, fg=DEFENDER_OP_COLOR)
            self.populate_operator_grid(self.defenders)
            
        self.update_op_counter() # Update counter for the new view

    def populate_operator_grid(self, operators):
        """Fills the grid with operators, preserving the original JSON order."""
        cols = 10
        for i, op_name in enumerate(operators):
            row, col = divmod(i, cols)
            op_frame = Frame(self.op_grid_frame, bg=BG_COLOR)
            op_frame.grid(row=row, column=col, padx=5, pady=5)
            icon_label = Label(op_frame, bg=BG_COLOR); icon_label.pack()
            name_label = Label(op_frame, text=op_name, bg=BG_COLOR, fg='white', font=(None, 9)); name_label.pack()
            self.operator_widgets[op_name] = {'icon': icon_label, 'name': name_label}
            self.update_op_widget_visual(op_name)
            for widget in [op_frame, icon_label, name_label]:
                widget.bind("<Button-1>", lambda e, op=op_name: self.toggle_operator_disabled(op))

    def reset_disables_for_current_view(self):
        """Resets the disabled operators for the currently active tab."""
        if not self.disable_window or not self.disable_window.winfo_exists():
            return
            
        ops_to_reset = self.attackers if self.active_disable_tab == 'attackers' else self.defenders
        
        # Go through the list of ops for the current view and remove them from the disabled set.
        for op_name in ops_to_reset:
            if op_name in self.disabled_operators:
                self.disabled_operators.remove(op_name)
        
        # Refresh the visuals for all operators on the current grid.
        for op_name in ops_to_reset:
            self.update_op_widget_visual(op_name)
            
        # Update the counter to reflect the changes.
        self.update_op_counter()

    def toggle_operator_disabled(self, op_name):
        if op_name in self.disabled_operators: self.disabled_operators.remove(op_name)
        else: self.disabled_operators.add(op_name)
        self.update_op_widget_visual(op_name)
        self.update_op_counter()

    def update_op_widget_visual(self, op_name):
        if op_name not in self.operator_widgets: return
        widget_set = self.operator_widgets[op_name]
        is_disabled = op_name in self.disabled_operators
        color_img, grey_img = self.load_disable_window_images(op_name)
        widget_set['icon'].config(image=grey_img if is_disabled else color_img)
        widget_set['name'].config(fg='grey' if is_disabled else 'white')

    def update_op_counter(self):
        """Updates the operator counter labels based on the active tab and colors them individually."""
        if not self.op_counter_frame or not self.disable_window.winfo_exists(): return
        
        for widget in self.op_counter_frame.winfo_children(): widget.destroy()

        if self.active_disable_tab == 'attackers':
            enabled_count = len([op for op in self.attackers if op not in self.disabled_operators])
            role = "Attackers"
        else: # defenders
            enabled_count = len([op for op in self.defenders if op not in self.disabled_operators])
            role = "Defenders"

        Label(self.op_counter_frame, text=f"{role}:", bg=BG_COLOR, fg='white', font=(None, 9, 'bold')).pack(side='left', padx=(0, 5))

        reqs = {"Quick": ROUND_COUNT["Quick"], "Ranked": ROUND_COUNT["Ranked"], "Unranked": ROUND_COUNT["Unranked"]}
        grouped_reqs = {}
        for mode, count in reqs.items():
            if count not in grouped_reqs: grouped_reqs[count] = []
            grouped_reqs[count].append(mode)
            
        for count, modes in sorted(grouped_reqs.items()):
            mode_str = "/".join(modes)
            is_sufficient = enabled_count >= count
            color = 'white' if is_sufficient else '#FF4C4C'
            text = f"{mode_str}: {enabled_count}/{count}"
            Label(self.op_counter_frame, text=text, bg=BG_COLOR, fg=color, font=(None, 9)).pack(side='left', padx=5)

    def _display_operators(self, parent_frame, data, title_prefix):
        for widget in parent_frame.winfo_children(): widget.destroy()
        if not data["attackers"]: return
        Label(parent_frame, text="", bg=BG_COLOR).grid(row=0, column=0, padx=5)
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"{title_prefix} {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)
        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            op_frame = Frame(parent_frame, bg=BG_COLOR); op_frame.grid(row=1, column=i+1, pady=2)
            icon = self.load_main_display_image(op)
            Label(op_frame, image=icon, bg=BG_COLOR).pack()
            Label(op_frame, text=op, bg=BG_COLOR, font=(None, 10, 'bold'), fg=ATTACKER_OP_COLOR).pack()
        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            op_frame = Frame(parent_frame, bg=BG_COLOR); op_frame.grid(row=2, column=i+1, pady=2)
            icon = self.load_main_display_image(op)
            Label(op_frame, image=icon, bg=BG_COLOR).pack()
            Label(op_frame, text=op, bg=BG_COLOR, font=(None, 10, 'bold'), fg=DEFENDER_OP_COLOR).pack()
        for i in range(len(data["attackers"]) + 1): parent_frame.grid_columnconfigure(i, weight=1)

    def display_round_operators(self): self._display_operators(self.output_frame, self.generated_rounds, "Round")
    def display_backup_operators(self): self._display_operators(self.backup_frame, self.generated_backups, "Back")

    def copy_to_clipboard(self):
        self.win.clipboard_clear()
        text_parts = []
        if self.generated_rounds["attackers"]:
            rounds_text = [f"Round {i+1}\nA={a}\nD={d}" for i, (a, d) in enumerate(zip(self.generated_rounds["attackers"], self.generated_rounds["defenders"]))]
            text_parts.append("\n\n".join(rounds_text))
        if self.generated_backups["attackers"]:
            attackers_str = ', '.join(self.generated_backups["attackers"])
            defenders_str = ', '.join(self.generated_backups["defenders"])
            text_parts.append(f"Backup\nA={attackers_str}\nD={defenders_str}")
        full_text = "\n\n".join(text_parts)
        if full_text:
            self.win.clipboard_append(full_text.strip())
            self.status_label.config(text="Copied to clipboard!")
        else: self.status_label.config(text="Nothing to copy.")

    def setup_hotkeys(self):
        try:
            for key in ['f13', 'f14', 'f15', 'f16', 'f17', 'ctrl+scroll lock']:
                keyboard.add_hotkey(key, self.reactivate_last_mode)
        except Exception: pass

    def reactivate_last_mode(self):
        if self.last_mode: self.win.after(0, lambda: self.generate_new_set(self.last_mode))
    
    # --- Scraper Integration Methods ---
    
    def start_scraper_thread(self):
        """Starts the scraper function in a separate thread to avoid freezing the GUI."""
        if not SCRAPER_LIBS_AVAILABLE:
            messagebox.showerror("Missing Libraries", "Required libraries for scraping (requests, beautifulsoup4, selenium) are not installed.")
            return

        if hasattr(self, 'scraper_thread') and self.scraper_thread.is_alive():
            self.status_label.config(text="Update check already in progress...")
            return

        self.update_button.config(state='disabled', text="Checking...")
        self.status_label.config(text="Starting update check... This may take a moment.")
        self.scraper_thread = threading.Thread(target=self._run_scraper_logic, daemon=True)
        self.scraper_thread.start()

    def _run_scraper_logic(self):
        """The core scraping logic, designed to run in a background thread."""
        results = {'new_ops': [], 'new_images_count': 0, 'error': None}
        try:
            setup_environment()
            driver = create_driver()
            if not driver:
                results['error'] = "Could not create Chrome driver. Is Chrome/chromedriver installed?"
                self.win.after(0, self._on_scraper_complete, results); return
            
            session = create_session()
            known_attackers, known_defenders = self.attackers.copy(), self.defenders.copy()
            updated_attackers, updated_defenders = known_attackers.copy(), known_defenders.copy()
            all_missing_images = []
            new_operators_found = False

            try:
                attacker_names, attacker_images = extract_operators_with_selenium(driver, ATTACKER_URL, "Attacker")
                new_attackers = [name for name in attacker_names if name not in known_attackers]
                if new_attackers: new_operators_found = True; results['new_ops'].extend(new_attackers); updated_attackers.extend(new_attackers)
                all_missing_images.extend(attacker_images)
                time.sleep(1)
                defender_names, defender_images = extract_operators_with_selenium(driver, DEFENDER_URL, "Defender")
                new_defenders = [name for name in defender_names if name not in known_defenders]
                if new_defenders: new_operators_found = True; results['new_ops'].extend(new_defenders); updated_defenders.extend(new_defenders)
                all_missing_images.extend(defender_images)
            finally: driver.quit()

            if all_missing_images:
                unique_images = {img['url']: img for img in all_missing_images}.values()
                results['new_images_count'] = len(unique_images)
                for image_info in unique_images: download_image(session, image_info['url'], image_info['filepath'])
            if new_operators_found: write_operator_lists(sorted(updated_attackers), sorted(updated_defenders))
        except Exception as e: results['error'] = f"An error occurred during scraping: {e}"
        self.win.after(0, self._on_scraper_complete, results)

    def _on_scraper_complete(self, results):
        """Handles the results from the scraper thread and updates the GUI."""
        self.update_button.config(state='normal', text="Check for Updates")
        if results['error']:
            self.status_label.config(text=f"Error: {results['error']}")
            messagebox.showerror("Update Failed", results['error'])
            return
        
        new_ops_count, new_images_count = len(results['new_ops']), results['new_images_count']
        if new_ops_count == 0 and new_images_count == 0:
            self.status_label.config(text="Everything is up to date! (b ᵔ▽ᵔ)b")
            return

        message_parts = []
        if new_ops_count > 0: message_parts.append(f"Found {new_ops_count} new operator(s): {', '.join(results['new_ops'])}")
        if new_images_count > 0: message_parts.append(f"Downloaded {new_images_count} new icon(s).")
        
        summary_message = "\n".join(message_parts)
        self.status_label.config(text="Update complete! " + " | ".join(message_parts))
        messagebox.showinfo("Update Complete", summary_message)
        self.reload_data_and_refresh_ui()

    def reload_data_and_refresh_ui(self):
        """Reloads operator data from file and refreshes relevant UI parts."""
        self.load_operators(OPERATORS_FILE)
        self.operator_images_color.clear()
        self.operator_images_grey.clear()
        self.main_display_images.clear()
        if self.disable_window and self.disable_window.winfo_exists():
            # Re-open (or refresh) logic
            self.disable_window.destroy()
            self.open_disable_window()
        if self.last_mode:
            self.generate_new_set(self.last_mode, force_display=True)
        self.fix_window_size()

    def run(self):
        """Starts the Tkinter main loop."""
        self.win.mainloop()

# --- Main Execution ---
if __name__ == "__main__":
    if not os.path.isdir(IMAGE_DIR): os.makedirs(IMAGE_DIR)
    app = R6OperatorGenerator()
    app.run()

