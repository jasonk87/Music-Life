from game.game import Game
from game.pygame_ui import PygameUI

class DummyUI:
    def __init__(self):
        self.messages = []
    def add_log_message(self, message):
        self.messages.append(message)
    def add_message(self, message):
        self.messages.append(message)
    def present_choices(self, opts, msg):
        return list(opts.keys())[0]
    def clear_messages(self):
        pass

game = Game(DummyUI())
# Just checking if it loads without issues
print("Imports and init works!")
