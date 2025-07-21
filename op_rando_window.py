# Import necessary libraries 
import random
from tkinter import Tk, Frame, Label, Button, Entry
import keyboard

# --- Operator Lists ---
# Fully updated and chronologically ordered based on your provided list.
ATTACKERS = ["Striker", "Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", "Blitz", "IQ", "Buck", "Blackbeard", "CAPITÃO", "Hibana", "Jackal", "Ying", "Zofia", "Dokkaebi", "Lion", "Finka", "Maverick", "Nomad", "Gridlock", "NØKK", "Amaru", "Kali", "Iana", "Ace", "Zero", "Flores", "Osa", "Sens", "Grim", "Brava", "Ram", "Deimos", "Rauora"]
DEFENDERS = ["Sentry", "Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Kapkan", "Tachanka", "Jäger", "Bandit", "Frost", "Valkyrie", "Caveira", "Echo", "Mira", "Lesion", "Ela", "Vigil", "Maestro", "Alibi", "Clash", "Kaid", "Mozzie", "Warden", "Goyo", "Wamai", "Oryx", "Melusi", "Aruni", "Thunderbird", "Thorn", "Azami", "Solis", "Fenrir", "Tubarão", "Skopós"]


# --- Configuration Constants ---
ROUND_COUNT = {"Ranked": 9, "Unranked": 9, "Quick": 5, "Just Generate": 1}

# --- GUI Styling Constants ---
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
        # Hide the window until it's fully sized and configured.
        self.win.withdraw()

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
        # Calculate and set the fixed window size while it's hidden
        self.fix_window_size()
        # Now that everything is set up, make the window visible
        self.win.deiconify()

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

    def fix_window_size(self):
        """
        Calculates the required window size based on the longest operator names
        and max rounds, then fixes the window size. This happens before the window is shown.
        """
        # 1. Find the longest names and max rounds (from Ranked mode)
        longest_attacker = max(ATTACKERS, key=len)
        longest_defender = max(DEFENDERS, key=len)
        max_rounds = ROUND_COUNT["Ranked"]

        # 2. Create dummy data with the longest names for sizing
        dummy_rounds = {
            "attackers": [longest_attacker] * max_rounds,
            "defenders": [longest_defender] * max_rounds
        }
        # The number of backups will match the max number of rounds for sizing
        dummy_backups = {
            "attackers": [longest_attacker] * max_rounds,
            "defenders": [longest_defender] * max_rounds
        }

        # 3. Temporarily store original data and set dummy data
        original_rounds = self.generated_rounds
        original_backups = self.generated_backups
        self.generated_rounds = dummy_rounds
        self.generated_backups = dummy_backups

        # 4. Populate the frames with this max-size content to measure it
        self.display_round_operators()
        self.display_backup_operators()

        # 5. Force the UI to update and calculate its required size
        self.win.update_idletasks()
        width = self.main_container.winfo_reqwidth()
        height = self.main_container.winfo_reqheight()

        # 6. Set the final, fixed geometry and make the window non-resizable
        self.win.geometry(f"{width + 20}x{height + 20}")
        self.win.resizable(False, False)

        # 7. Clear the frames so the window starts up blank and clean
        for widget in self.output_frame.winfo_children():
            widget.destroy()
        for widget in self.backup_frame.winfo_children():
            widget.destroy()

        # 8. Restore the original (empty) data structures
        self.generated_rounds = original_rounds
        self.generated_backups = original_backups

    def generate_new_set(self, mode):
        """Generates a new set of operators for the main rounds and a backup set."""
        self.last_mode = mode
        round_count = ROUND_COUNT.get(mode, 0)

        # Check if there are enough unique operators for main + backup lists
        if len(ATTACKERS) < round_count * 2 or len(DEFENDERS) < round_count * 2:
            print(f"Not enough operators to generate a main and backup list for mode '{mode}'.")
            self.generated_rounds = {"attackers": [], "defenders": []}
            self.generated_backups = {"attackers": [], "defenders": []}
            self.display_round_operators()
            self.display_backup_operators()
            return

        # Generate main list
        main_attackers = random.sample(ATTACKERS, round_count)
        main_defenders = random.sample(DEFENDERS, round_count)
        self.generated_rounds["attackers"] = main_attackers
        self.generated_rounds["defenders"] = main_defenders
        
        # Determine remaining operators for backups
        available_attackers_for_backup = [op for op in ATTACKERS if op not in main_attackers]
        available_defenders_for_backup = [op for op in DEFENDERS if op not in main_defenders]
        
        # Generate backup list from the remaining operators, matching the round count
        self.generated_backups["attackers"] = random.sample(available_attackers_for_backup, round_count)
        self.generated_backups["defenders"] = random.sample(available_defenders_for_backup, round_count)
        
        # Update the display
        self.display_round_operators()
        self.display_backup_operators()

    def display_round_operators(self):
        """Clears the main frame and displays the round operator data."""
        parent_frame = self.output_frame
        data = self.generated_rounds

        # Clear any existing widgets in the frame
        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"]: return

        # Grid layout for operators
        Label(parent_frame, text="", bg=BG_COLOR).grid(row=0, column=0)
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"Round {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)
            
        # Ensure columns resize equally to fill space
        for i in range(len(data["attackers"]) + 1):
            parent_frame.grid_columnconfigure(i, weight=1)

    def display_backup_operators(self):
        """Clears the backup frame and displays backup operators with a section header."""
        parent_frame = self.backup_frame
        data = self.generated_backups

        # Clear any existing widgets in the frame
        for widget in parent_frame.winfo_children():
            widget.destroy()

        if not data["attackers"]: return

        # "Backup" title
        Label(parent_frame, text="Backup", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=0, column=0, sticky='w')

        # Use "Back" + number for backup headers
        for i in range(len(data["attackers"])):
            Label(parent_frame, text=f"Back {i+1}", bg=BG_COLOR, font=FONT_STYLE, fg=HEADER_TEXT_COLOR, pady=5).grid(row=0, column=i+1)

        # Display backup operators
        Label(parent_frame, text="Attacker", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=1, column=0, sticky='w')
        for i, op in enumerate(data["attackers"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=ATTACKER_OP_COLOR).grid(row=1, column=i+1)

        Label(parent_frame, text="Defender", bg=BG_COLOR, font=FONT_STYLE, fg=SIDE_LABEL_COLOR, padx=10).grid(row=2, column=0, sticky='w')
        for i, op in enumerate(data["defenders"]):
            Label(parent_frame, text=op, bg=BG_COLOR, font=FONT_STYLE, fg=DEFENDER_OP_COLOR).grid(row=2, column=i+1)

        # Ensure columns resize equally
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
            keyboard.add_hotkey('f14', self.reactivate_last_mode)
            keyboard.add_hotkey('f15', self.reactivate_last_mode)
            keyboard.add_hotkey('f16', self.reactivate_last_mode)
            keyboard.add_hotkey('f17', self.reactivate_last_mode)
            keyboard.add_hotkey('ctrl+scroll lock', self.reactivate_last_mode)
        except Exception as e:
            print(f"Could not set up hotkeys: {e}")

    def reactivate_last_mode(self):
    #"""Re-runs the last used generation mode safely on the GUI thread."""
        if self.last_mode:
            print(f"Reactivating: {self.last_mode}")
            # Schedule the GUI update on the main thread to avoid threading issues
            self.win.after(0, lambda: self.generate_new_set(self.last_mode))

    def run(self):
        """Starts the Tkinter main loop."""
        self.win.mainloop()


# --- Main Execution ---
if __name__ == "__main__":
    app = R6OperatorGenerator()
    app.run()
