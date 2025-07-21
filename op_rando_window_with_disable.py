# Import necessary libraries 
import random
from tkinter import Tk, Frame, Label, Button, Toplevel
import keyboard
import os
import math

# --- Operator Lists ---
# Fully updated and chronologically ordered based on your provided list.
ATTACKERS = ["Striker", "Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", "Blitz", "IQ", "Buck", "Blackbeard", "CAPITÃO", "Hibana", "Jackal", "Ying", "Zofia", "Dokkaebi", "Lion", "Finka", "Maverick", "Nomad", "Gridlock", "NØKK", "Amaru", "Kali", "Iana", "Ace", "Zero", "Flores", "Osa", "Sens", "Grim", "Brava", "Ram", "Deimos", "Rauora"]
DEFENDERS = ["Sentry", "Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Kapkan", "Tachanka", "Jäger", "Bandit", "Frost", "Valkyrie", "Caveira", "Echo", "Mira", "Lesion", "Ela", "Vigil", "Maestro", "Alibi", "Clash", "Kaid", "Mozzie", "Warden", "Goyo", "Wamai", "Oryx", "Melusi", "Aruni", "Thunderbird", "Thorn", "Azami", "Solis", "Fenrir", "Tubarão", "Skopós"]

# --- Configuration Constants ---
ROUND_COUNT = {"Ranked": 9, "Unranked": 9, "Quick": 5, "Just Generate": 1}

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


class R6OperatorGenerator:
    def __init__(self):
        # --- Window Setup ---
        self.win = Tk()
        self.win.title("R6 Operator Randomizer (No Icons)")
        self.win.configure(background=BG_COLOR)
        self.win.attributes('-topmost', True)
        self.win.withdraw()

        # --- State Variables ---
        self.last_mode = None
        self.generated_rounds = {"attackers": [], "defenders": []}
        self.generated_backups = {"attackers": [], "defenders": []}
        
        # --- State for disabled operators ---
        self.disabled_operators = set()
        self.operator_widgets = {} 
        self.disable_window = None 
        self.op_grid_frame = None
        self.attacker_tab_button = None
        self.defender_tab_button = None

        # --- UI Frames ---
        self.main_container = Frame(self.win, background=BG_COLOR, padx=10, pady=10)
        self.main_container.pack(expand=True, fill='both')
        
        self.output_frame = None
        self.button_frame = None
        self.backup_frame = None
        self.status_label = None 
        
        # --- Initialization ---
        self.create_widgets()
        self.setup_hotkeys()
        self.fix_window_size()
        self.win.deiconify()

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
        
        modes = ["Ranked", "Unranked", "Quick", "Just Generate", "Copy", "Disable Ops"]
        commands = {
            "Ranked": lambda: self.generate_new_set("Ranked"),
            "Unranked": lambda: self.generate_new_set("Unranked"),
            "Quick": lambda: self.generate_new_set("Quick"),
            "Just Generate": lambda: self.generate_new_set("Just Generate"),
            "Copy": self.copy_to_clipboard,
            "Disable Ops": self.open_disable_window
        }

        for i, mode in enumerate(modes):
            btn = Button(
                self.button_frame, text=mode, bg=BUTTON_BG_COLOR, fg=BUTTON_TEXT_COLOR, 
                font=FONT_STYLE, relief='raised', padx=10, pady=5, command=commands[mode]
            )
            btn.pack(side='left', padx=5)
            if mode == "Disable Ops":
                btn.config(bg='#B00020', fg='#FFFFFF')

    def fix_window_size(self):
        """Calculates and fixes the window size based on text content."""
        longest_attacker = max(ATTACKERS, key=len)
        longest_defender = max(DEFENDERS, key=len)
        max_rounds = ROUND_COUNT["Ranked"]

        dummy_rounds = {"attackers": [longest_attacker] * max_rounds, "defenders": [longest_defender] * max_rounds}
        dummy_backups = {"attackers": [longest_attacker] * max_rounds, "defenders": [longest_defender] * max_rounds}

        original_rounds, original_backups = self.generated_rounds, self.generated_backups
        self.generated_rounds, self.generated_backups = dummy_rounds, dummy_backups

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

    def generate_new_set(self, mode, force_display=True):
        """Generates a new set of operators, respecting the disabled list."""
        self.status_label.config(text="")
        self.last_mode = mode
        round_count = ROUND_COUNT.get(mode, 0)

        enabled_attackers = [op for op in ATTACKERS if op not in self.disabled_operators]
        enabled_defenders = [op for op in DEFENDERS if op not in self.disabled_operators]

        required_ops = round_count * 2 if mode != "Just Generate" else round_count
        if len(enabled_attackers) < required_ops or len(enabled_defenders) < required_ops:
            msg = f"Not enough enabled operators for mode '{mode}'!"
            self.status_label.config(text=msg)
            self.generated_rounds = {"attackers": [], "defenders": []}
            self.generated_backups = {"attackers": [], "defenders": []}
        else:
            main_attackers = random.sample(enabled_attackers, round_count)
            main_defenders = random.sample(enabled_defenders, round_count)
            self.generated_rounds = {"attackers": main_attackers, "defenders": main_defenders}
            
            if mode != "Just Generate":
                available_attackers_for_backup = [op for op in enabled_attackers if op not in main_attackers]
                available_defenders_for_backup = [op for op in enabled_defenders if op not in main_defenders]
                self.generated_backups["attackers"] = random.sample(available_attackers_for_backup, round_count)
                self.generated_backups["defenders"] = random.sample(available_defenders_for_backup, round_count)
            else:
                self.generated_backups = {"attackers": [], "defenders": []}
        
        if force_display:
            self.display_round_operators()
            self.display_backup_operators()

    # --- Disable Operators Window (Text Only) ---

    def open_disable_window(self):
        """Opens a new Toplevel window to manage disabled operators with a tabbed view."""
        if self.disable_window and self.disable_window.winfo_exists():
            self.disable_window.lift()
            return

        self.disable_window = Toplevel(self.win)
        self.disable_window.title("Disable Operators")
        self.disable_window.configure(bg=BG_COLOR)
        self.disable_window.attributes('-topmost', True)
        self.disable_window.resizable(False, False)

        tab_frame = Frame(self.disable_window, bg=BG_COLOR)
        tab_frame.pack(pady=5, padx=10, fill='x')
        
        self.attacker_tab_button = Button(tab_frame, text="Attackers", font=FONT_STYLE, relief='flat', command=lambda: self.switch_disable_view('attackers'))
        self.attacker_tab_button.pack(side='left', expand=True, fill='x')

        self.defender_tab_button = Button(tab_frame, text="Defenders", font=FONT_STYLE, relief='flat', command=lambda: self.switch_disable_view('defenders'))
        self.defender_tab_button.pack(side='left', expand=True, fill='x')

        self.op_grid_frame = Frame(self.disable_window, bg=BG_COLOR)
        self.op_grid_frame.pack(pady=10, padx=10)

        self.switch_disable_view('attackers')

    def switch_disable_view(self, op_type):
        """Clears and repopulates the grid for the selected operator type."""
        for widget in self.op_grid_frame.winfo_children(): widget.destroy()

        if op_type == 'attackers':
            self.attacker_tab_button.config(bg=ACTIVE_TAB_COLOR, fg=ATTACKER_OP_COLOR)
            self.defender_tab_button.config(bg=INACTIVE_TAB_COLOR, fg=DEFENDER_OP_COLOR)
            self.populate_operator_grid(ATTACKERS)
        else:
            self.attacker_tab_button.config(bg=INACTIVE_TAB_COLOR, fg=ATTACKER_OP_COLOR)
            self.defender_tab_button.config(bg=ACTIVE_TAB_COLOR, fg=DEFENDER_OP_COLOR)
            self.populate_operator_grid(DEFENDERS)
        
        self.disable_window.update_idletasks()
        req_width = self.op_grid_frame.winfo_reqwidth()
        req_height = self.op_grid_frame.winfo_reqheight() + self.attacker_tab_button.winfo_reqheight()
        self.disable_window.geometry(f"{req_width + 20}x{req_height + 20}")

    def populate_operator_grid(self, operators):
        """Fills the grid frame with operator names for the disable window."""
        cols = 6 # Adjusted for text labels
        for i, op_name in enumerate(operators):
            row, col = divmod(i, cols)
            
            name_label = Label(self.op_grid_frame, text=op_name, bg=BG_COLOR, fg='white', font=(None, 10, 'bold'), padx=10, pady=5)
            name_label.grid(row=row, column=col, padx=2, pady=2, sticky='ew')

            self.operator_widgets[op_name] = name_label
            self.update_op_widget_visual(op_name)
            name_label.bind("<Button-1>", lambda e, op=op_name: self.toggle_operator_disabled(op))

    def toggle_operator_disabled(self, op_name):
        """Toggles an operator's disabled state and updates their visual."""
        if op_name in self.disabled_operators:
            self.disabled_operators.remove(op_name)
        else:
            self.disabled_operators.add(op_name)
        self.update_op_widget_visual(op_name)

    def update_op_widget_visual(self, op_name):
        """Updates a single operator's label to reflect its current state."""
        if op_name not in self.operator_widgets: return
        
        widget = self.operator_widgets[op_name]
        is_disabled = op_name in self.disabled_operators
        widget.config(fg='grey' if is_disabled else 'white')

    # --- Main Display (Text Only) ---

    def _display_operators(self, parent_frame, data, title_prefix):
        """Helper function to display a set of operators (main or backup) as text."""
        for widget in parent_frame.winfo_children(): widget.destroy()
        if not data["attackers"]: return

        Label(parent_frame, text="", bg=BG_COLOR).grid(row=0, column=0, padx=5)
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"{title_prefix} {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)
            
        for i in range(len(data["attackers"]) + 1):
            parent_frame.grid_columnconfigure(i, weight=1)

    def display_round_operators(self):
        """Displays the main round operators."""
        self._display_operators(self.output_frame, self.generated_rounds, "Round")

    def display_backup_operators(self):
        """Displays the backup operators."""
        self._display_operators(self.backup_frame, self.generated_backups, "Back")

    # --- Other Methods ---

    def copy_to_clipboard(self):
        """Formats and copies the generated operators to the clipboard."""
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
        else:
            self.status_label.config(text="Nothing to copy.")

    def setup_hotkeys(self):
        """Sets up the global hotkeys to re-run the generator."""
        try:
            keys_to_bind = ['f13', 'f14', 'f15', 'f16', 'f17', 'ctrl+scroll lock']
            for key in keys_to_bind:
                keyboard.add_hotkey(key, self.reactivate_last_mode)
        except Exception as e:
            print(f"Could not set up hotkeys: {e}")

    def reactivate_last_mode(self):
        """Re-runs the last used generation mode safely on the GUI thread."""
        if self.last_mode:
            self.win.after(0, lambda: self.generate_new_set(self.last_mode))

    def run(self):
        """Starts the Tkinter main loop."""
        self.win.mainloop()

# --- Main Execution ---
if __name__ == "__main__":
    app = R6OperatorGenerator()
    app.run()
