# Music-Life

Music-Life is a Python/Pygame music-career simulation prototype. The current codebase already contains world data, character creation, exploration, songwriting, gigs, travel, charts, staff, merch, and NPC systems, but those systems are not yet fully hardened into a complete game.

## Current state

- The game starts and loads into character creation.
- World data currently loads successfully.
- The project has a small passing test suite.
- The overall experience is still under active reconstruction toward a stable vertical slice.

## Requirements

- Python 3.11+
- `pip`
- A desktop environment for Pygame

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Tests

```bash
python -m pytest -q
```

## AI dialogue

NPC dialogue currently references Google's deprecated `google-generativeai` package and reads configuration from `config.py`. This should be treated as optional during development. The game should remain playable even if no API key is configured.

## Project layout

- `main.py`: app entrypoint
- `game/game.py`: main game coordinator and state machine
- `game/pygame_ui.py`: Pygame UI and menu rendering
- `game_data/`: authored world and catalog data
- `tests/`: current automated tests
- `progress.md`: active rebuild plan and working notes

## Rebuild target

The first milestone is not "every feature complete." The first milestone is a stable playable loop:

1. Create a character.
2. Explore the starting town.
3. Write a song.
4. Record and release it.
5. Play gigs.
6. Earn money and fame.
7. Progress toward travel and larger opportunities.
