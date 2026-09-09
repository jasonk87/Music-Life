Original prompt: lets do all of this one go. produce a fully functional game

# Music-Life Progress

## Playable club night — 2026-09-08

Verification: **392 passing tests**, including 26 club regressions. A real Pygame input playthrough covered mouse approach, soundcheck, doors, set selection, stage choices, settlement and Explore entry/exit. Seven screens were rendered and visually reviewed; load-in and performance captures are included under docs/screenshots.

- Clubs and bar stages use a walkable room with violet and amber stage lighting, drums and amplifiers, sound desk, merchandise, a green room and recurring people. Shared shop movement supports scene-specific furniture and targets.
- Soundcheck, monitor repairs, merchandise preparation and conversations spend real career time. Existing hired crew can work concurrently; assignments survive save/load, preserve staff identity, and stop when staff are removed.
- Doors and set windows follow the calendar. Crowd arrival starts after doors, and lateness reduces turnout and opening response. Arriving at a venue does not automatically start the set in the spatial UI.
- Stage choices remain in the room. Soundcheck and crowd connection affect performance, merchandise needs a prepared table, and redundant section confirmation clicks are removed. Tab retains full feedback and action descriptions.
- Shows leave promoter memories and world-history records. Played, withdrawn and prepared missed slots close once; the completed booking stays visible afterward instead of silently resetting the room to another public slot.
- All earlier shop, touring, travel, save and career tests pass. Existing running sessions and player saves were left intact.

Scope: clubs share one layout, crowds are grouped simulation, and larger venues retain their existing interface. This pass adds consequences and continuity; it does not claim the remaining performance loop or career economy is fully balanced.


## Playable music shop — 2026-09-08

Verification: **366 passing tests**, including 23 shop regressions. Real Pygame mouse/keyboard handlers and the full Explore → shop → exit event loop were exercised. Five rendered screens were inspected; two are included under docs/screenshots. No running player session was replaced.

- Replaced music-shop Explore menus with a walkable room in the desktop UI: counter, record bins, repair bench, signing table and exit. Click furniture or people to approach via navigation around solid furniture; WASD/arrows, E, Tab/Enter and mouse controls work.
- Added persistent shop hosts and three individually named regulars per shop; returning conversations, daily conversation limits, signature memories, relationship-dependent turnout and host responses to past appearances. Released artists can ask for a local signing without a tour.
- Shop signings now advance minute by minute under a pace policy. Queue service requires presence at the table; stepping away or doing phone work lets it wait. Walkouts, stock-limited sales, energy costs and closing-time decisions feed the existing appearance history and world memory.
- Added pause/1x/4x/12x controls, automatic pauses for meaningful decisions and calendar boundaries, inline conversation panels, and accessible calendar/phone controls.
- Added safe mid-signing save/resume: canonical POI data stores the active queue, pending decision and saved position. A loaded active signing re-enters the shop paused. Leaving closes and settles the remaining queue once.
- Preserved authored shop stock and loadout capacity checks; purchases clone catalog items. Repairs remain available in the room.

The room and encounter pool are deliberately small. Shops currently share a layout; the club scene remains future work. Anonymous attendees are queue entries, while named locals persist as NPCs. Broader career balance is not established by regression tests.

## Travel, appearances and menu fixes — 2026-09-08

Verification: **343 passing tests**, including 19 new travel/appearance regressions. Actual Pygame keyboard input verified an entire signing through settlement and a passenger phone call; screenshots were inspected. Existing in-memory game sessions were left running.

- Repaired the unhandled contact-details phone state. Contacts now support chosen, timed calls with persistent memories and a daily relationship-gain limit.
- Repaired unreachable dynamic guest-feature invitations; review/decline or record at home or an authored recording studio. Completed invitations cannot pay twice.
- Connected the passenger phone to actual calendar, news, booking and contact systems. Reading costs no simulation time; committed remote actions share the journey clock. Presence is cleared while en route.
- Added continuous travel to arrival or interruption, with exact partial final legs, timed road delays and fractional vehicle risk. Calls can finish at the destination. Rest benefits scale with actual time.
- Replaced instant signing rewards with turnout, policy-dependent throughput, fan attention, walkouts, fatigue, stock-limited sales and closing-time decisions. Visible queue/time/receipts, saved appearance history and world memory; local cooldowns and renewed invitations point to the correct city.
- Fixed calendar day/week queries to use the game's 30-day months, including February 30.
- Added docs/ACTIVITY_DESIGN.md: next proposed work is spatial shop/venue scenes, recurring people, activity policies and delegation. The current signing is a small menu-based scene, not a full crowd or real-time place simulation.

No commits or user save replacement were performed. Backup before this pass is in the Codex thread workspace. Broader repository whitespace warnings in unrelated pre-existing files were left intact.

## Live bookings and touring pass — 2026-09-08

Current verification: **324 passing tests**, including 16 new live-booking regressions. The earlier playable build and all existing user work remain intact.

- Added Phone → Live bookings & settlements. Quote local shows and all authored tour itineraries before acceptance, with explicit dates, rooms, set requirements, guarantees, booking fees, minimum known fares, and baseline grocery/lodging costs.
- Replaced partial tour mutations with full validation before booking; unavailable venues, insufficient funds, expired quotes, and conflicting dates leave the calendar and wallet intact. Reopening a quote on the same game day returns the same itinerary.
- Local bookings can coexist with a tour and settle independently. Agent and dynamic tour offers now use the same review path. Established artists can still choose smaller routes.
- Added idempotent show settlement and cancellation, including missed/unavailable venues, last-date closure, current-tour release, completed-tour history, and recovery of old stranded active tour records.
- Completed sets receive their contracted minimum. Ledgers distinguish show receipts, booking/rental charges, and whole-career cash change so streaming, meals, and other activity are not mislabeled as tour profit.
- Added explicit whole-setlist sequencing and paid temporary venue gear. Rental gear is returned after the show without mutating shop inventory.
- Kept future booked events intact when venue management changes.

Tests include a complete two-date tour through performance menus, saving between dates and loading a fresh game; local-show settlement alongside a running tour; expired/conflicting/declined offers; all authored routes; missed dates; cancellations; rental payment/return; selected set order; and dynamic phone offers.

Remaining broader work includes multi-year economic balance, more regional scene identity, and further integration of advanced late-career systems. Existing game windows keep their loaded version until restarted; no active session was closed during this pass.

## Playability and presentation pass — 2026-09-07

This entry supersedes the early status notes below. Baseline at the start of this pass: 283 passing tests, substantial existing work preserved. Current verification: **308 passing tests** (including 25 new career/menu regressions).

Delivered:
- Shared illustrated title/menu shell, readable typography, mouse/keyboard paging, factual HUD, full context documents, persistent journal, and cancellation that never silently accepts.
- Repaired authored place actions and submenu dispatch for rest, practice, home demos, food, services, venues, and transit. Fixed physical bus/airport category recognition and ticket cancellation.
- Optional single-shift listings with attendance requirements; no assigned starting job or automatic transport. Career record replaces the prescribed next-objective screen.
- Resumable song drafts with separate lyrics, melody, and arrangement sessions. Pause/save between sessions; writing and recording consume energy, and condition affects quality.
- Corrected flight timing, legacy vehicle speeds, and false arrivals on failed final legs; added paid fuel stops and roadside repair actions.
- Entire live setlists consume time and stamina; quality, fatigue, gear wear, and action repetition affect performance. Venue slots cannot be farmed repeatedly on the same day.
- Connected album sequencing, streaming statements, editorial submissions, press reviews, vinyl orders, and meetings/cowrites with travelling musicians.
- Daily/weekly ticks remain distinct across long actions and month boundaries. Fixed stream compounding, copied release dates, chart aging, duplicated living expenses, and rental expiry.
- Full JSON career graph with atomic writes, previous-file backup, legacy JSON loading, and restoration of relationships/shared objects. Quicksave prevents losing an active show or journey.
- Portable local launcher and documented offline setup. Original generated art and prompt provenance included.

Validation includes actual menu handlers for creation → writing → recording → release → royalties → save/fresh resume, complete gig payout, public travel/arrival and ticket cancellation, missed and attended work, ordered album release/press reviews/manufacturing, rentals crossing month boundaries, graph identity, failed-save preservation, and injected Pygame navigation events. Headless renderer captures cover the title and career menus. This does not substitute for extended manual or multi-year balance testing.

Remaining development: broader late-career integration, long-horizon economy/balance, more distinct city scenes, and further coordinator refactoring. Existing advanced modules should not be mistaken for fully integrated player-facing features.

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
