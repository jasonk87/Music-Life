import pygame
from game.pygame_ui import PygameUI
from game.game import Game

def main():
    ui = PygameUI()
    game = Game(ui)

    if not game.setup_world():
        print("World setup failed. Check log.")
        return

    game.initialize_player()
    game.ui.clear_screen()
    game.ui.draw_hud(game.ui.get_current_time_str(date_only=True), str(game.player.money), game.player.hair_length, game.player.beard_length)
    game.ui.draw_log()
    game.handle_main_menu()
    pygame.image.save(game.ui.screen, "jules-scratch/verification/screenshot.png")

if __name__ == "__main__":
    main()
