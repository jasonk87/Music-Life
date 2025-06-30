<<<<<<< SEARCH
        # print(f"DEBUG: Stress increased due to starvation. New stress: {player.stress}")


def setup_world():
    global WORLD_MAP, NPC_REGISTRY
    # Create Locations
    home_town = Location("Your Hometown", "A quiet place, good for starting out.")
    city_center = Location("City Center", "A bustling hub with more opportunities.")
    # Add more locations if desired (e.g., "The Suburbs", "University District")

    WORLD_MAP = {
        home_town.name: home_town,
        city_center.name: city_center,
    }

    # Define Venues and POIs
    # Hometown Venues
    community_hall = Venue(
        venue_id="hometown_community_hall",
        name="Community Hall",
        description="Hosts local events.",
        venue_type="HALL",
        category="VENUE_HALL",
        capacity=50,
        prestige=1,
        parent_location_id=home_town.name,
        can_rent_gear=False # Community hall doesn't rent gear
    )
    home_town.add_venue(community_hall)

    # Hometown POIs
    music_shop_home = PointOfInterest(
        poi_id="hometown_music_shop_oldtimers",
        name="Old Timer's Music Shop",
        description="Sells basic gear and instruments.",
        category="SHOP_MUSIC",
        interaction_options=["Browse items for sale", "Repair Gear", "Talk to Old Timer Joe"],
        parent_location_id=home_town.name
    )
    music_shop_home.shop_inventory_item_ids = [
        "worn_acoustic_guitar",
        "guitar_strings_basic",
        "guitar_picks_assorted"
    ]
    home_town.add_poi(music_shop_home)
    rehearsal_space_home = PointOfInterest(
        poi_id="hometown_rehearsal_garage",
        name="Garage Rehearsal Space",
        description="A bit rough but it's cheap.",
        category="REHEARSAL_STUDIO",
        interaction_options=["Book Rehearsal Slot (1 hour, $10)"], # Refined text
        parent_location_id=home_town.name
    )
    home_town.add_poi(rehearsal_space_home)

    # City Center Venues
    rusty_mug_club = Venue(
        venue_id="citycenter_rustymug",
        name="The Rusty Mug",
        description="A well-known club for upcoming bands.",
        venue_type="CLUB",
        category="VENUE_CLUB",
        capacity=150,
        prestige=4,
        parent_location_id=city_center.name,
        can_rent_gear=True,
        gear_rental_fee=30, # Cost to rent at Rusty Mug
        available_rental_gear_ids=["basic_electric_guitar", "practice_amp_small"] # What they offer
    )
    city_center.add_venue(rusty_mug_club)
    grande_theater = Venue(
        venue_id="citycenter_grandetheater",
        name="Grande Concert Hall",
        description="A prestigious venue for established artists.",
        venue_type="CONCERT_HALL",
        category="VENUE_THEATER",
        capacity=1000,
        prestige=8,
        parent_location_id=city_center.name,
        can_rent_gear=True, # High-end venues often have backline
        gear_rental_fee=100,
        available_rental_gear_ids=["pro_electric_guitar", "pro_bass_guitar", "pro_amp_large", "pro_drum_kit"] # Example pro gear
    )
    city_center.add_venue(grande_theater)

    # City Center POIs
    pro_music_store = PointOfInterest(
        poi_id="citycenter_proaudio",
        name="Pro Audio Central",
        description="High-end instruments and recording gear.",
        category="SHOP_MUSIC",
        interaction_options=["Browse items for sale", "Repair Gear", "Talk to Sales Rep"],
        parent_location_id=city_center.name
    )
    pro_music_store.shop_inventory_item_ids = [
        "basic_electric_guitar",
        "practice_amp_small",
        "guitar_strings_basic",
        "guitar_picks_assorted"
        # Can add more expensive/pro items from catalog here later
    ]
    city_center.add_poi(pro_music_store)

    pr_agency_poi = PointOfInterest(
        poi_id="citycenter_sharp_pr",
        name="Sharp PR Solutions",
        description="A modern office for a boutique PR agency. They look like they mean business.",
        category="OFFICE_PR_AGENCY", # New category for PR agencies
        interaction_options=["Inquire about PR representation"],
        parent_location_id=city_center.name,
        comfort_modifier_hourly=0 # Neutral office environment
    )
    city_center.add_poi(pr_agency_poi)

    news_agency_poi = PointOfInterest(
        poi_id="citycenter_chronicle_news",
        name="City Center Chronicle",
        description="The bustling office of the city's main newspaper and online news hub.",
        category="OFFICE_NEWS_AGENCY",
        interaction_options=["Look for today's paper", "Ask for a journalist"],
        parent_location_id=city_center.name,
        comfort_modifier_hourly=-1
    )
    city_center.add_poi(news_agency_poi)

    record_label_office = PointOfInterest(
        poi_id="citycenter_indiehits_records",
        name="Indie Hits Records",
        description="A small but ambitious record label. They seem to like fresh sounds.",
        category="OFFICE_RECORD_LABEL",
        interaction_options=[], # Will be dynamically generated or set based on fame
        parent_location_id=city_center.name,
        min_fame_to_submit=75, # Lowered for easier early testing
        genres_preferred=["Indie", "Pop", "Rock", "Electronic"]
    )
    # Dynamically create interaction option text based on min_fame_to_submit
    record_label_office.interaction_options = [
        f"Submit Demo (requires {record_label_office.min_fame_to_submit} fame)",
        "Talk to A&R Rep (requires Manager)" # Placeholder for now
    ]
    city_center.add_poi(record_label_office)
    downtown_cafe = PointOfInterest(
        poi_id="citycenter_dailygrind_cafe",
        name="The Daily Grind Cafe",
        description="Popular hangout, good coffee, free Wi-Fi.",
        category="POI_CAFE",
        interaction_options=["Grab Coffee ($5)", "People Watch", "Look for Local Flyers"],
        parent_location_id=city_center.name,
        comfort_modifier_hourly=1 # Slightly comforting to be in a cafe
    )
    city_center.add_poi(downtown_cafe)

    # --- Define New Key POIs for Intra-City Travel & Player Start ---
    # Your Hometown
    player_home = PointOfInterest(
        poi_id="hometown_player_home",
        name="Your Apartment",
        description="Your starting digs. A bit small, but it's home.",
        category="HOME",
        interaction_options=["Rest (8 hours)", "Practice guitar (at home)", "Write a new song", "Relax at home (2 hours)"],
        parent_location_id=home_town.name,
        rest_quality=0.8,
        stress_modifier_hourly=-10,
        comfort_modifier_hourly=5 # Home is very comforting
    )
    home_town.add_poi(player_home)

    bus_stop_hometown = PointOfInterest(
        poi_id="hometown_bus_stop",
        name="Hometown Bus Stop",
        description="A dusty bus stop for regional travel to City Center.",
        category="TRANSPORT_BUS",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=home_town.name
    )
    home_town.add_poi(bus_stop_hometown)

    hometown_grocery = PointOfInterest(
        poi_id="hometown_bodega",
        name="Corner Bodega",
        description="A small grocery store with basic necessities.",
        category="SHOP_FOOD", # New category
        interaction_options=["Buy Food Items", "Chat with Clerk"],
        parent_location_id=home_town.name
    )
    hometown_grocery.shop_inventory_item_ids = ["food_energy_bar", "food_grocery_bag"]
    home_town.add_poi(hometown_grocery)

    hometown_fastfood = PointOfInterest(
        poi_id="hometown_diner",
        name="Greasy Spoon Diner",
        description="Cheap, fast, and... food-like substances.",
        category="FOOD_FASTFOOD",
        interaction_options=[], # Will be populated from menu_items
        parent_location_id=home_town.name
    )
    hometown_fastfood.menu_items = [
        {"display_text": "Order Greasy Breakfast ($8)", "item_id": "food_greasy_breakfast", "cost": 8, "effects": {"hunger": -50, "energy": 15, "comfort": 1}},
        {"display_text": "Order Cheap Burger ($5)", "item_id": "food_cheap_burger", "cost": 5, "effects": {"hunger": -35, "energy": 10, "comfort": -2}},
        {"display_text": "Order Water (Free)", "item_id": "food_water", "cost": 0, "effects": {"hunger": 0, "energy": 1}}
    ]
    hometown_fastfood.interaction_options = [item["display_text"] for item in hometown_fastfood.menu_items]
    home_town.add_poi(hometown_fastfood)

    # City Center
    city_airport = PointOfInterest(
        poi_id="citycenter_airport",
        name="City Center International Airport",
        description="Flights to other major cities (when you can afford them).",
        category="TRANSPORT_AIRPORT",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_airport)

    city_bus_station = PointOfInterest(
        poi_id="citycenter_bus_station",
        name="Main Bus Terminal (City Center)",
        description="Regional and long-haul bus services.",
        category="TRANSPORT_BUS",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_bus_station)

    crash_pad_motel = PointOfInterest(
        poi_id="citycenter_motel_cheap",
        name="Sleep EZ Motel",
        description="A cheap, somewhat clean room for the night. Better than the streets.",
        category="ACCOMMODATION_CHEAP",
        interaction_options=["Rent Room ($50/night)", "Sleep (8 hours, if rented)"],
        parent_location_id=city_center.name,
        rest_quality=0.4,
        stress_modifier_hourly=-2,
        comfort_modifier_hourly=-3 # Grim places can reduce comfort
    )
    city_center.add_poi(crash_pad_motel)

    starlight_studio = PointOfInterest(
        poi_id="citycenter_starlight_studio",
        name="Starlight Recording Studio",
        description="A decent local recording studio. Sessions can be booked by the hour.",
        category="STUDIO_RECORDING",
        interaction_options=["Book recording session", "Talk to Sound Engineer (if available)"],
        parent_location_id=city_center.name,
        studio_quality=0.6, # Mid-tier studio
        hourly_rate=50      # $50 per hour
    )
    city_center.add_poi(starlight_studio)

    city_grocery_super = PointOfInterest(
        poi_id="citycenter_supervalu",
        name="SuperValue Mart",
        description="A large supermarket with a wide variety of groceries.",
        category="SHOP_FOOD",
        interaction_options=["Buy Food Items"],
        parent_location_id=city_center.name,
    )
    city_grocery_super.shop_inventory_item_ids = ["food_energy_bar", "food_grocery_bag"] # Could have more/different items
    city_center.add_poi(city_grocery_super)

    city_fastfood_chain = PointOfInterest(
        poi_id="citycenter_burgerblast",
        name="Burger Blast",
        description="A generic but reliable fast food burger chain.",
        category="FOOD_FASTFOOD",
        interaction_options=[], # Will be populated from menu_items
        parent_location_id=city_center.name
    )
    city_fastfood_chain.menu_items = [
        {"display_text": "Order Blast Burger ($7)", "item_id": "food_blast_burger", "cost": 7, "effects": {"hunger": -40, "energy": 10, "comfort": 0}},
        {"display_text": "Order Value Meal ($10)", "item_id": "food_value_meal", "cost": 10, "effects": {"hunger": -60, "energy": 15, "comfort": -1}},
        {"display_text": "Order Soda ($2)", "item_id": "food_soda", "cost": 2, "effects": {"hunger": -5, "energy": 5}},
        {"display_text": "Order Water (Free)", "item_id": "food_water", "cost": 0, "effects": {"hunger": 0, "energy": 1}}
    ]
    city_fastfood_chain.interaction_options = [item["display_text"] for item in city_fastfood_chain.menu_items]
    city_center.add_poi(city_fastfood_chain)

    # city_restaurant_mid (The Cozy Nook Eatery) - for later, more complex food/social
    # For now, just grocery and fast food.


    # --- AUSTIN, TEXAS ---
    austin = Location("Austin, TX", "The Live Music Capital of the World. Keep Austin Weird!")
    WORLD_MAP[austin.name] = austin

    # Austin Venues
    austin_local_stage = Venue(
        venue_id="austin_local_stage", name="Austin Local Stage", description="A small, friendly venue for local acts.",
        venue_type="BAR_GIG", category="VENUE_CLUB", capacity=80, prestige=3, parent_location_id=austin.name
    )
    austin.add_venue(austin_local_stage)

    austin_iconic_club = Venue(
        venue_id="austin_iconic_club", name="The Sixth Street Sound", description="A legendary club on 6th Street, known for blues and rock.",
        venue_type="CLUB", category="VENUE_CLUB", capacity=250, prestige=7, parent_location_id=austin.name,
        owner_npc_id="cliff_sound_owner" # New NPC
    )
    austin.add_venue(austin_iconic_club)
    # TODO: Add events to these Austin venues later

    # Austin POIs
    austin_music_store = PointOfInterest(
        poi_id="austin_guitar_emporium", name="Austin Guitar Emporium", description="Guitars, amps, and everything in between.",
        category="SHOP_MUSIC", interaction_options=["Browse items for sale", "Repair Gear", "Talk to Staff"], parent_location_id=austin.name
    )
    austin_music_store.shop_inventory_item_ids = ["basic_electric_guitar", "pro_electric_guitar", "practice_amp_small", "guitar_strings_basic", "merch_tshirt_basic"]
    austin.add_poi(austin_music_store)

    austin_radio_station = PointOfInterest(
        poi_id="austin_kaus_radio", name="KAUS Austin Radio", description="Independent Austin radio, playing local and eclectic sounds.",
        category="MEDIA_RADIO_STATION",
        interaction_options=["Talk to DJ 'Dr. Vibes'", "Submit Demo for Airplay", "Inquire about Local Artist Spotlight"],
        parent_location_id=austin.name,
        owner_npc_id="dj_dr_vibes" # New NPC
    )
    austin.add_poi(austin_radio_station)

    austin_record_store = PointOfInterest(
        poi_id="austin_vinyl_frontier", name="Vinyl Frontier Records", description="A haven for record collectors and music lovers.",
        category="SHOP_RECORDS", # New Category, or use SHOP_MUSIC with different inventory type
        interaction_options=["Browse Records", "Talk to Clerk"], parent_location_id=austin.name
        # shop_inventory_item_ids could list specific famous (but genericized) album names or genre packs later
    )
    austin.add_poi(austin_record_store)

    austin_landmark = PointOfInterest(
        poi_id="austin_capitol_view", name="Capitol View Park", description="A park with a view of the State Capitol building.",
        category="POI_PARK", interaction_options=["Relax", "People Watch"], parent_location_id=austin.name, comfort_modifier_hourly=1
    )
    austin.add_poi(austin_landmark)

    austin_motel = PointOfInterest(
        poi_id="austin_roadside_motel", name="Austin Roadside Motel", description="Basic, clean, and affordable.",
        category="ACCOMMODATION_CHEAP", interaction_options=["Rent Room ($60/night)", "Sleep (8 hours, if rented)"],
        parent_location_id=austin.name, rest_quality=0.5, stress_modifier_hourly=-1, comfort_modifier_hourly=-2
    )
    austin.add_poi(austin_motel)

    austin_cafe = PointOfInterest(
        poi_id="austin_weird_beans_cafe", name="Weird Beans Cafe", description="A quirky cafe popular with musicians and artists.",
        category="POI_CAFE", interaction_options=["Grab Coffee ($6)", "People Watch", "Look for Gig Flyers"],
        parent_location_id=austin.name, comfort_modifier_hourly=2
    )
    austin.add_poi(austin_cafe)

    austin_bus_terminal = PointOfInterest(
        poi_id="austin_main_bus_terminal", name="Austin Main Bus Terminal", description="Connects Austin to other Texan cities and beyond.",
        category="TRANSPORT_BUS", interaction_options=["View Departures & Buy Tickets"], parent_location_id=austin.name
    )
    austin.add_poi(austin_bus_terminal)

    austin_rehearsal = PointOfInterest(
        poi_id="austin_soundcheck_rehearsal", name="SoundCheck Rehearsal Studios", description="Professional rehearsal rooms by the hour.",
        category="REHEARSAL_STUDIO", interaction_options=["Book Rehearsal Slot (1 hour, $25)"], parent_location_id=austin.name
    )
    austin.add_poi(austin_rehearsal)

    # Austin NPCs
    dj_dr_vibes = NPC(npc_id="dj_dr_vibes", name="DJ 'Dr. Vibes'", personality_key="dj_eclectic_local", home_location=austin_radio_station, current_location=austin_radio_station)
    dj_dr_vibes.schedule = {"Weekday_Afternoon": austin_radio_station, "Weekday_Evening": austin_radio_station}
    NPC_REGISTRY[dj_dr_vibes.npc_id] = dj_dr_vibes

    cliff_sound_owner = NPC(npc_id="cliff_sound_owner", name="Clifford 'Cliff' Mayes", personality_key="gruff_club_owner", # Can reuse or make specific later
                              home_location=austin_iconic_club, current_location=austin_iconic_club)
    cliff_sound_owner.schedule = {"Weekday_Evening": austin_iconic_club, "Weekend_Evening": austin_iconic_club}
    NPC_REGISTRY[cliff_sound_owner.npc_id] = cliff_sound_owner
    # Note: owner_npc_id was set on austin_iconic_club at definition.

    # --- END AUSTIN, TEXAS ---

    # Update existing locations with connections to Austin
    home_town.add_travel_connection(austin.name, cost=120, time_hours=10) # e.g., Long bus ride
    city_center.add_travel_connection(austin.name, cost=60, time_hours=6)  # e.g., Shorter bus ride / regional flight

    # Add connections from Austin to existing locations
    austin.add_travel_connection(home_town.name, cost=120, time_hours=10)
    austin.add_travel_connection(city_center.name, cost=60, time_hours=6)


    # Define Travel Connections (Location Name -> {cost, time}) # INTER-CITY
    home_town.add_travel_connection(city_center.name, cost=20, time_hours=2)
    city_center.add_travel_connection(home_town.name, cost=20, time_hours=2)

    # --- Define Intra-City POI Connections ---
    # Your Hometown Connections
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, music_shop_home.poi_id})] = {
        "walk": {"time": 15, "cost": 0},
        "bike": {"time": 5, "cost": 0, "requires_bike": True},
        "taxi": {"time": 3, "cost": 8}
    }
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, community_hall.venue_id})] = {
        "walk": {"time": 10, "cost": 0},
        "bike": {"time": 3, "cost": 0, "requires_bike": True},
        "taxi": {"time": 2, "cost": 6}
    }
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, bus_stop_hometown.poi_id})] = {
        "walk": {"time": 20, "cost": 0},
        "bike": {"time": 7, "cost": 0, "requires_bike": True},
        "taxi": {"time": 5, "cost": 10}
    }
    home_town.intra_city_poi_connections[frozenset({music_shop_home.poi_id, community_hall.venue_id})] = {
        "walk": {"time": 5, "cost": 0},
        "bike": {"time": 2, "cost": 0, "requires_bike": True},
        # No direct taxi, too short / must walk from player_home
    }
    # City Center Connections (Example - can be expanded)
    # Assuming city_bus_station, rusty_mug_club, pro_music_store, downtown_cafe, city_airport, crash_pad_motel are defined POI/Venue objects
    city_center.intra_city_poi_connections[frozenset({city_bus_station.poi_id, rusty_mug_club.venue_id})] = {
        "walk": {"time": 25, "cost": 0},
        "bike": {"time": 10, "cost": 0, "requires_bike": True}, # Player might not have bike in new city initially
        "taxi": {"time": 7, "cost": 12}
    }
    city_center.intra_city_poi_connections[frozenset({rusty_mug_club.venue_id, pro_music_store.poi_id})] = {
        "walk": {"time": 10, "cost": 0},
        "bike": {"time": 4, "cost": 0, "requires_bike": True},
        "taxi": {"time": 3, "cost": 7}
    }
    city_center.intra_city_poi_connections[frozenset({downtown_cafe.poi_id, rusty_mug_club.venue_id})] = {
        "walk": {"time": 12, "cost": 0},
        "bike": {"time": 5, "cost": 0, "requires_bike": True},
        "taxi": {"time": 4, "cost": 9}
    }
    city_center.intra_city_poi_connections[frozenset({city_bus_station.poi_id, city_airport.poi_id})] = {
        "walk": {"time": 60, "cost": 0}, # Long walk
        # "bike": {"time": 25, "cost": 0, "requires_bike": True}, # Maybe not bikeable easily
        "taxi": {"time": 15, "cost": 25} # Airport taxi usually more
    }

    # Events (now primarily associated with Venues)
    open_mic_event = Event(
        name="Open Mic Night",
        event_type="OPEN_MIC",
        location=community_hall,
        required_skills={"vocals": 1, "guitar": 1},
        required_gear_types=["INSTRUMENT_ACOUSTIC"], # Open mic often acoustic
        description="A chance to show your skills at the local Community Hall."
    )
    community_hall.add_event(open_mic_event)

    first_club_gig_event = Event(
        name="Debut at 'The Rusty Mug'",
        event_type="CLUB_GIG",
        location=rusty_mug_club,
        required_skills={"vocals": 5, "guitar": 5, "stage_presence": 3},
        required_gear_types=["INSTRUMENT_ELECTRIC", "AMPLIFIER"], # Electric gig
        description="Your first real club gig! Make it count.",
    )
    first_club_gig_event.preparation_tasks_required = {
        "Write Setlist (3 songs)": False,
        "Rehearse Set (2 hours)": False,
        "Promote Gig Locally (social media post)": False
    }
    rusty_mug_club.add_event(first_club_gig_event)

    # Example of a higher tier event (player likely won't qualify for a while)
    opening_act_concert = Event(
        name="Opening Act for Major Band",
        event_type="CONCERT",
        location=grande_theater,
        required_skills={"vocals": 15, "guitar": 15, "stage_presence": 10, "songwriting": 10},
        required_gear_types=["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"], # Full band setup
        description="A huge opportunity to open for a touring band at the Grande Concert Hall!",
    )
    opening_act_concert.preparation_tasks_required = {
        "Finalize Setlist (5 songs, original material preferred)": False,
        "Intensive Rehearsal Week (10 hours)": False,
        "Coordinate with Main Act's Team": False,
        "Sound Check (2 hours, day of show)": False,
    }
    # This event might only be added if player has a manager or high fame
    # For now, add it so it's visible if player gets to City Center.
    grande_theater.add_event(opening_act_concert)

    # --- Instantiate NPCs ---
    # Old Timer Joe at his music shop in Hometown
    # For schedule, using object references directly instead of names for now for simplicity
    joe = NPC(npc_id="joe001", name="Old Timer Joe", personality_key="old_timer_joe", home_location=music_shop_home)
    joe.current_location = music_shop_home
    joe.schedule = {
        "Weekday_Morning": music_shop_home,
        "Weekday_Afternoon": music_shop_home,
        "Weekend_Morning": music_shop_home, # Covers Saturday and Sunday morning
        "Weekend_Evening": community_hall  # Covers Sunday evening (and Saturday if no other rule overrides)
    }
    NPC_REGISTRY[joe.npc_id] = joe
    music_shop_home.owner_npc_id = joe.npc_id

    # Sarah the Fan, often found where music is, especially in Hometown
    sarah = NPC(npc_id="sarah001", name="Sarah the Fan", personality_key="adoring_fan", home_location=WORLD_MAP["Your Hometown"])
    sarah.current_location = WORLD_MAP["Your Hometown"]
    sarah.schedule = {
        "open_mic_night_at_community_hall": community_hall
    }
    NPC_REGISTRY[sarah.npc_id] = sarah

    # Vic Vega, owner of The Rusty Mug in City Center
    vic = NPC(npc_id="vic001", name="Vic Vega", personality_key="gruff_club_owner", home_location=rusty_mug_club)
    vic.current_location = rusty_mug_club
    vic.schedule = {
        "Weekday_Afternoon": rusty_mug_club,
        "Weekday_Evening": rusty_mug_club,
        "Weekend_Evening": rusty_mug_club, # Covers Sat/Sun evenings
    }
    NPC_REGISTRY[vic.npc_id] = vic
    rusty_mug_club.owner_npc_id = vic.npc_id

    # Potential Bandmate - Alex Miles
    alex = NPC(npc_id="alex001", name="Alex 'Shredder' Miles", personality_key="potential_bandmate_guitarist", home_location=pro_music_store)
    alex.current_location = pro_music_store # Starts at the pro music store
    # alex.skills = {"guitar": 18, "songwriting": 7} # Store skills if NPC class supports it, or for dev reference
    alex.schedule = {
        "Weekday_Afternoon": pro_music_store, # Using keys from get_time_slot_key
        "Weekday_Evening": rusty_mug_club,
        "Weekend_Afternoon": pro_music_store, # Assuming Weekend maps to Saturday/Sunday
        "Weekend_Evening": rusty_mug_club,
    }
    NPC_REGISTRY[alex.npc_id] = alex

    # Music Blogger - Casey Jones
    casey = NPC(npc_id="casey001", name="Casey 'The Cynic' Jones", personality_key="music_blogger_critical", home_location=downtown_cafe) # Home is the cafe
    casey.current_location = downtown_cafe # Starts at the cafe
    casey.schedule = {
        "Weekday_Morning": downtown_cafe,
        "Weekday_Afternoon": downtown_cafe,
        "Weekday_Evening": rusty_mug_club, # Checks out gigs at Rusty Mug
        "Weekend_Evening": grande_theater, # Might check out bigger shows at Grande Theater too
    }
    NPC_REGISTRY[casey.npc_id] = casey

    # Interviewer NPC at the News Agency
    # news_agency_poi was defined earlier as: city_center.add_poi(news_agency_poi)
    # We need to ensure news_agency_poi is accessible here or passed correctly.
    # Assuming news_agency_poi is the variable holding the City Center Chronicle POI object.
    brenda_reporter = NPC(
        npc_id="brenda_reporter001",
        name="Brenda Reporter",
        personality_key="interviewer_professional",
        home_location=news_agency_poi, # Needs news_agency_poi to be defined in this scope
        current_location=news_agency_poi
    )
    brenda_reporter.schedule = {
        "Weekday_Morning": news_agency_poi,
        "Weekday_Afternoon": news_agency_poi,
        # Evenings and weekends she's off or somewhere else (e.g., home_location if different)
    }
    NPC_REGISTRY[brenda_reporter.npc_id] = brenda_reporter
    if news_agency_poi:
        news_agency_poi.owner_npc_id = brenda_reporter.npc_id

    # PR Agent NPC at Sharp PR Solutions
    # pr_agency_poi was defined earlier as: city_center.add_poi(pr_agency_poi)
    ms_sharp = NPC(
        npc_id="ms_sharp_pr001",
        name="Ms. Patricia Sharp",
        personality_key="pr_agent_evaluator",
        home_location=pr_agency_poi,
        current_location=pr_agency_poi
    )
    ms_sharp.schedule = {
        "Weekday_Morning": pr_agency_poi,
        "Weekday_Afternoon": pr_agency_poi,
    }
    NPC_REGISTRY[ms_sharp.npc_id] = ms_sharp
    if pr_agency_poi:
        pr_agency_poi.owner_npc_id = ms_sharp.npc_id # Ms. Sharp is the main contact/owner


# --- Time and Scheduling Helpers ---
def get_day_of_week_name(day_number_in_month):
=======
# game/main.py
from game.player import Player
from game.location import Location
from game.venue import Venue
from game.poi import PointOfInterest
from game.event import Event
from game.game_time import current_game_time, advance_game_time, get_current_time_str
from game.dialogue import generate_npc_response, NPC_PERSONALITIES # Ensure NPC_PERSONALITIES is imported if used directly
from game.random_events import check_for_random_event, check_for_post_gig_random_event
from game.song import Song
from game.gear import GearItem # For creating gear instances if needed by PR manager etc.
import random
import json # For loading world data

from game_data.gear_catalog import GEAR_CATALOG
from game.npc import NPC

WORLD_MAP = {}
NPC_REGISTRY = {}
PLAYER_HOME_POI_ID_GLOBAL = None # Will be set after world load

# --- Player Needs Update Function --- (Keep existing process_time_based_player_needs)
def process_time_based_player_needs(player, minutes_just_passed):
    if minutes_just_passed <= 0:
        return
    hours_passed_float = minutes_just_passed / 60.0
    if player.current_poi and hasattr(player.current_poi, 'comfort_modifier_hourly'):
        comfort_change = hours_passed_float * player.current_poi.comfort_modifier_hourly
        player.comfort = min(100, max(0, player.comfort + comfort_change))
        player.comfort = int(round(player.comfort))
    is_at_player_home = player.current_poi and PLAYER_HOME_POI_ID_GLOBAL and \
                        hasattr(player.current_poi, 'poi_id') and \
                        player.current_poi.poi_id == PLAYER_HOME_POI_ID_GLOBAL
    if is_at_player_home:
        homesickness_reduction_per_hour_at_home = 5
        player.homesickness = max(0, player.homesickness - (hours_passed_float * homesickness_reduction_per_hour_at_home))
        player.homesickness = int(round(player.homesickness))
    else:
        homesickness_increase_per_hour_away = 0.5
        player.homesickness = min(100, player.homesickness + (hours_passed_float * homesickness_increase_per_hour_away))
        player.homesickness = int(round(player.homesickness))
    if player.homesickness > 75:
        stress_increase_rate_from_homesickness = ((player.homesickness - 75) / 25.0) * 1.0
        player.stress = min(100, player.stress + (hours_passed_float * stress_increase_rate_from_homesickness))
        player.stress = int(round(player.stress))
    hunger_increase_per_hour = 2.5
    player.hunger = min(100, player.hunger + (hours_passed_float * hunger_increase_per_hour))
    player.hunger = int(round(player.hunger))
    if player.hunger > 90:
        stress_from_starvation_hourly_rate = 2.0
        player.stress = min(100, player.stress + (hours_passed_float * stress_from_starvation_hourly_rate))
        player.stress = int(round(player.stress))

# Helper function to get a POI or Venue by its ID from WORLD_MAP (after it's populated)
# This is needed because schedules in JSON will use IDs, not direct object references yet.
# And also to link NPC owners to their POIs/Venues.
_POI_VENUE_ID_MAP = {} # Internal map for quick ID lookups after loading

def _build_poi_venue_id_map():
    _POI_VENUE_ID_MAP.clear()
    for location in WORLD_MAP.values():
        for poi in location.points_of_interest:
            _POI_VENUE_ID_MAP[poi.poi_id] = poi
        for venue in location.venues:
            _POI_VENUE_ID_MAP[venue.venue_id] = venue

def get_poi_or_venue_by_id(target_id):
    return _POI_VENUE_ID_MAP.get(target_id)


def setup_world():
    global WORLD_MAP, NPC_REGISTRY, PLAYER_HOME_POI_ID_GLOBAL
    WORLD_MAP.clear()
    NPC_REGISTRY.clear()
    _POI_VENUE_ID_MAP.clear()


    # 1. Load Locations
    try:
        with open("game_data/world/locations.json", 'r') as f:
            locations_data = json.load(f)
    except FileNotFoundError:
        print("FATAL ERROR: game_data/world/locations.json not found!")
        return False # Indicate failure
    except json.JSONDecodeError as e:
        print(f"FATAL ERROR: Could not decode game_data/world/locations.json: {e}")
        return False

    temp_location_id_map = {} # Maps location_id (from JSON) to Location object
    for loc_data in locations_data:
        location = Location(loc_data["name"], loc_data["description"])
        location.id = loc_data["id"]
        WORLD_MAP[location.name] = location # Keep WORLD_MAP keyed by name for existing game logic
        temp_location_id_map[location.id] = location


    # 2. Load POIs and Venues for each Location
    for loc_id_from_json, location_obj in temp_location_id_map.items():
        poi_file_name = next((ld["poi_definition_file"] for ld in locations_data if ld["id"] == loc_id_from_json), None)
        if not poi_file_name:
            print(f"Warning: No POI definition file specified for location ID '{loc_id_from_json}' ({location_obj.name}).")
            continue

        poi_file_path = f"game_data/world/city_definitions/{poi_file_name}"
        try:
            with open(poi_file_path, 'r') as f:
                city_def_data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: POI definition file {poi_file_path} not found for location {location_obj.name}!")
            continue
        except json.JSONDecodeError as e:
            print(f"ERROR: Could not decode {poi_file_path} for location {location_obj.name}: {e}!")
            continue

        for poi_data in city_def_data.get("points_of_interest", []):
            properties = poi_data.get("properties", {})
            poi = PointOfInterest(
                poi_id=poi_data["poi_id"], name=poi_data["name"], description=poi_data["description"],
                category=poi_data["category"],
                interaction_options=list(poi_data.get("interaction_options", [])),
                parent_location_id=location_obj.name, # Uses name for now
                rest_quality=properties.get("rest_quality", 0.0),
                stress_modifier_hourly=properties.get("stress_modifier_hourly", 0),
                studio_quality=properties.get("studio_quality", 0.0),
                hourly_rate=properties.get("hourly_rate", 0),
                min_fame_to_submit=properties.get("min_fame_to_submit", 0),
                genres_preferred=list(properties.get("genres_preferred", [])),
                comfort_modifier_hourly=properties.get("comfort_modifier_hourly", 0)
            )
            if "shop_inventory_item_ids" in properties: poi.shop_inventory_item_ids = list(properties["shop_inventory_item_ids"])
            if "menu_items" in properties:
                poi.menu_items = list(properties["menu_items"])
                if poi.category == "FOOD_FASTFOOD" and not poi.interaction_options:
                    poi.interaction_options = [item["display_text"] for item in poi.menu_items]
            if "owner_npc_id" in properties: poi.owner_npc_id = properties["owner_npc_id"] # Store ID string

            if poi.poi_id == "citycenter_indiehits_records": # Example of specific POI logic after generic load
                 poi.interaction_options = [f"Submit Demo (requires {poi.min_fame_to_submit} fame)", "Talk to A&R Rep (requires Manager)"]
            location_obj.add_poi(poi)

        for venue_data in city_def_data.get("venues", []):
            properties = venue_data.get("properties", {})
            venue = Venue(
                venue_id=venue_data["venue_id"], name=venue_data["name"], description=venue_data["description"],
                venue_type=venue_data["venue_type"], category=venue_data["category"],
                capacity=venue_data["capacity"], prestige=venue_data["prestige"], parent_location_id=location_obj.name,
                can_rent_gear=properties.get("can_rent_gear", False),
                gear_rental_fee=properties.get("gear_rental_fee", 0),
                available_rental_gear_ids=list(properties.get("available_rental_gear_ids", []))
            )
            if "owner_npc_id" in properties: venue.owner_npc_id = properties["owner_npc_id"] # Store ID string
            venue.events_hosted_ids_from_json = list(venue_data.get("events_hosted_ids", []))
            location_obj.add_venue(venue)

        for conn_data in city_def_data.get("intra_city_poi_connections", []):
            poi_ids_tuple = tuple(sorted(conn_data["pois"]))
            if len(poi_ids_tuple) == 2:
                modes = {k: v for k, v in conn_data.items() if k != "pois"}
                location_obj.intra_city_poi_connections[frozenset(poi_ids_tuple)] = modes

    _build_poi_venue_id_map() # Populate the ID map for quick lookups

    # 3. Load NPCs
    try:
        with open("game_data/world/npcs.json", 'r') as f:
            npcs_data = json.load(f)
    except FileNotFoundError:
        print("ERROR: game_data/world/npcs.json not found!")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not decode game_data/world/npcs.json: {e}")
        return False

    for npc_data in npcs_data:
        home_loc_obj = None
        if "home_location_poi_id" in npc_data:
            home_loc_obj = get_poi_or_venue_by_id(npc_data["home_location_poi_id"])
        elif "home_location_location_id" in npc_data:
            # This assumes home_location_location_id is a name that exists in WORLD_MAP
            home_loc_obj = WORLD_MAP.get(npc_data["home_location_location_id"])

        current_loc_obj = None
        if "initial_current_location_poi_id" in npc_data:
            current_loc_obj = get_poi_or_venue_by_id(npc_data["initial_current_location_poi_id"])
        elif "initial_current_location_location_id" in npc_data:
             current_loc_obj = WORLD_MAP.get(npc_data["initial_current_location_location_id"])

        if not home_loc_obj and npc_data.get("schedule"):
            first_sched_id = list(npc_data["schedule"].values())[0]
            home_loc_obj = get_poi_or_venue_by_id(first_sched_id)
        if not current_loc_obj: current_loc_obj = home_loc_obj

        if not home_loc_obj:
             print(f"Warning: Could not determine home location for NPC {npc_data['name']}. NPC might not be placed correctly.")
        if not current_loc_obj:
             print(f"Warning: Could not determine current location for NPC {npc_data['name']}. NPC might not be placed correctly.")


        npc = NPC( npc_id=npc_data["npc_id"], name=npc_data["name"], personality_key=npc_data["personality_key"],
            home_location=home_loc_obj, current_location=current_loc_obj )

        for time_slot, loc_id_str in npc_data.get("schedule", {}).items():
            scheduled_loc_obj = get_poi_or_venue_by_id(loc_id_str)
            if scheduled_loc_obj: npc.schedule[time_slot] = scheduled_loc_obj
            else: print(f"Warning: Scheduled POI/Venue ID '{loc_id_str}' not found for {npc.name}'s schedule.")
        NPC_REGISTRY[npc.npc_id] = npc

    # 4. Link NPC owners to POIs/Venues (objects)
    for location in WORLD_MAP.values():
        for item_list in [location.points_of_interest, location.venues]:
            for item in item_list:
                if hasattr(item, 'owner_npc_id') and isinstance(item.owner_npc_id, str):
                    owner_npc_object = NPC_REGISTRY.get(item.owner_npc_id)
                    if owner_npc_object: item.owner_npc_id = owner_npc_object
                    else:
                        print(f"Warning: Owner NPC ID '{item.owner_npc_id}' (string) not found in NPC_REGISTRY for '{item.name}'. Setting owner to None.")
                        item.owner_npc_id = None


    # 5. Establish Inter-City Travel Connections
    for loc_data in locations_data:
        current_location_obj = temp_location_id_map.get(loc_data["id"]) # Use temp_location_id_map for consistency
        if not current_location_obj: continue
        for conn_data in loc_data.get("travel_connections", []):
            target_loc_obj = temp_location_id_map.get(conn_data["to_location_id"])
            if target_loc_obj:
                current_location_obj.add_travel_connection(
                    target_loc_obj.name, cost=conn_data["cost"], time_hours=conn_data["time_hours"]
                )
            else:
                print(f"Warning: Target location ID '{conn_data['to_location_id']}' for travel from '{current_location_obj.name}' not found.")

    # --- Event Creation (Still Python-based for now, linking to loaded venues) ---
    event_definitions = [
        {"id": "open_mic_hometown_hall", "venue_id": "hometown_community_hall", "name": "Open Mic Night", "type": "OPEN_MIC",
         "skills": {"vocals": 1, "guitar": 1}, "gear": ["INSTRUMENT_ACOUSTIC"], "desc": "A chance to show your skills..."},
        {"id": "debut_rusty_mug", "venue_id": "citycenter_rustymug", "name": "Debut at 'The Rusty Mug'", "type": "CLUB_GIG",
         "skills": {"vocals": 5, "guitar": 5, "stage_presence": 3}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER"],
         "desc": "Your first real club gig! Make it count.",
         "prep_tasks": {"Write Setlist (3 songs)": False, "Rehearse Set (2 hours)": False, "Promote Gig Locally (social media post)": False}},
        {"id": "opening_act_grande", "venue_id": "citycenter_grandetheater", "name": "Opening Act for Major Band", "type": "CONCERT",
         "skills": {"vocals": 15, "guitar": 15, "stage_presence": 10, "songwriting": 10},
         "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"],
         "desc": "A huge opportunity...",
         "prep_tasks": {"Finalize Setlist (5 songs, original material preferred)": False, "Intensive Rehearsal Week (10 hours)": False,
                        "Coordinate with Main Act's Team": False, "Sound Check (2 hours, day of show)": False,}}
    ]

    for event_def in event_definitions:
        venue_obj = get_poi_or_venue_by_id(event_def["venue_id"])
        if venue_obj and isinstance(venue_obj, Venue):
            # Check if this event was listed in the venue's JSON definition
            if event_def["id"] in getattr(venue_obj, 'events_hosted_ids_from_json', []):
                event = Event( name=event_def["name"], event_type=event_def["type"], location=venue_obj,
                               required_skills=event_def["skills"], required_gear_types=event_def["gear"],
                               description=event_def["desc"] )
                if "prep_tasks" in event_def: event.preparation_tasks_required = event_def["prep_tasks"]
                venue_obj.add_event(event)
        else:
            print(f"Warning: Venue ID '{event_def['venue_id']}' for event '{event_def['name']}' not found or not a Venue.")

    # --- Global Player Home POI ID ---
    player_home_obj = get_poi_or_venue_by_id("hometown_player_home")
    if player_home_obj: PLAYER_HOME_POI_ID_GLOBAL = player_home_obj.poi_id
    else: print("CRITICAL ERROR: Player home POI 'hometown_player_home' not found after loading world data.")

    print(f"World setup complete. Loaded {len(WORLD_MAP)} locations and {len(NPC_REGISTRY)} specific NPCs from JSON data.")
    return True # Indicate success


# --- Time and Scheduling Helpers --- (Keep existing get_day_of_week_name, get_time_slot_key, update_npc_locations)
def get_day_of_week_name(day_number_in_month):
    day_index = (day_number_in_month - 1) % 7
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[day_index]

def get_time_slot_key(game_time_obj):
    day_name = get_day_of_week_name(game_time_obj.day)
    hour = game_time_obj.hour
    day_type = "Weekend" if day_name in ["Saturday", "Sunday"] else "Weekday"
    time_period = "Night"
    if 6 <= hour <= 11: time_period = "Morning"
    elif 12 <= hour <= 17: time_period = "Afternoon"
    elif 18 <= hour <= 23: time_period = "Evening"
    return f"{day_type}_{time_period}"

def update_npc_locations(game_time_obj):
    current_time_slot_key = get_time_slot_key(game_time_obj)
    for npc in NPC_REGISTRY.values():
        scheduled_destination = npc.home_location
        if current_time_slot_key in npc.schedule:
            scheduled_destination_ref = npc.schedule[current_time_slot_key]
            if isinstance(scheduled_destination_ref, (PointOfInterest, Venue, Location)): # Already an object
                 scheduled_destination = scheduled_destination_ref
            else: # Should be an ID string now if loaded from JSON and not resolved, though loading logic tries to resolve
                 resolved_loc = get_poi_or_venue_by_id(scheduled_destination_ref) # Check POI/Venue map
                 if not resolved_loc: resolved_loc = WORLD_MAP.get(scheduled_destination_ref) # Check Location map (by name)
                 if resolved_loc: scheduled_destination = resolved_loc
                 else: print(f"Warning: NPC {npc.name} schedule contains unresolved location ID: {scheduled_destination_ref}")

        if npc.npc_id == "sarah001":
            community_hall_obj = get_poi_or_venue_by_id("hometown_community_hall")
            if community_hall_obj:
                open_mic_active = any(event.name == "Open Mic Night" and event.is_active for event in community_hall_obj.events_hosted)
                if "open_mic_night_at_community_hall" in npc.schedule and open_mic_active:
                    if npc.schedule["open_mic_night_at_community_hall"] == community_hall_obj :
                         scheduled_destination = community_hall_obj
            else: # Should not happen if world loaded correctly
                print("Warning: Hometown Community Hall object not found for Sarah's schedule check.")


        if npc.current_location != scheduled_destination:
            npc.current_location = scheduled_destination


# --- UI Helper Functions --- (Keep existing clear_screen_ish, present_choices)
def clear_screen_ish():
    print("\n" * 30)

def present_choices(options, title="Choose an option:"):
    print(f"\n--- {title} ---")
    if isinstance(options, list):
        for i, option_text in enumerate(options): print(f"{i+1}. {option_text}")
    elif isinstance(options, dict):
        for key, text in options.items(): print(f"{key}. {text}")
    else:
        print("Error: Invalid options type for present_choices.")
        return None
    max_attempts = 3
    for attempt in range(max_attempts):
        choice = input("> ")
        if isinstance(options, list):
            if choice.isdigit() and 1 <= int(choice) <= len(options): return str(int(choice))
        elif isinstance(options, dict):
            if choice in options: return choice
        print(f"Invalid choice. Please enter a valid number/key. ({max_attempts - 1 - attempt} attempts left)")
    print("Too many invalid attempts.")
    return None

# --- Helper for NPC Interaction --- (Keep existing talk_to_npc_instance)
def talk_to_npc_instance(player, npc_instance):
    if not npc_instance:
        print("No one specific to talk to here.")
        return
    print(f"\n--- Talking to {npc_instance.name} ---")
    print(f"Type 'bye' to end the conversation.")
    while True:
        player_input = input(f"{player.name}: ")
        if player_input.lower() == 'bye':
            print(f"{npc_instance.name} nods or waves goodbye.")
            npc_instance.add_memory(f"Had a conversation with {player.name} that ended.")
            advance_game_time(minutes=60)
            update_npc_locations(current_game_time)
            process_time_based_player_needs(player, 60) # Added needs processing
            break
        if not player_input.strip(): continue
        npc_response = generate_npc_response(player_input, npc_instance, player_name=player.name)
        print(f"{npc_instance.name}: {npc_response}")
        if "LLM Error" in npc_response or "An unexpected error occurred" in npc_response:
            npc_instance.add_memory(f"Had a communication problem while talking to {player.name}.")
            advance_game_time(minutes=60)
            update_npc_locations(current_game_time)
            process_time_based_player_needs(player, 60) # Added needs processing
            break
        clarification_options = {"1": "Friendly", "2": "Neutral", "3": "Unfriendly", "0": "No specific impact / Continue" }
        if not ("LLM Error" in npc_response or "An unexpected error occurred" in npc_response):
            print(f"\nHow should {npc_instance.name} interpret your last statement?")
            intent_choice = present_choices(clarification_options, title="Your intent:")
            relationship_points = 0; memory_detail = ""
            if intent_choice == "1": relationship_points = 5; memory_detail = f"Player ({player.name}) said something friendly: '{player_input}'"
            elif intent_choice == "3": relationship_points = -5; memory_detail = f"Player ({player.name}) said something unfriendly: '{player_input}'"
            if relationship_points != 0:
                npc_instance.update_relationship(relationship_points)
                npc_instance.add_memory(memory_detail)
                print(f"(Relationship with {npc_instance.name} updated by {relationship_points})")


def main():
    if not setup_world(): # Call new setup_world and check for success
        print("Failed to initialize the game world. Exiting.")
        return

    print("Welcome to the Text-Based Music Career Simulator!")
    print("IMPORTANT: This game uses Ollama for NPC conversations.")
    print("Please ensure Ollama is installed, running, and you have pulled the required model (e.g., `ollama pull llama3`).")

    player_name = input("Enter your character's name: ")
    player = Player(player_name)

    # Set player's starting location and POI
    # This needs to use the loaded world data
    hometown_location_obj = WORLD_MAP.get("Your Hometown") # Assuming WORLD_MAP is keyed by name
    player_home_poi_obj = None
    if hometown_location_obj:
        player_home_poi_obj = get_poi_or_venue_by_id(PLAYER_HOME_POI_ID_GLOBAL) # Use the global ID

    if hometown_location_obj and player_home_poi_obj:
        player.current_location = hometown_location_obj
        player.current_poi = player_home_poi_obj
    else:
        print("Error: Could not set player's starting home. Defaulting to first available city/POI.")
        if WORLD_MAP:
            first_loc_name = list(WORLD_MAP.keys())[0]
            player.current_location = WORLD_MAP[first_loc_name]
            if player.current_location.points_of_interest:
                player.current_poi = player.current_location.points_of_interest[0]
            elif player.current_location.venues:
                 player.current_poi = player.current_location.venues[0] # POI can be a venue
        if not player.current_location:
            print("FATAL: No locations loaded. Cannot start game.")
            return


    update_npc_locations(current_game_time)
    process_time_based_player_needs(player, 0)

    starting_guitar = GEAR_CATALOG.get("worn_acoustic_guitar")
    if starting_guitar: player.add_gear(starting_guitar)
    starting_picks = GEAR_CATALOG.get("guitar_picks_assorted")
    if starting_picks: player.add_gear(starting_picks)

    print(f"\n--- {get_current_time_str()} ---")
    print(player)

    # Game Loop (largely unchanged, but ensure it uses the new WORLD_MAP and NPC_REGISTRY correctly)
    while True:
        clear_screen_ish()
        # Display current location name; if current_location is None, handle gracefully
        current_loc_name_display = player.current_location.name if player.current_location else "Unknown Location"
        print(f"--- Current Location: {current_loc_name_display} ---")
        print(f"--- {get_current_time_str()} ---")
        print(f"--- Player: {player.name} | Fame: {player.fame} | Money: ${player.money} | Energy: {player.energy}/100 | Stress: {player.stress}/100 ---")
        # Display current POI name; if current_poi is None, use location name
        current_poi_name_display = player.current_poi.name if player.current_poi else current_loc_name_display
        print(f"--- Currently at: {current_poi_name_display} ---")


        main_menu_options = {
            "1": "Practice a skill", "2": "Travel to another City", "3": "Travel within this City (to another POI)",
            "4": "Explore current POI/Area", "5": "Check available gigs (at current City)",
            "6": "Prepare for a gig", "7": "Attempt a gig", "8": "View detailed player stats",
            "9": "Talk to someone (at current POI/Area)", "10": "Eat food from inventory",
            "11": "View Schedule", # New option
        }
        if player.has_manager or player.has_pr_manager: main_menu_options["12"] = "Staff Actions" # Shifted
        main_menu_options["00"] = "Advance time by 1 hour (debug)"; main_menu_options["0"] = "Quit game"

        choice = present_choices(main_menu_options, title=f"What would {player.name} like to do?")
        if choice is None: continue
        clear_screen_ish()

        # --- Action Handling (Most of this logic remains the same, but relies on WORLD_MAP and NPC_REGISTRY being populated from JSON) ---

        # Choice 1: Practice
        if choice == "1":
            print("--- Practice a Skill ---")
            skill_to_practice = input("Which skill to practice (e.g., vocals, guitar, stage_presence)? ").lower()
            try:
                hours_to_practice = int(input(f"How many hours to practice {skill_to_practice}? "))
                if hours_to_practice <= 0: print("Practice time must be positive."); continue
                player.practice_skill(skill_to_practice, hours_to_practice)
                minutes_passed = hours_to_practice*60
                advance_game_time(minutes=minutes_passed); update_npc_locations(current_game_time); process_time_based_player_needs(player, minutes_passed)
            except ValueError: print("Invalid number of hours.")

        # Choice 2: Inter-City Travel Info
        elif choice == "2":
            print("\n--- Inter-City Travel Information ---")
            current_city = player.current_location
            if not current_city: print("Error: Player not in a valid location."); continue # Should not happen

            transport_hubs_in_city = [poi for poi in (current_city.points_of_interest + current_city.venues) if hasattr(poi, 'category') and poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]]

            if not transport_hubs_in_city: print(f"{current_city.name} doesn't seem to have any major bus stations or airports defined for inter-city travel.")
            elif player.current_poi and player.current_poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                print(f"You are currently at {player.current_poi.name}. Use 'Explore current POI/Area' to find departures and buy tickets.")
            else:
                print(f"To travel to another city, go to a transport hub (bus station or airport).")
                if player.current_poi: print(f"You are currently at: {player.current_poi.name}.")
                else: print(f"You are currently in the general area of {current_city.name}.")
                print(f"\nAvailable transport hubs in {current_city.name}:")
                hub_display_list = [f"{hub.name} ({hub.category})" for hub in transport_hubs_in_city] + ["Nevermind / Stay in current area"]
                hub_choice_idx_str = present_choices(hub_display_list, "Go to which transport hub? (Or select 'Nevermind')")
                if hub_choice_idx_str and hub_choice_idx_str.isdigit():
                    choice_idx = int(hub_choice_idx_str) -1
                    if 0 <= choice_idx < len(transport_hubs_in_city):
                        chosen_hub_poi = transport_hubs_in_city[choice_idx]
                        print(f"\nTo get to {chosen_hub_poi.name}, use option '3. Travel within this City'.")
            print("--------------------")

        # Choice 3: Travel within City
        elif choice == "3":
            print(f"\n--- Travel within {player.current_location.name} ---")
            if not player.current_poi: print("You are not at a specific POI. Explore first."); continue

            current_city_object = player.current_location
            all_city_pois_and_venues = current_city_object.points_of_interest + current_city_object.venues
            dest_poi_options = [poi_obj for poi_obj in all_city_pois_and_venues if poi_obj != player.current_poi]

            if not dest_poi_options: print("No other specific POIs to travel to in this city.")
            else:
                dest_display_list = [f"{poi.name} ({poi.category if hasattr(poi,'category') else poi.venue_type})" for poi in dest_poi_options]
                dest_choice_idx_str = present_choices(dest_display_list, "Choose destination POI:")
                if dest_choice_idx_str and dest_choice_idx_str.isdigit():
                    chosen_destination_poi = dest_poi_options[int(dest_choice_idx_str) - 1]
                    origin_poi_id = player.current_poi.poi_id if hasattr(player.current_poi, 'poi_id') else getattr(player.current_poi, 'venue_id', None)
                    dest_poi_id = chosen_destination_poi.poi_id if hasattr(chosen_destination_poi, 'poi_id') else getattr(chosen_destination_poi, 'venue_id', None)

                    if not origin_poi_id or not dest_poi_id : print("Error determining travel route IDs."); continue

                    connection_key = frozenset({origin_poi_id, dest_poi_id})
                    travel_modes_data = current_city_object.intra_city_poi_connections.get(connection_key)

                    if not travel_modes_data: print(f"No direct travel route defined between {player.current_poi.name} and {chosen_destination_poi.name}.")
                    else:
                        print(f"Travel modes to {chosen_destination_poi.name}:")
                        available_modes_for_choice = {}; mode_map = {}; choice_num = 1
                        if "walk" in travel_modes_data:
                            mode_info = travel_modes_data["walk"]
                            available_modes_for_choice[str(choice_num)] = f"Walk: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                            mode_map[str(choice_num)] = ("walk", mode_info); choice_num += 1
                        if player.has_bike and "bike" in travel_modes_data:
                            mode_info = travel_modes_data["bike"]
                            available_modes_for_choice[str(choice_num)] = f"Bike: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                            mode_map[str(choice_num)] = ("bike", mode_info); choice_num += 1
                        if "taxi" in travel_modes_data:
                            mode_info = travel_modes_data["taxi"]
                            available_modes_for_choice[str(choice_num)] = f"Taxi: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                            mode_map[str(choice_num)] = ("taxi", mode_info); choice_num += 1

                        if not available_modes_for_choice: print("No travel modes available for this route."); continue

                        mode_choice_key = present_choices(available_modes_for_choice, "Choose travel mode:")
                        if mode_choice_key and mode_choice_key in mode_map:
                            chosen_mode_name, chosen_mode_details = mode_map[mode_choice_key]
                            if chosen_mode_name == "taxi" and player.money < chosen_mode_details['cost']: print(f"Not enough money for a taxi."); continue
                            if player.get_current_gear_load() > player.get_current_gear_capacity(chosen_mode_name): print(f"Too much gear to travel by {chosen_mode_name}."); continue

                            if chosen_mode_name == "taxi": player.money -= chosen_mode_details['cost']; print(f"Paid ${chosen_mode_details['cost']} for the taxi.")
                            player.travel_within_city(chosen_destination_poi, chosen_mode_details['time']) # This only sets current_poi
                            minutes_passed = chosen_mode_details['time']
                            advance_game_time(minutes=minutes_passed); update_npc_locations(current_game_time); process_time_based_player_needs(player, minutes_passed)
            print("--------------------")

        # Choice 4: Explore POI/Area
        elif choice == "4":
            current_poi_for_explore = player.current_poi
            current_location_for_explore = player.current_location
            print(f"\n--- Exploring {current_poi_for_explore.name if current_poi_for_explore else current_location_for_explore.name} ---")

            if current_poi_for_explore:
                print(f"Description: {current_poi_for_explore.description}")
                current_poi_interactions = list(current_poi_for_explore.interaction_options)
                pre_gig_autograph_interaction_text = "Hold Pre-Show Autograph Signing (1 hour)"
                if isinstance(current_poi_for_explore, Venue):
                    venue = current_poi_for_explore
                    can_do_pre_gig_signing = False
                    for event in venue.events_hosted:
                        if event.is_active and (event.are_preparations_complete() or not event.preparation_tasks_required):
                            if 16 <= current_game_time.hour <= 19: can_do_pre_gig_signing = True; break
                    if can_do_pre_gig_signing and pre_gig_autograph_interaction_text not in current_poi_interactions:
                        current_poi_interactions.append(pre_gig_autograph_interaction_text)

                interview_interaction_text = "Attend Scheduled Interview"
                if current_poi_for_explore.category == "OFFICE_NEWS_AGENCY" and \
                   player.active_opportunities.get("interview_city_chronicle") == "pending_player_action":
                    if interview_interaction_text not in current_poi_interactions:
                        current_poi_interactions.append(interview_interaction_text)

                if current_poi_interactions:
                    interaction_choice_key = present_choices(current_poi_interactions, title=f"Actions at {current_poi_for_explore.name}:")
                    if interaction_choice_key:
                        chosen_interaction_text = current_poi_interactions[int(interaction_choice_key) -1]
                        print(f"You chose to: {chosen_interaction_text}")

                        # --- PRE-GIG AUTOGRAPH ---
                        if chosen_interaction_text == pre_gig_autograph_interaction_text:
                            from game.interactions import handle_autograph_interaction
                            print("\nYou decide to hold a pre-show autograph signing session..."); num_fans = random.randint(2,4); met_fans=0; sess_time=0
                            for i in range(num_fans):
                                if sess_time >= 50: print("Scheduled hour is nearly up."); break
                                met_fans+=1; print(f"\nFan #{met_fans} approaches..."); tfan = NPC(f"pgfan_{i}",f"Fan #{met_fans}","adoring_fan")
                                print(f"{tfan.name}: \"{random.choice(['Love your work!','So excited for tonight!'])}\"")
                                outcome = handle_autograph_interaction(player,tfan,"pre_gig_signing"); sess_time+=outcome.get("minutes_passed",0)
                                if sess_time>=60: print("Time's up for autographs!"); break
                            print(f"\n--- Autograph Session Summary ---\nMet {met_fans} fan(s)."); player.stress=max(0,player.stress-(met_fans*2)); player.comfort=min(100,player.comfort+(met_fans*1))
                            if met_fans > 0: print("Feeling good after connecting!"); sess_time = max(15, min(sess_time, 75))
                            else: print("No fans for autographs today."); sess_time = 5
                            if sess_time > 0: advance_game_time(sess_time); update_npc_locations(current_game_time); process_time_based_player_needs(player,sess_time)

                        # --- SHOP MUSIC ---
                        elif current_poi_for_explore.category == "SHOP_MUSIC" and chosen_interaction_text == "Browse items for sale":
                            if current_poi_for_explore.shop_inventory_item_ids:
                                display = []; item_map = {}; idx=1
                                for item_id in current_poi_for_explore.shop_inventory_item_ids:
                                    item=GEAR_CATALOG.get(item_id)
                                    if item: display.append(f"{item.name} - ${item.cost} (Size: {item.size})"); item_map[str(idx)]=item; idx+=1
                                if not display: print("Out of stock.");
                                else:
                                    buy_key = present_choices(display, f"Items at {current_poi_for_explore.name}: (0 to cancel)")
                                    if buy_key and buy_key!="0" and buy_key in item_map:
                                        sel_item=item_map[buy_key]
                                        if player.money>=sel_item.cost:
                                            if player.can_carry_gear(sel_item): player.money-=sel_item.cost; player.add_gear(sel_item); print(f"Money: ${player.money}")
                                            else: print(f"Can't carry {sel_item.name}.")
                                        else: print(f"Not enough money for {sel_item.name}.")
                                    elif buy_key=="0": print("Cancelled.")
                            else: print("Nothing for sale.")

                        # --- INTER-CITY TRAVEL TICKETS ---
                        elif current_poi_for_explore.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"] and chosen_interaction_text == "View Departures & Buy Tickets":
                            connections = current_location_for_explore.travel_connections
                            if not connections: print(f"No inter-city routes from {current_location_for_explore.name}.")
                            else:
                                print(f"\n--- Departures from {current_poi_for_explore.name} ---"); dest_opts=[]; dest_map={}
                                for i,(dest_name,details) in enumerate(connections.items()):
                                    mode="Bus" if current_poi_for_explore.category=="TRANSPORT_BUS" else "Plane"
                                    dest_opts.append(f"To {dest_name} by {mode} (Cost: ${details['cost']}, Time: {details['time_hours']}h)"); dest_map[str(i+1)]=(dest_name,details)
                                if not dest_opts: print("No departures listed.");
                                else:
                                    dest_key = present_choices(dest_opts, "Select destination: (0 to cancel)")
                                    if dest_key and dest_key!="0" and dest_key in dest_map:
                                        chosen_dest_name,travel_details = dest_map[dest_key]
                                        if input(f"Travel to {chosen_dest_name} for ${travel_details['cost']} ({travel_details['time_hours']}h)? (y/n) > ").lower()=='y':
                                            if player.money >= travel_details['cost']:
                                                player.money -= travel_details['cost']
                                                dest_loc_obj = WORLD_MAP.get(chosen_dest_name)
                                                if dest_loc_obj:
                                                    travel_duration_hours = travel_details['time_hours']
                                                    travel_duration_minutes = travel_duration_hours * 60

                                                    # Log travel to schedule BEFORE advancing global time
                                                    travel_start_time = current_game_time.copy()
                                                    travel_end_time = current_game_time.copy()
                                                    travel_end_time.advance_time(minutes=travel_duration_minutes)

                                                    player.schedule.add_event(
                                                        start_time=travel_start_time,
                                                        end_time=travel_end_time,
                                                        description=f"Travel: {current_location_for_explore.name} to {chosen_dest_name}",
                                                        category="Travel",
                                                        details={
                                                            "from_city_id": current_location_for_explore.id if hasattr(current_location_for_explore, 'id') else current_location_for_explore.name,
                                                            "to_city_id": dest_loc_obj.id if hasattr(dest_loc_obj, 'id') else dest_loc_obj.name,
                                                            "transport_poi_id": current_poi_for_explore.poi_id
                                                        }
                                                    )

                                                    player.travel(dest_loc_obj, travel_duration_hours) # This updates player.current_location and stats
                                                    advance_game_time(minutes=travel_duration_minutes)
                                                    update_npc_locations(current_game_time)
                                                    process_time_based_player_needs(player, travel_duration_minutes)
                                                    print(f"Ticket bought. Travelled to {chosen_dest_name}.")
                                                else:
                                                    print(f"Error: Destination city '{chosen_dest_name}' not found in WORLD_MAP.")
                                                    player.money += travel_details['cost'] # Refund
                                            else:
                                                print(f"Not enough money. Need ${travel_details['cost']}.")
                                        else:
                                            print("Travel cancelled.")
                        # --- REST/SLEEP --- (HOME / ACCOMMODATION_CHEAP)
                        elif (current_poi_for_explore.category == "HOME" and chosen_interaction_text == "Rest (8 hours)") or \
                             (current_poi_for_explore.category == "ACCOMMODATION_CHEAP" and chosen_interaction_text.startswith("Sleep")):
                            hours_to_rest = 8; can_sleep_here = False
                            if current_poi_for_explore.category == "HOME": can_sleep_here = True
                            elif current_poi_for_explore.category == "ACCOMMODATION_CHEAP":
                                if player.rented_accommodation_info and player.rented_accommodation_info["poi_id"] == current_poi_for_explore.poi_id: can_sleep_here = True
                                else: print("You haven't rented a room here or it expired.")
                            if can_sleep_here:
                                comfort_eff=0; hunger_eff=0
                                if player.comfort < 25: comfort_eff=-0.2; elif player.comfort < 50: comfort_eff=-0.1
                                if player.hunger > 75: hunger_eff=-0.2; elif player.hunger > 50: hunger_eff=-0.1
                                eff_rest_q = max(0.05, current_poi_for_explore.rest_quality + comfort_eff + hunger_eff)
                                energy_g = int(hours_to_rest*10*eff_rest_q); stress_chg = int(hours_to_rest*current_poi_for_explore.stress_modifier_hourly)
                                if current_poi_for_explore.category == "HOME": player.homesickness=max(0,player.homesickness-(hours_to_rest*10)); player.comfort=min(100,player.comfort+(hours_to_rest*2))
                                player.energy=min(100,player.energy+energy_g); player.stress=max(0,player.stress+stress_chg)
                                advance_game_time(hours_to_rest*60); update_npc_locations(current_game_time); process_time_based_player_needs(player,hours_to_rest*60)
                                print(f"Rested for {hours_to_rest}h. Energy: {player.energy}, Stress: {player.stress}.")
                                if current_poi_for_explore.category == "ACCOMMODATION_CHEAP": player.rented_accommodation_info = None
                        # --- RENT ROOM ---
                        elif current_poi_for_explore.category == "ACCOMMODATION_CHEAP" and chosen_interaction_text.startswith("Rent Room"):
                            try:
                                rent_cost = int(chosen_interaction_text.split('$')[1].split('/')[0])
                                if player.money>=rent_cost:
                                    player.money-=rent_cost; from game.game_time import GameTime
                                    co_time=GameTime(current_game_time.year,current_game_time.month,current_game_time.day,current_game_time.hour,current_game_time.minute); co_time.advance_time(24*60)
                                    player.rented_accommodation_info = {"poi_id":current_poi_for_explore.poi_id, "checkout_time_obj":co_time}
                                    print(f"Rented room for ${rent_cost} until {co_time}. Money: ${player.money}.")
                                else: print(f"Not enough money. Need ${rent_cost}.")
                            except: print("Error parsing rent cost.")
                        # --- ORDER MERCH ---
                        elif current_poi_for_explore.category == "HOME" and chosen_interaction_text == "Order Merchandise Stock":
                            print("Order Merch logic here...") # Placeholder, use existing logic
                            advance_game_time(60); update_npc_locations(current_game_time); process_time_based_player_needs(player,60)
                        # --- WRITE SONG ---
                        elif current_poi_for_explore.category == "HOME" and chosen_interaction_text == "Write a new song":
                            print("Write Song logic here...") # Placeholder
                            advance_game_time(120); update_npc_locations(current_game_time); process_time_based_player_needs(player,120)
                        # --- BOOK RECORDING ---
                        elif current_poi_for_explore.category == "STUDIO_RECORDING" and chosen_interaction_text == "Book recording session":
                            print("Book Recording logic here...") # Placeholder
                            advance_game_time(180); update_npc_locations(current_game_time); process_time_based_player_needs(player,180)
                        # --- SUBMIT DEMO ---
                        elif current_poi_for_explore.category == "OFFICE_RECORD_LABEL" and chosen_interaction_text.startswith("Submit Demo"):
                             print("Submit Demo logic here...") # Placeholder
                             advance_game_time(120); update_npc_locations(current_game_time); process_time_based_player_needs(player,120)
                        # --- RELAX AT HOME ---
                        elif current_poi_for_explore.category == "HOME" and chosen_interaction_text == "Relax at home (2 hours)":
                            player.homesickness=max(0,player.homesickness-30); player.comfort=min(100,player.comfort+15); player.stress=max(0,player.stress-10); player.energy=max(0,player.energy-5)
                            advance_game_time(120); update_npc_locations(current_game_time); process_time_based_player_needs(player,120)
                            print(f"Relaxed. Comfort: {player.comfort}, Homesickness: {player.homesickness}, Stress: {player.stress}")
                        # --- CAFE ---
                        elif current_poi_for_explore.poi_id == "citycenter_dailygrind_cafe": # Example specific POI ID check
                            if chosen_interaction_text=="Grab Coffee ($5)":
                                if player.money>=5: player.money-=5; player.energy=min(100,player.energy+10); player.comfort=min(100,player.comfort+3); advance_game_time(20); update_npc_locations(current_game_time); process_time_based_player_needs(player,20); print(f"Grabbed coffee. Energy: {player.energy}")
                                else: print("Not enough money.")
                            elif chosen_interaction_text=="People Watch": player.stress=max(0,player.stress-5); player.comfort=min(100,player.comfort+2); advance_game_time(45); update_npc_locations(current_game_time); process_time_based_player_needs(player,45); print("People watched.")
                            elif chosen_interaction_text=="Look for Local Flyers": advance_game_time(15); update_npc_locations(current_game_time); process_time_based_player_needs(player,15); print("Found some flyers.")
                        # --- REHEARSAL STUDIO ---
                        elif current_poi_for_explore.category == "REHEARSAL_STUDIO" and chosen_interaction_text.startswith("Book Rehearsal Slot"):
                            print("Rehearsal logic here..."); advance_game_time(70); update_npc_locations(current_game_time); process_time_based_player_needs(player,70) # Placeholder
                        # --- REPAIR GEAR ---
                        elif current_poi_for_explore.category == "SHOP_MUSIC" and chosen_interaction_text == "Repair Gear":
                            print("Repair Gear logic here..."); advance_game_time(45); update_npc_locations(current_game_time); process_time_based_player_needs(player,45) # Placeholder
                        # --- BUY FOOD (GROCERY) ---
                        elif current_poi_for_explore.category == "SHOP_FOOD" and chosen_interaction_text == "Buy Food Items":
                            print("Buy Food (Grocery) logic here..."); advance_game_time(10); update_npc_locations(current_game_time); process_time_based_player_needs(player,10) # Placeholder
                        # --- FAST FOOD ---
                        elif current_poi_for_explore.category == "FOOD_FASTFOOD": # Already handled by dynamic menu items if interaction_options were empty
                            selected_menu_item_data=None
                            for mi in current_poi_for_explore.menu_items:
                                if mi["display_text"] == chosen_interaction_text: selected_menu_item_data=mi; break
                            if selected_menu_item_data:
                                cost=selected_menu_item_data["cost"]; eff=selected_menu_item_data["effects"]
                                if player.money>=cost:
                                    player.money-=cost; player.hunger=max(0,player.hunger+eff.get("hunger",0)); player.energy=min(100,player.energy+eff.get("energy",0)); player.comfort=min(100,max(0,player.comfort+eff.get("comfort",0)))
                                    advance_game_time(20); update_npc_locations(current_game_time); process_time_based_player_needs(player,20)
                                    print(f"Consumed {GEAR_CATALOG.get(selected_menu_item_data['item_id']).name if GEAR_CATALOG.get(selected_menu_item_data['item_id']) else 'food'}. Stats updated.")
                                else: print(f"Not enough money for {chosen_interaction_text}.")
                            else: print(f"Action '{chosen_interaction_text}' unclear at fast food.") # Should not happen if menu drives options
                        # --- NEWS AGENCY INTERVIEW ---
                        elif current_poi_for_explore.category == "OFFICE_NEWS_AGENCY" and chosen_interaction_text == "Attend Scheduled Interview":
                            interviewer_npc = NPC_REGISTRY.get(current_poi_for_explore.owner_npc_id.npc_id if hasattr(current_poi_for_explore.owner_npc_id, 'npc_id') else current_poi_for_explore.owner_npc_id) # Handle obj or id
                            if not interviewer_npc or interviewer_npc.current_location != current_poi_for_explore: print("Interviewer not available.");
                            else:
                                print(f"Meeting with {interviewer_npc.name}..."); succ_score=0; turns=3; mins_per_turn=20; total_mins=0
                                for i in range(turns):
                                    q_prompt=f"Ask interview Q{i+1} to {player.name}."
                                    if i==0: q_prompt=f"Welcome {player.name}. Let's start. {q_prompt}"
                                    i_q = generate_npc_response(q_prompt,interviewer_npc,player.name)
                                    print(f"\n{interviewer_npc.name}: {i_q}");
                                    if "LLM Error" in i_q: print("Interview cut short by tech issue."); break
                                    p_ans=input(f"{player.name} response: ")
                                    if p_ans.strip(): succ_score+=1; _=generate_npc_response(p_ans,interviewer_npc,player.name)
                                    else: print("You stumble for words.")
                                    total_mins+=mins_per_turn
                                print("\n--- Interview Concluded ---")
                                if succ_score>=2: fg=random.randint(25,40); player.fame+=fg; player.stress=max(0,player.stress-10); print(f"Good press! (Fame +{fg}, Stress -10)")
                                elif succ_score==1: fg=random.randint(10,20); player.fame+=fg; print(f"Okay interview. (Fame +{fg})")
                                else: player.stress=min(100,player.stress+5); print("Didn't go smoothly. (Stress +5)")
                                player.active_opportunities["interview_city_chronicle"]="completed"; total_mins=max(30,total_mins)

                                # Log interview to schedule
                                interview_start_time = current_game_time.copy() # Time before advancing for the interview itself
                                interview_end_time = interview_start_time.copy()
                                interview_end_time.advance_time(minutes=total_mins)
                                player.schedule.add_event(
                                    start_time=interview_start_time,
                                    end_time=interview_end_time,
                                    description=f"Interview: {current_poi_for_explore.name} with {interviewer_npc.name}",
                                    category="Interview",
                                    details={"poi_id": current_poi_for_explore.poi_id, "interviewer_npc_id": interviewer_npc.npc_id}
                                )

                                advance_game_time(total_mins); update_npc_locations(current_game_time); process_time_based_player_needs(player,total_mins)
                        # --- HIRE PR MANAGER ---
                        elif current_poi_for_explore.category == "OFFICE_PR_AGENCY" and chosen_interaction_text == "Inquire about PR representation":
                            pr_agent = NPC_REGISTRY.get(current_poi_for_explore.owner_npc_id.npc_id if hasattr(current_poi_for_explore.owner_npc_id, 'npc_id') else current_poi_for_explore.owner_npc_id)
                            if not pr_agent or pr_agent.current_location != current_poi_for_explore: print("Agent not available."); advance_game_time(10)
                            elif player.has_pr_manager: print(f"{pr_agent.name}: 'We're already working together!'"); advance_game_time(10)
                            else:
                                print(f"Meeting {pr_agent.name}..."); req_fame=player.pr_manager_fame_requirement_to_hire
                                if player.fame>=req_fame:
                                    print(f"{pr_agent.name}: '{player.name}, your fame ({player.fame}) is promising. We'd be interested.'")
                                    if input("Hire Sharp PR? (y/n): ").lower()=='y':
                                        player.has_pr_manager=True; print(f"Hired {pr_agent.name}!"); pr_agent.add_memory(f"Signed {player.name}."); pr_agent.update_relationship(20)
                                    else: print(f"{pr_agent.name}: 'Perhaps another time.'"); pr_agent.add_memory(f"Declined by {player.name}.")
                                else: print(f"{pr_agent.name}: '{player.name}, you need more buzz (Fame {player.fame}/{req_fame}). Come back later.'"); pr_agent.add_memory(f"Met {player.name}, not ready.")
                                advance_game_time(60);update_npc_locations(current_game_time);process_time_based_player_needs(player,60)
                        # --- OTHER/NOT IMPLEMENTED ---
                        else: print(f"(Action '{chosen_interaction_text}' not fully implemented yet.)")
                else:
                    if current_poi_for_explore and current_poi_for_explore.category == "OFFICE_NEWS_AGENCY" and \
                       player.active_opportunities.get("interview_city_chronicle") == "pending_player_action" and \
                       "Attend Scheduled Interview" not in current_poi_interactions :
                        print("\n(You remember your PR Manager mentioned an interview opportunity here.)")
                    else: print("There's not much to do here specifically.")
            else:
                print(f"Description: {current_location_for_explore.description}")
                if current_location_for_explore.venues: print("\nVenues:"); [print(f"  {i+1}. {v.name}") for i,v in enumerate(current_location_for_explore.venues)]
                if current_location_for_explore.points_of_interest: print("\nPOIs:"); [print(f"  {i+1}. {p.name}") for i,p in enumerate(current_location_for_explore.points_of_interest)]

            # Default time for just exploring an area/POI if no specific interaction took time above
            # This needs to be conditional on whether an interaction already advanced time.
            # For now, let's assume most interactions above will call advance_game_time.
            # If no interaction_choice_key or if chosen_interaction_text was a "Talk to" that didn't advance time itself:
            if not interaction_choice_key or (chosen_interaction_text and "Talk to" in chosen_interaction_text and not ("Interviewer" in chosen_interaction_text or "PR agent" in chosen_interaction_text)): # Crude check
                 advance_game_time(minutes=15) # Reduced general exploring time
                 update_npc_locations(current_game_time)
                 process_time_based_player_needs(player, 15)
            print("--------------------")

        # Choice 5: Check Gigs
        elif choice == "5":
            print(f"\n--- Gigs available in {player.current_location.name} ---")
            all_gigs = player.current_location.get_all_events_at_location()
            active_gigs = [event for event in all_gigs if event.is_active]
            if not active_gigs: print("No gigs available here at the moment.")
            else:
                for i, event in enumerate(active_gigs):
                    venue_name = event.location.name if hasattr(event.location, 'venue_type') else player.current_location.name
                    print(f"\n{i+1}. {event.name} ({event.event_type}) at {venue_name}\n   Desc: {event.description}\n   Reqs: {event.required_skills}\n   Fame: {event.fame_reward}, Payout: ${event.payout}")
                    if event.preparation_tasks_required:
                        pending = [task for task,done in event.preparation_tasks_required.items() if not done]
                        print(f"   Preparation: {', '.join(pending) if pending else 'Complete!'}")
                    else: print("   Preparation: Not Required.")
            print("--------------------")

        # Choice 6: Prepare Gig
        elif choice == "6":
            print(f"\n--- Prepare for a Gig ---")
            all_gigs = player.current_location.get_all_events_at_location()
            preparable = [e for e in all_gigs if e.is_active and e.preparation_tasks_required and not e.are_preparations_complete()]
            if not preparable: print("No gigs need prep or all preps done.")
            else:
                opts={str(i+1):e for i,e in enumerate(preparable)}; display=[f"{e.name} (at {e.location.name if hasattr(e.location,'name') else 'Unknown'}) - Pending: {', '.join([t for t,d in e.preparation_tasks_required.items() if not d])}" for e in preparable]
                gig_key = present_choices(display, "Prepare for which gig?")
                if gig_key and gig_key in opts:
                    event=opts[gig_key]; tasks_pending={str(i+1):task for i,(task,done) in enumerate(event.preparation_tasks_required.items()) if not done}
                    if not tasks_pending: print(f"All preps for {event.name} done."); continue
                    task_display = [name for name in tasks_pending.values()]
                    task_key = present_choices(task_display, f"Task for {event.name}?")
                    if task_key and task_key in tasks_pending:
                        task_to_do = tasks_pending[task_key]; print(f"Completing: {task_to_do}..."); event.complete_preparation_task(task_to_do)
                        advance_game_time(120); update_npc_locations(current_game_time); process_time_based_player_needs(player,120)
            print("--------------------")

        # Choice 7: Attempt Gig
        elif choice == "7":
            print(f"\n--- Attempt a Gig ---")
            all_gigs = player.current_location.get_all_events_at_location() # Use current_location consistently
            performable = [e for e in all_gigs if e.is_active and (not e.preparation_tasks_required or e.are_preparations_complete())]
            if not performable: print("No gigs ready to perform here.")
            else:
                opts={str(i+1):e for i,e in enumerate(performable)}; display=[f"{e.name} (at {e.location.name if hasattr(e.location,'name') else 'Unknown'})" for e in performable]
                gig_key = present_choices(display, "Attempt which gig?")
                if gig_key and gig_key in opts:
                    event = opts[gig_key]; can_perf, msg = event.can_perform(player)
                    if not can_perf: print(f"Cannot perform {event.name}: {msg}"); advance_game_time(60); update_npc_locations(current_game_time); process_time_based_player_needs(player,60)
                    elif event.perform_event(player):
                        gig_duration_minutes = 180

                        # Log to schedule before advancing global time
                        gig_start_time = current_game_time.copy()
                        gig_end_time = current_game_time.copy()
                        gig_end_time.advance_time(minutes=gig_duration_minutes)
                        event_name_for_schedule = event.name
                        venue_name_for_schedule = event.location.name if hasattr(event.location, 'name') else "Unknown Venue"
                        player.schedule.add_event(
                            start_time=gig_start_time,
                            end_time=gig_end_time,
                            description=f"Gig: {event_name_for_schedule} at {venue_name_for_schedule}",
                            category="Gig",
                            details={"event_id": event.event_id if hasattr(event, "event_id") else event.name, "venue_id": venue.venue_id if hasattr(venue,"venue_id") else venue_name_for_schedule} # Assuming venue is event.location
                        )

                        advance_game_time(gig_duration_minutes); update_npc_locations(current_game_time); process_time_based_player_needs(player,gig_duration_minutes)
                        player.check_and_unlock_staff()
                        venue_name = event.location.name if hasattr(event.location, 'name') else "the venue"
                        post_gig_outcome = check_for_post_gig_random_event(player,event.event_type,venue_name=venue_name)
                        if post_gig_outcome.get("event_triggered"):
                            event_mins = post_gig_outcome.get("minutes_passed",15)
                            if event_mins>0: advance_game_time(event_mins);update_npc_locations(current_game_time);process_time_based_player_needs(player,event_mins)
                            player.check_and_unlock_staff()
                        owner_id = getattr(event.location,'owner_npc_id',None)
                        owner_id = owner_id.npc_id if hasattr(owner_id,'npc_id') else owner_id # Get ID if it's obj
                        if owner_id and owner_id in NPC_REGISTRY:
                            owner=NPC_REGISTRY[owner_id]; owner.update_relationship(15); owner.add_memory(f"{player.name} had successful gig '{event.name}'."); print(f"Rel with {owner.name} improved.")
                        if not event.is_active: # e.g. one-time event
                            if hasattr(event.location,'remove_event'): event.location.remove_event(event)
                            # elif event in player.current_location.events_available: player.current_location.remove_location_event(event) # This attribute doesn't exist
                    else: # Failed performance
                        fail_mins=60; advance_game_time(fail_mins);update_npc_locations(current_game_time);process_time_based_player_needs(player,fail_mins)
                        owner_id = getattr(event.location,'owner_npc_id',None)
                        owner_id = owner_id.npc_id if hasattr(owner_id,'npc_id') else owner_id
                        if owner_id and owner_id in NPC_REGISTRY:
                            owner=NPC_REGISTRY[owner_id]; owner.update_relationship(-10); owner.add_memory(f"{player.name} failed gig '{event.name}'."); print(f"Rel with {owner.name} worsened.")
            print("--------------------")

        # Choice 8: View Player Stats
        elif choice == "8":
            print("\n--- Player Stats ---"); print(player); print(get_current_time_str()); print("--------------------")

        # Choice 9: Talk to Someone
        elif choice == "9":
            print("--- Talk to Someone ---")
            target_area_name = player.current_poi.name if player.current_poi else player.current_location.name
            available_npcs = []
            if player.current_poi:
                for npc in NPC_REGISTRY.values():
                    if npc.current_location == player.current_poi: available_npcs.append(npc)
            else: # Player at general city level
                 for npc in NPC_REGISTRY.values():
                    if npc.current_location == player.current_location: available_npcs.append(npc)

            if not available_npcs:
                print(f"No one specific to talk to at {target_area_name} right now.")
                if not player.current_poi :
                    print("A passerby notices you..."); temp_fan = NPC("temp_fan","Passerby","friendly_fan");
                    print(f"{temp_fan.name}: \"Hey, aren't you {player.name}?\""); talk_to_npc_instance(player,temp_fan)
            else:
                opts={str(i+1):npc for i,npc in enumerate(available_npcs)}; display=[npc.name for npc in available_npcs]
                npc_key = present_choices(display, f"Who at {target_area_name}?")
                if npc_key and npc_key in opts: talk_to_npc_instance(player, opts[npc_key])

        # Choice 10: Eat from Inventory
        elif choice == "10":
            print("\n--- Eat Food From Inventory ---")
            food_items = [item for item in player.gear_inventory if item.gear_type == "FOOD"]
            if not food_items: print("No food in inventory.")
            else:
                opts={str(i+1):item for i,item in enumerate(food_items)}
                display=[f"{item.name} (Hunger: -{item.hunger_reduction}, Energy: +{item.energy_boost})" + (f", Comfort: {item.get_property('comfort_effect'):+}" if item.get_property("comfort_effect") else "") for item in food_items]
                food_key = present_choices(display, "Eat which item? (0 to cancel)")
                if food_key and food_key!="0" and food_key in opts:
                    item=opts[food_key]; player.hunger=max(0,player.hunger-item.hunger_reduction); player.energy=min(100,player.energy+item.energy_boost)
                    player.comfort=min(100,max(0,player.comfort+(item.get_property("comfort_effect") or 0)))
                    player.remove_gear(item); eat_mins=15; advance_game_time(eat_mins);update_npc_locations(current_game_time);process_time_based_player_needs(player,eat_mins)
                    print(f"Ate {item.name}. Hunger: {player.hunger}, Energy: {player.energy}, Comfort: {player.comfort}")
                elif food_key=="0": print("Cancelled eating.")
            print("--------------------")

        # Choice 11: View Schedule
        elif choice == "11":
            print("\n--- View Schedule ---")
            schedule_view_options = {
                "1": "Today's Schedule",
                "2": "Tomorrow's Schedule",
                "3": "This Week's Schedule",
                "0": "Back"
            }
            view_choice = present_choices(schedule_view_options, "Select schedule view:")

            if view_choice == "0":
                print("Returning to main menu.")
            elif view_choice in ["1", "2", "3"]:
                from game.game_time import GameTime # For creating target dates

                target_time = current_game_time.copy()
                if view_choice == "2": # Tomorrow
                    target_time.advance_time(minutes=24*60) # Advance by one day

                scheduled_items = []
                if view_choice == "1" or view_choice == "2": # Today or Tomorrow
                    scheduled_items = player.schedule.get_events_for_day(target_time.year, target_time.month, target_time.day)
                    day_str = "Today" if view_choice == "1" else "Tomorrow"
                    print(f"\n--- {day_str}'s Schedule ({target_time.year}-{target_time.month:02d}-{target_time.day:02d}) ---")
                elif view_choice == "3": # This Week
                    scheduled_items = player.schedule.get_events_for_week(target_time.year, target_time.month, target_time.day)
                    print(f"\n--- This Week's Schedule (Starting {target_time.year}-{target_time.month:02d}-{target_time.day:02d}) ---")

                if not scheduled_items:
                    print("Nothing scheduled.")
                else:
                    for item in scheduled_items:
                        # Ensure start_time and end_time are GameTime objects
                        start_display = f"{item.start_time.hour:02d}:{item.start_time.minute:02d}" if hasattr(item.start_time, 'hour') else str(item.start_time)
                        end_display = f"{item.end_time.hour:02d}:{item.end_time.minute:02d}" if hasattr(item.end_time, 'hour') else str(item.end_time)

                        # Include date for weekly view or if event spans multiple days (not handled yet but good for future)
                        date_prefix = ""
                        if view_choice == "3": # For weekly view, show the date of the event
                             date_prefix = f"{item.start_time.year}-{item.start_time.month:02d}-{item.start_time.day:02d} "

                        print(f"{date_prefix}{start_display} - {end_display}: {item.description} ({item.category})")

                advance_game_time(minutes=10) # Time spent checking schedule
                update_npc_locations(current_game_time)
                process_time_based_player_needs(player, 10)
            else:
                print("Invalid schedule view choice.")
            print("--------------------")


        # Choice 12: Staff Actions (Shifted from 11)
        elif choice == "12":
            if not (player.has_manager or player.has_pr_manager): print("No staff yet.")
            else:
                print("\n--- Staff Actions ---"); staff_opts={}; current_opt_idx = 1
                if player.has_manager: staff_opts[str(current_opt_idx)]="Talk to Artist Manager"; current_opt_idx+=1
                if player.has_pr_manager: staff_opts[str(current_opt_idx)]="Check PR Opportunities"; current_opt_idx+=1
                staff_opts["0"]="Back to Main Menu"

                sub_choice_key = present_choices({k:v for k,v in staff_opts.items()}, "Staff action:") # Pass dict
                action_text = staff_opts.get(sub_choice_key)

                if action_text == "Talk to Artist Manager":
                    print("Met Artist Manager. (Interactions TBD)"); adv_min=30
                elif action_text == "Check PR Opportunities":
                    print("Checking with PR Manager..."); adv_min=30
                    chron_key="interview_city_chronicle"; chron_fame_req=player.OPPORTUNITY_FAME_THRESHOLDS.get(chron_key,float('inf'))
                    op_status=player.active_opportunities.get(chron_key)
                    if op_status=="completed": print("PR: 'Chronicle interview done!'")
                    elif op_status=="pending_player_action": print("PR: 'Chronicle interview ready when you are.'")
                    elif player.fame>=chron_fame_req: player.active_opportunities[chron_key]="pending_player_action"; print("PR: 'Good news! Chronicle interview lined up!'")
                    else: print(f"PR: 'Quiet on press front. Need ~{chron_fame_req} fame for Chronicle.'")
                elif action_text == "Back to Main Menu": adv_min=0 # No time passed
                else: print("Invalid staff action."); adv_min=0

                if adv_min > 0: advance_game_time(adv_min);update_npc_locations(current_game_time);process_time_based_player_needs(player,adv_min)
            print("--------------------")

        # Choice 00: Debug Advance Time
        elif choice == "00":
            advance_game_time(minutes=60); update_npc_locations(current_game_time); process_time_based_player_needs(player, 60)

        # Choice 0: Quit
        elif choice == "0": print("Thanks for playing!"); break
        else: print("Invalid choice. Please try again.")

        print(f"\n--- {get_current_time_str()} ---")

        # General Random Event Check (if not an LLM error state from talk_to_npc_instance)
        if choice in ["1", "2", "3", "4", "5", "6", "7", "10", "11", "00"]: # Most actions can trigger
            # Avoid if last interaction was an LLM error, to prevent spamming events while LLM is down.
            # This check is a bit broad; ideally, check a specific flag set by generate_npc_response if it errored.
            # For now, assume 'npc_response' in locals() is a decent proxy if choice '9' was just run.
            npc_response_check = locals().get('npc_response', '')
            if not ("LLM Error" in npc_response_check or "An unexpected error occurred" in npc_response_check):
                ctx_name = player.current_poi.name if player.current_poi else player.current_location.name
                event_outcome = check_for_random_event(player, current_poi_name=ctx_name, chance=0.15) # Slightly lower chance
                if event_outcome.get("event_triggered"):
                    event_mins = event_outcome.get("minutes_passed", 15)
                    if event_mins > 0: advance_game_time(event_mins);update_npc_locations(current_game_time);process_time_based_player_needs(player,event_mins)
                    player.check_and_unlock_staff()


if __name__ == "__main__":
    main()
