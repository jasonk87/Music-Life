import pygame
from game.pygame_ui import PygameUI
from game.game import Game

def main():
    ui = PygameUI()
    game = Game(ui)
    game.run()

if __name__ == "__main__":
    main()
