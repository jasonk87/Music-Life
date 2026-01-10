import random

CAMPAIGN_TYPES = {
    "social_media": {"name": "Social Media Blast", "cost": 100, "buzz_gain_min": 5, "buzz_gain_max": 15},
    "street_team": {"name": "Street Team Flyers", "cost": 300, "buzz_gain_min": 10, "buzz_gain_max": 30},
    "radio_push": {"name": "Radio Push", "cost": 1000, "buzz_gain_min": 40, "buzz_gain_max": 80},
    "pr_stunt": {"name": "PR Stunt (Risky)", "cost": 500, "buzz_gain_min": -20, "buzz_gain_max": 100},
    "music_video": {"name": "Music Video", "cost": 5000, "buzz_gain_min": 150, "buzz_gain_max": 300},
}

def run_marketing_campaign(campaign_type, song):
    data = CAMPAIGN_TYPES.get(campaign_type)
    if not data:
        return 0, "Invalid campaign."

    buzz = random.randint(data['buzz_gain_min'], data['buzz_gain_max'])

    # Apply logic to song? Or just return buzz?
    # Song.buzz_score is where it should go.
    song.buzz_score += buzz

    msg = f"Campaign '{data['name']}' complete. Generated {buzz} buzz for '{song.title}'."
    if buzz < 0:
        msg = f"Campaign '{data['name']}' backfired! Lost {-buzz} buzz."

    return buzz, msg
