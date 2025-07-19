__version__ = "1.0.0"
__author__ = "YourName"
__description__ = "Rainbow Six Siege Operator Randomizer"
# Import necessary libraries 
import random
from tkinter import Tk, Frame, Label, Button, Entry

# Using the keyboard library for global hotkeys.
# This means the hotkey will work even if the window isn't focused.
import keyboard

# --- Operator Lists ---
# Fully updated and chronologically ordered based on your provided list.
ATTACKERS = ["Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", "Blitz", "IQ","Buck", "Blackbeard", "Capitão", "Hibana","Jackal", "Ying", "Zofia", "Dokkaebi","Lion", "Finka", "Maverick", "Nomad","Gridlock", "Nokk", "Amaru", "Kali","Iana", "Ace", "Zero", "Flores","Osa", "Sens","Grim", "Brava","Ram", "Deimos","Striker", "Skopós","Rauora"]
DEFENDERS = ["Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Jäger", "Bandit", 
    "Kapkan", "Tachanka","Frost", "Valkyrie", "Caveira", "Echo","Mira", "Lesion", "Ela", "Vigil","Maestro", "Alibi", "Clash", "Kaid","Mozzie", "Warden", "Goyo", "Wamai","Oryx", "Melusi", "Aruni","Thunderbird", "Thorn","Azami", "Solis","Fenrir", "Tubarao","Sentry"]


# --- Configuration Constants ---
ROUND_COUNT = {"Ranked": 9, "Unranked": 7, "Quick": 5, "Just Generate": 1}

# --- GUI Styling Constants (Updated based on user feedback) ---
FONT_STYLE = (None, 12, 'bold') # Default font, size 12, bold
BG_COLOR = '#1C1C1C'             # Dark grey background
HEADER_TEXT_COLOR = "#FFFF00"    # Yellow for "Round X" headers
SIDE_LABEL_COLOR = '#FFFF00'     # Yellow for "Attacker"/"Defender" labels
BUTTON_BG_COLOR = '#00A000'      # Green for button background
BUTTON_TEXT_COLOR = "#FFFFFF"    # White for button text
ATTACKER_OP_COLOR = '#FF0000'    # Red for Attacker names
DEFENDER_OP_COLOR = '#00BFFF'    # Deep Sky Blue for Defender names

class R6OperatorGenerator:
    def __init__(self):
        # --- Window Setup ---
        self.win = Tk()
        self.win.title("R6 Operator Randomizer")
        self.win.configure(background=BG_COLOR)
        # This makes the window always stay on top of other windows.
        self.win.attributes('-topmost', True)
        # Set a minimum size for the window
        self.win.minsize(600, 300) # Increased min height slightly for better spacing

        # --- State Variables ---
        self.last_mode = None
        self.generated_rounds = {"attackers": [], "defenders": []}
        self.generated_backups = {"attackers": [], "defenders": []}

        # --- UI Frames ---
        self.main_container = Frame(self.win, background=BG_COLOR, padx=10, pady=10)
        self.main_container.pack(expand=True, fill='both')
        
        self.output_frame = None
        self.button_frame = None
        self.backup_frame = None
        
        # --- Initialization ---
        self.create_widgets()
        self.setup_hotkeys()

    def create_widgets(self):
        """Creates and organizes all the UI elements in the window."""
        # --- Create Frames ---
        self.output_frame = Frame(self.main_container, background=BG_COLOR)
        self.output_frame.pack(pady=5, expand=True, fill='x')

        self.button_frame = Frame(self.main_container, background=BG_COLOR)
        self.button_frame.pack(pady=(10, 10))

        self.backup_frame = Frame(self.main_container, background=BG_COLOR)
        self.backup_frame.pack(pady=5, expand=True, fill='x')
        
        # --- Buttons ---
        modes = ["Ranked", "Unranked", "Quick", "Just Generate", "Copy"]
        commands = {
            "Ranked": lambda: self.generate_new_set("Ranked"),
            "Unranked": lambda: self.generate_new_set("Unranked"),
            "Quick": lambda: self.generate_new_set("Quick"),
            "Just Generate": lambda: self.generate_new_set("Just Generate"),
            "Copy": self.copy_to_clipboard
        }

        for mode in modes:
            Button(
                self.button_frame, 
                text=mode, 
                bg=BUTTON_BG_COLOR, 
                fg=BUTTON_TEXT_COLOR, 
                font=FONT_STYLE,
                relief='raised',
                padx=10,
                pady=5,
                command=commands[mode]
            ).pack(side='left', padx=5)

    def generate_new_set(self, mode):
        """Generates a new set of operators for the main rounds and a backup set."""
        self.last_mode = mode
        round_count = ROUND_COUNT.get(mode, 0)

        if len(ATTACKERS) < round_count * 2 or len(DEFENDERS) < round_count * 2:
            print(f"Not enough operators to generate a main and backup list for mode '{mode}'.")
            self.generated_rounds = {"attackers": [], "defenders": []}
            self.generated_backups = {"attackers": [], "defenders": []}
            self.display_round_operators()
            self.display_backup_operators()
            return

        main_attackers = random.sample(ATTACKERS, round_count)
        main_defenders = random.sample(DEFENDERS, round_count)
        self.generated_rounds["attackers"] = main_attackers
        self.generated_rounds["defenders"] = main_defenders
        
        available_attackers_for_backup = [op for op in ATTACKERS if op not in main_attackers]
        available_defenders_for_backup = [op for op in DEFENDERS if op not in main_defenders]
        
        self.generated_backups["attackers"] = random.sample(available_attackers_for_backup, round_count)
        self.generated_backups["defenders"] = random.sample(available_defenders_for_backup, round_count)
        
        self.display_round_operators()
        self.display_backup_operators()

    def display_round_operators(self):
        """Clears the main frame and displays the round operator data."""
        parent_frame = self.output_frame
        data = self.generated_rounds

        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"]: return

        Label(parent_frame, text="", bg=BG_COLOR).grid(row=0, column=0)
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"Round {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)
            
        for i in range(len(data["attackers"]) + 1):
            parent_frame.grid_columnconfigure(i, weight=1)

    def display_backup_operators(self):
        """Clears the backup frame and displays backup operators with a section header."""
        parent_frame = self.backup_frame
        data = self.generated_backups

        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"]: return

        # Add "Backups" title in the top-left corner of this section
        Label(parent_frame, text="Backup", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=0, column=0, sticky='w')

        # Add Round headers for backups to align with the main list
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"Round {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        # Display backup operators under the new headers
        # Using "Attacker" and "Defender" for the labels to ensure alignment
        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)

        col_count = len(data["attackers"])
        for i in range(col_count + 1):
            parent_frame.grid_columnconfigure(i, weight=1)

    def copy_to_clipboard(self):
        """Formats and copies the generated operators to the clipboard."""
        self.win.clipboard_clear()
        
        text_parts = []
        if self.generated_rounds["attackers"]:
            rounds_text = []
            for i in range(len(self.generated_rounds["attackers"])):
                attacker = self.generated_rounds["attackers"][i]
                defender = self.generated_rounds["defenders"][i]
                rounds_text.append(f"Round {i+1}\nA={attacker}\nD={defender}")
            text_parts.append("\n\n".join(rounds_text))
        
        if self.generated_backups["attackers"]:
            attackers_str = ', '.join(self.generated_backups["attackers"])
            defenders_str = ', '.join(self.generated_backups["defenders"])
            backup_text = f"Backup\nA={attackers_str}\nD={defenders_str}"
            text_parts.append(backup_text)
            
        full_text = "\n\n".join(text_parts)
        self.win.clipboard_append(full_text.strip())
        print("Copied to clipboard!")

    def setup_hotkeys(self):
        """Sets up the global hotkeys to re-run the generator."""
        try:
            keyboard.add_hotkey('f13', self.reactivate_last_mode)
            keyboard.add_hotkey('ctrl+scroll lock', self.reactivate_last_mode)
        except Exception as e:
            print(f"Could not set up hotkeys: {e}")

    def reactivate_last_mode(self):
        """Re-runs the last used generation mode."""
        if self.last_mode:
            print(f"Reactivating: {self.last_mode}")
            self.generate_new_set(self.last_mode)

    def run(self):
        """Starts the Tkinter main loop."""
        self.win.mainloop()


# --- Main Execution ---
if __name__ == "__main__":
    app = R6OperatorGenerator()
    app.run()
