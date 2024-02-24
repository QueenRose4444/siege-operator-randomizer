# Import necessary libraries 
# test
import random
from tkinter import Tk, Frame, Label, Button
import keyboard

# Define constants
# List of attacker and defender operators
ATTACKERS = ["Ram", "Brava", "Grim", "Sens", "Osa", "Flores", "Zero", "Ace", "Iana", "Kali", "Amaru", "Nokk", "Gridlock", "Nomad", "Maverick", "Lion", "Finka", "Dokkaebi", "Zofia", "Ying", "Jackal", "Hibana", "Capito", "Blackbeard", "Buck", "Sledge", "Thatcher", "Ash", "Thermite", "Montagne", "Twitch", "Blitz", "Iq", "Fuze", "Glaz"]
DEFENDERS = ["Tubarao", "Fenrir", "Solis", "Azami", "Thorn", "Thunderbird", "Aruni", "Melusi", "Oryx", "Wamai", "Goyo", "Warden", "Mozzie", "Kaid", "Clash", "Maestro", "Alibi", "Vigil", "Ela", "Lesion", "Mira", "Echo", "Caveira", "Valkrie", "Frost", "Mute", "Smoke", "Castle", "Pulse", "Doc", "Rook", "Jager", "Bandit", "Tachanka", "Kapkan"]

# Number of rounds for each game mode
ROUND_COUNT = {"Ranked": 9, "Standard": 7, "Quick": 5, "Just Generate": 1}
BACKUP_COUNT = 4

# GUI styling constants
FONT = (None, 12, 'bold')
BG_COLOR = 'black'
FG_COLOR = 'violet'
BUTTON_COLOR = 'green'
TEXT_COLOR = 'white'

# Row numbers for attackers and defenders
ATTACKER_ROW = 1
DEFENDER_ROW = 2

# Main class for the operator generator
class R6OperatorGenerator:
    def __init__(self):
        # Initialize the last mode to None
        self.last_mode = None
        # Create the main window
        self.win = Tk()
        self.win.title("siege op rando")
        self.win.configure(background=BG_COLOR)
        self.win.attributes('-topmost', True)
        
        # Create the main container frame
        self.main_container = Frame(self.win, background=BG_COLOR)
        
        self.main_container.pack()
        # Initialize output and backup frames to None
        self.output_frame = None
        self.backup_frame = None
        
        # Create the widgets and setup hotkeys
        self.create_widgets()
        self.setup_hotkeys()

    # Method to create the widgets
    def create_widgets(self):
        self.create_buttons()
        self.create_output_frame()

    # Method to create the buttons
    def create_buttons(self):
        button_frame = Frame(self.main_container, background=BG_COLOR)
        button_frame.grid(row=1, column=0)
        modes = ["Ranked", "Standard", "Quick", "Just Generate", "backup", "copy"]
        for i, mode in enumerate(modes):
            Button(button_frame, text=mode, bg=BUTTON_COLOR, fg=TEXT_COLOR, font=FONT, command=lambda m=mode: self.mode(m)).grid(row=0, column=i)

    # Method to create the output frame
    def create_output_frame(self):
        self.output_frame = Frame(self.main_container, background=BG_COLOR)
        self.output_frame.grid(row=0, column=0)

        self.backup_frame = Frame(self.main_container, background=BG_COLOR)
        self.backup_frame.grid(row=2, column=0)

    # Method to handle mode selection
    def mode(self, selected_mode):
        if selected_mode not in ["backup", "copy"]:
            self.last_mode = selected_mode
            self.clear_PR()
            self.generate_rounds(selected_mode)
        elif selected_mode == "copy":
            self.copy_to_clipboard()
        else:
            self.backup_gen_out()
            
    # Method to generate rounds based on the selected mode
    def generate_rounds(self, mode):
        round_count = ROUND_COUNT.get(mode, 0)
        attackers = random.sample(ATTACKERS, round_count)
        defenders = random.sample(DEFENDERS, round_count)

        for col in range(round_count):
            round_label = self.create_label(self.output_frame, text=f"Round {col + 1}", fg="red")
            round_label.grid(row=0, column=col + 1)

        for row, op_type in enumerate(["Attacker", "Defender"], start=1):
            type_label = self.create_label(self.output_frame, text=op_type, fg="yellow")
            type_label.grid(row=row, column=0)

            for col in range(round_count):
                op = attackers[col] if row == 1 else defenders[col]
                op_label = self.create_label(self.output_frame, text=op)
                op_label.grid(row=row, column=col + 1)

    # Method to generate backup operators
    def backup_gen_out(self):
        if self.backup_frame:
            self.backup_frame.destroy()
            self.backup_frame = Frame(self.main_container, background=BG_COLOR)
            self.backup_frame.grid(row=2, column=0)
    
        self.create_backup_labels("Attacker", BACKUP_COUNT)
        self.create_backup_labels("Defender", BACKUP_COUNT)

    # Method to create backup labels
    def create_backup_labels(self, op_type, count):
        ops = random.sample(ATTACKERS if op_type == "Attacker" else DEFENDERS, count)
        type_label = self.create_label(self.backup_frame, text=op_type, fg="yellow")
        type_label.grid(row=1 if op_type == "Attacker" else 2, column=0)

        for i, op in enumerate(ops):
            op_label = self.create_label(self.backup_frame, text=op)
            op_label.grid(row=1 if op_type == "Attacker" else 2, column=i + 1)

    # Method to clear the output frame
    def clear_PR(self):
        if self.output_frame:
            for widget in self.output_frame.winfo_children():
                widget.destroy()

    # Method to create a label
    def create_label(self, frame, text="", fg=FG_COLOR, font=FONT):
        return Label(frame, text=text, fg=fg, padx=10, pady=0, bd=0, background=BG_COLOR, highlightthickness=0, font=font)

    # Method to copy the generated operators to the clipboard
    def copy_to_clipboard(self):
        self.win.clipboard_clear()
        rounds_text = self.get_rounds_text()
        backup_text = self.get_backup_text()
        self.win.clipboard_append(rounds_text + "\n" + backup_text)
        
    # Method to get the text of a widget
    def get_widget_text(self, frame, row, column):
        widgets = frame.grid_slaves(row=row, column=column)
        return widgets[0].cget('text') if widgets else ''

    # Method to get the text for all rounds
    def get_rounds_text(self):
        round_widgets = []
        for i in range(len(self.output_frame.grid_slaves(row=ATTACKER_ROW)) - 1):
            round_text = f"Round {i+1}\nA={self.get_widget_text(self.output_frame, ATTACKER_ROW, i+1)}\nD={self.get_widget_text(self.output_frame, DEFENDER_ROW, i+1)}"
            round_widgets.append(round_text)
        return "\n\n".join(round_widgets)

    # Method to get the text for the backup operators
    def get_backup_text(self):
        attackers_text = ', '.join([self.get_widget_text(self.backup_frame, ATTACKER_ROW, i + 1) for i in range(BACKUP_COUNT)])
        defenders_text = ', '.join([self.get_widget_text(self.backup_frame, DEFENDER_ROW, i + 1) for i in range(BACKUP_COUNT)])
        return f"\nBackup\nA={attackers_text}\nD={defenders_text}"

    # Method to setup hotkeys
    def setup_hotkeys(self):
        keyboard.add_hotkey('f13', self.reactivate_last_mode)
        keyboard.add_hotkey('ctrl + scroll lock', self.reactivate_last_mode)

    # Method to reactivate the last mode
    def reactivate_last_mode(self):
        print(f"Reactivating:", self.last_mode)
        if self.last_mode is not None:
            if self.last_mode == "Just Generate":
                self.mode(self.last_mode)

# Main execution
if __name__ == "__main__":
    R6OperatorGenerator().win.mainloop()
