Original prompt: lets do all of this one go. produce a fully functional game

# Music-Life Progress

## Current status

- The game boots, loads world data, and reaches character creation.
- `python -m pytest -q` passes the current 7 tests.
- The project is not yet a fully functional game. It is a large prototype with many partially integrated systems.

## Verified baseline

- Entrypoint: `main.py`
- Core coordinator: `game/game.py`
- UI loop: `game/pygame_ui.py`
- Data loads successfully from `game_data/`
- Current runtime can initialize:
  - 3 locations
  - 12 NPCs
  - 2 charts

## Major blockers

- Scope is too broad for the current architecture.
- `game/game.py` is monolithic and mixes state handling, simulation, progression, and UI flow.
- AI dialogue depends on a deprecated Gemini package and a manual API key in `config.py`.
- Save/load uses pickle on a large object graph, which is brittle.
- Tests cover only a small part of the simulation.
- README is effectively empty, so setup and expected behavior are undocumented.

## Delivery strategy

### Milestone 1: Runnable baseline

- Add real setup and run documentation.
- Make the game playable without external AI configuration.
- Harden startup and failure paths.
- Preserve current world-loading behavior.

### Milestone 2: Early-game vertical slice

- Complete a reliable loop:
  - create character
  - explore town
  - write a song
  - record and release it
  - play gigs
  - gain money and fame
- Remove or gate unfinished late-game branches that break flow.

### Milestone 3: Systems hardening

- Refactor `Game` into smaller state/scene modules.
- Extract simulation logic from Pygame menu code.
- Add tests for core progression and save/load.

### Milestone 4: Expansion

- Travel and second-city progression
- richer events and NPC interactions
- labels, tours, rivals, staff depth
- economy and balance pass

## Immediate implementation order

1. Expand README with actual setup and project state.
2. Remove hard dependency on Gemini for basic play.
3. Audit startup and menu transitions for the first playable loop.
4. Add tests around world boot and early progression.

## Completed in this pass

- Added a real project README with setup, run, and rebuild-target documentation.
- Added offline NPC dialogue fallback so missing API config no longer blocks play.
- Moved AI SDK import to runtime so the game no longer emits the Gemini deprecation warning on normal import paths.
- Added bootstrap coverage for headless world initialization.
- Added dialogue coverage for offline fallback behavior.
- Fixed label-deal acceptance to write into `player.signed_label_deal` instead of a nonexistent field.
- Attached `label_poi_id` to generated contracts so downstream chart logic can identify label-backed releases.
- Replaced the outdated startup log line about Ollama with the current dialogue behavior.
- Fixed interaction timing so menu transitions do not consume time before the real action starts.
- Centralized time advancement through a helper that also applies player needs.
- Added scheduled gig activation so calendar gigs can promote into the performance scene.
- Added stable event IDs and wired scheduled gigs to real venue events.
- Normalized manager tour opportunities to the same opportunity data shape used elsewhere.
- Added performance preflight checks before entering gigs.
- Added setlist tracking in the performance scene and aligned gig rewards with event payout/fame values.

## Current verified baseline

- `python -m pytest -q` passes with 15 tests.
- The game can initialize headlessly into character creation.
- NPC dialogue works without external AI configuration.

## Notes for next pass

- Do not try to stabilize every late-game system at once.
- Treat the first target as a complete playable vertical slice, not a content-complete simulation.

## Completed since baseline

- Added a progression-aware HUD with live "next step" guidance.
- Reworked shared choice screens so menus can show contextual side panels instead of plain debug lists.
- Added a dedicated Career Overview screen with current standing, milestone progress, and next opportunity thresholds.
- Updated the main menu and explore menu to present the player's situation and likely next move more clearly.
- Added a harsher survival layer with weekly living costs, unpaid-week pressure, health tracking, and a real run-ending collapse/death state.
- Added run-to-run variance through a hidden luck profile and weekly life events, including hard-luck weeks, side-hustle breaks, and rare viral jumps.
- Made low-wage shift work more grounded by tying pay and physical cost to the player's condition and run luck.
- Added housing instability and eviction pressure, plus rough-sleep fallback so losing your apartment changes the run instead of just changing a number.
- Expanded survival-job coverage in hometown and City Center so the player has more grounded ways to scrape together money.
- Added condition-based consequence events like sickness, theft, and burnout to make bad planning feel materially dangerous.
- Replaced the remaining run-level luck shortcuts with contextual roll thresholds driven by current state instead of a hidden fate variable.
- Moved media, gigs, demo responses, ally opportunities, NPC career actions, and chart drift further onto the same probability model.
