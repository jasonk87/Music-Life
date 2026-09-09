# Making Music Life feel like a life

The design goal is fewer routine confirmations and more decisions with consequences. Increasing the number of dialogue choices does not, by itself, make an activity deeper.

## Implemented in the September 8 activity pass

- Passenger phone: actual calendar, booking desk, scene feed and chosen contacts. Browsing is free; calls and booking administration consume journey time. A call that outlasts the route finishes at the destination.
- Travel continuation: advance to arrival, road trouble, a calendar boundary or deteriorating condition without confirming each hour. Delays use the same clock as the rest of the career. Drivers need a capable hired driver to use passenger actions.
- Signing scene: turnout, queue, pace, attention, walkouts, stock, receipts and condition. Up to four decisions cover an entire appearance. Empty queues end the activity without redundant prompts. Completed appearances persist as career and world-memory records.

The first spatial shop slice is now implemented in `game/shop_scene.py` and `game/shop_life.py`. Shop signings advance minute by minute with visible queues, physical service position, pause/speed controls, recurring locals and a persistent host. Purchases, repairs, conversations and phone work share the world clock. Mid-signing saves restore the queue, player position and pending decision. The older menu appearance path remains for non-spatial UI integrations.

This remains a small scene and encounter pool. All shops share a room layout. Named regulars persist individually; anonymous attendees are queue entries, not full NPCs. Clubs and bar stages now use a second spatial scene with shared time, preparation, crew work and performance consequences. Wider career playtesting and economic balance are still needed.

## Playable places: shops and small clubs delivered

The music shop and club are the first spatial scenes, with the existing calendar and simulation underneath them. Show the stage, entrance, counter, backstage area and nearby people. Clicking a person opens a context-specific exchange; clicking an object opens a relevant action. The scene should show changes such as the queue length, people leaving, a delayed bandmate or a promoter waiting by the stage.

Movement should answer a question: whom can I reach, what can I overhear, and what am I leaving unattended? Avoid adding long walks between ordinary buttons. A one-room scene with credible people is a better first target than a large empty city.

The phone becomes an overlay on that scene and on the journey view. Catalogs, finances and the calendar remain menus because they are records a musician would actually consult. Activities take place in scenes.

## Set intentions, intervene at meaningful moments

Let the player set a pace or approach once. Ordinary work then proceeds under that policy. Interrupt when circumstances create a decision: a queue is becoming unmanageable, a fan asks for something unusual, a bandmate is late, the equipment starts failing, or a rival arrives.

Provide pause and speed controls for routine stretches. Do not impose real-world waiting time to fill a journey. Optional onboard writing, calls, setlist preparation and rest should compete for the same available time and energy. Some activities can continue after arrival; others need to be packed away before the player leaves the vehicle.

Repeated choices should change context. A regular fan can remember being rushed last time. A shop owner can offer another appearance after a well-run session. A promoter may hesitate after a missed date. These consequences should feed future opportunities and relationships, not only a recap score.

## Concrete next slices

1. **Expand the delivered shop.** Add encounter variety, stronger individual visitor routines and more visual identity between stores. The first slice already carries relationships and signing results into local turnout and repeat invitations.
2. **Expand the delivered club night.** Soundcheck, monitor faults, a prepared merch table, promoter and regular conversations, scheduled doors and concurrent crew preparation now affect the actual show. Stage choices remain visible in the room, and settlement persists. Next add band disagreements, more specific audience reactions and different room identities. Current crowd animation and a three-action performance model still need wider playtesting; spatial presentation alone does not establish depth.
3. **A studio session with revisions.** Listen to or inspect takes, choose where to spend limited studio time, negotiate arrangement disagreements and decide when a recording is good enough. Better equipment cannot erase an exhausted performance. Short authored audio previews would give this activity a sensory dimension before attempting generated music.

Avoid giving each system its own disconnected reflex minigame. A signing does not need repeated mouse signatures; a journey does not need repeated “continue” clicks. Familiar routine actions should become faster as the player and their staff become more experienced.

## Keep the sandbox demanding

Show facts the character could reasonably observe: queue, clock, money, energy, contractual terms and people's behavior. Do not mark a best choice or prescribe a sequence of objectives. Leave personalities and exact outcomes uncertain, but explain enough afterward that the player can connect a result to their decisions.

For every new activity, check:

- Would two plausible approaches lead to meaningfully different careers or relationships?
- Can the player change course when circumstances change?
- Does an ordinary stretch run without repeated approval?
- Does the rest of the world keep its commitments and clock?
- Does the player see the situation before being asked to act?
- Will any of this matter the next time they visit?

Test through multi-week careers, including mundane and unsuccessful runs. Passing interaction tests establishes correctness; it does not establish that the rhythm is fun or the economy balanced.
