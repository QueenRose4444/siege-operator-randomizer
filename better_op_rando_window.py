# Import necessary libraries 
import random
from tkinter import Tk, Frame, Label, Button

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
BACKUP_COUNT = 4

# --- GUI Styling Constants (Updated based on user feedback) ---
FONT_STYLE = (None, 12, 'bold') # Default font, size 12, bold
BG_COLOR = '#1C1C1C'             # Dark grey background
HEADER_TEXT_COLOR = "#FFFF00"    # Red for "Round X" headers
SIDE_LABEL_COLOR = '#FFFF00'     # Yellow for "Attacker"/"Defender" labels
BUTTON_BG_COLOR = '#00A000'      # Green for button background
BUTTON_TEXT_COLOR = "#FFFFFF"    # Black for button text
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
        self.win.minsize(600, 250)

        # --- State Variables ---
        # Storing the generated operators in variables is more reliable
        # than trying to read them back from the UI labels.
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
        # The order of packing determines the layout
        self.output_frame = Frame(self.main_container, background=BG_COLOR)
        self.output_frame.pack(pady=5, expand=True, fill='x')

        self.button_frame = Frame(self.main_container, background=BG_COLOR)
        self.button_frame.pack(pady=(10, 10))

        self.backup_frame = Frame(self.main_container, background=BG_COLOR)
        self.backup_frame.pack(pady=5, expand=True, fill='x')
        
        # --- Buttons ---
        modes = ["Ranked", "Unranked", "Quick", "Just Generate", "Backup", "Copy"]
        commands = {
            "Ranked": lambda: self.generate_new_set("Ranked"),
            "Unranked": lambda: self.generate_new_set("Unranked"),
            "Quick": lambda: self.generate_new_set("Quick"),
            "Just Generate": lambda: self.generate_new_set("Just Generate"),
            "Backup": self.generate_backup_ops,
            "Copy": self.copy_to_clipboard
        }

        for mode in modes:
            Button(
                self.button_frame, 
                text=mode, 
                bg=BUTTON_BG_COLOR, 
                fg=BUTTON_TEXT_COLOR, 
                font=FONT_STYLE,
                relief='raised', # Changed from 'flat' for a more standard button look
                padx=10,
                pady=5,
                command=commands[mode]
            ).pack(side='left', padx=5)

    def generate_new_set(self, mode):
        """Generates a new set of operators for the main rounds."""
        self.last_mode = mode
        round_count = ROUND_COUNT.get(mode, 0)
        
        # Store the generated operators
        self.generated_rounds["attackers"] = random.sample(ATTACKERS, round_count)
        self.generated_rounds["defenders"] = random.sample(DEFENDERS, round_count)
        
        # Update the UI display
        self.display_round_operators()

    def generate_backup_ops(self):
        """Generates a new set of backup operators."""
        # Store the generated backup operators
        self.generated_backups["attackers"] = random.sample(ATTACKERS, BACKUP_COUNT)
        self.generated_backups["defenders"] = random.sample(DEFENDERS, BACKUP_COUNT)
        
        # Update the UI display
        self.display_backup_operators()

    def display_round_operators(self):
        """Clears the main frame and displays the round operator data."""
        parent_frame = self.output_frame
        data = self.generated_rounds

        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"] or not data["defenders"]:
            return

        # --- Headers ---
        Label(parent_frame, text="", bg=BG_COLOR, font=FONT_STYLE).grid(row=0, column=0)
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"Round {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        # --- Attacker Row ---
        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        # --- Defender Row ---
        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)
            
        # Configure columns to have equal weight so they space out nicely
        for i in range(len(data["attackers"]) + 1):
            parent_frame.grid_columnconfigure(i, weight=1)

    def display_backup_operators(self):
        """Clears the backup frame and displays backup operators in a simple list."""
        parent_frame = self.backup_frame
        data = self.generated_backups

        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"] or not data["defenders"]:
            return

        # --- Attacker Row ---
        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=0, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=0, column=i+1)

        # --- Defender Row ---
        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=1, column=i+1)

        # Configure columns to have equal weight
        for i in range(len(data["attackers"]) + 1):
            parent_frame.grid_columnconfigure(i, weight=1)


    def copy_to_clipboard(self):
        """Formats and copies the generated operators to the clipboard."""
        self.win.clipboard_clear()
        
        # Build the text from our stored data, not from the UI
        rounds_text = []
        if self.generated_rounds["attackers"]:
            for i in range(len(self.generated_rounds["attackers"])):
                attacker = self.generated_rounds["attackers"][i]
                defender = self.generated_rounds["defenders"][i]
                rounds_text.append(f"Round {i+1}\nA={attacker}\nD={defender}")
        
        backup_text = ""
        if self.generated_backups["attackers"]:
            attackers_str = ', '.join(self.generated_backups["attackers"])
            defenders_str = ', '.join(self.generated_backups["defenders"])
            backup_text = f"\nBackup\nA={attackers_str}\nD={defenders_str}"
            
        full_text = "\n\n".join(rounds_text) + "\n" + backup_text
        self.win.clipboard_append(full_text.strip())
        print("Copied to clipboard!") # For debugging

    def setup_hotkeys(self):
        """Sets up the global hotkeys to re-run the generator."""
        # Using a try-except block is good practice in case the hotkey is already registered by another program.
        try:
            keyboard.add_hotkey('f13', self.reactivate_last_mode)
            keyboard.add_hotkey('ctrl+scroll lock', self.reactivate_last_mode)
        except Exception as e:
            print(f"Could not set up hotkeys: {e}")

    def reactivate_last_mode(self):
        """Re-runs the last used generation mode."""
        print(f"Reactivating: {self.last_mode}")
        if self.last_mode is not None:
            self.generate_new_set(self.last_mode)

    def run(self):
        """Starts the Tkinter main loop."""
        self.win.mainloop()


# --- Main Execution ---
if __name__ == "__main__":
    app = R6OperatorGenerator()
    app.run()
