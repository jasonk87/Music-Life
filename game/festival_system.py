from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from game.game_time import current_game_time


@dataclass
class TournamentRound:
    round_name: str
    opponent_name: str
    required_score: float
    prize_money: int
    fame_reward: int


class FestivalSystem:
    TOURNAMENTS = {
        "battle_of_the_bands_hometown": {
            "name": "Asbury Park Battle of the Bands",
            "location_name": "Asbury Park, NJ",
            "min_fame": 0,
            "entry_fee": 50,
            "rounds": [
                {"round_name": "Quarter-Finals", "opponent_name": "The Garage Rats", "required_score": 10.0, "prize_money": 100, "fame_reward": 5},
                {"round_name": "Semi-Finals", "opponent_name": "Velvet Static", "required_score": 14.0, "prize_money": 250, "fame_reward": 10},
                {"round_name": "Finals", "opponent_name": "Neon Syndicate", "required_score": 18.0, "prize_money": 600, "fame_reward": 25},
            ],
        },
        "city_center_indie_cup": {
            "name": "Philadelphia Indie Showcase Cup",
            "location_name": "Philadelphia, PA",
            "min_fame": 30,
            "entry_fee": 150,
            "rounds": [
                {"round_name": "Quarter-Finals", "opponent_name": "Sonic Echo", "required_score": 14.0, "prize_money": 300, "fame_reward": 10},
                {"round_name": "Semi-Finals", "opponent_name": "Subway Ghosts", "required_score": 18.0, "prize_money": 700, "fame_reward": 20},
                {"round_name": "Finals", "opponent_name": "The Metropolitan", "required_score": 22.0, "prize_money": 1500, "fame_reward": 45},
            ],
        },
    }

    FESTIVALS = {
        "austin_live_music_fest": {
            "name": "Austin Live Music Fest",
            "city": "Austin, TX",
            "min_fame": 60,
            "stages": ["Side Stage", "Indie Pavilion", "Main Stage"],
            "base_payout": 800,
            "fame_surge": 60,
        }
    }

    def start_tournament(self, game, tournament_key: str) -> Dict:
        tourn = self.TOURNAMENTS.get(tournament_key)
        if not tourn:
            return {"ok": False, "explanation": "Unknown tournament."}

        player = game.player
        if player.money < tourn["entry_fee"]:
            return {"ok": False, "explanation": f"Need ${tourn['entry_fee']} entry fee to compete."}

        player.money -= tourn["entry_fee"]
        game.active_tournament = {
            "key": tournament_key,
            "name": tourn["name"],
            "current_round_idx": 0,
            "rounds": tourn["rounds"],
        }
        return {"ok": True, "explanation": f"Entered {tourn['name']}! Get ready for the {tourn['rounds'][0]['round_name']}."}

    def advance_tournament_round(self, game, performance_score: float) -> Dict:
        active = getattr(game, "active_tournament", None)
        if not active:
            return {"ok": False, "explanation": "No active tournament."}

        idx = active["current_round_idx"]
        current_round = active["rounds"][idx]

        if performance_score >= current_round["required_score"]:
            game.player.money += current_round["prize_money"]
            game.player.fame += current_round["fame_reward"]
            game.player.street_cred = min(100, getattr(game.player, "street_cred", 50) + 4)

            if idx + 1 < len(active["rounds"]):
                active["current_round_idx"] += 1
                next_r = active["rounds"][idx + 1]
                return {
                    "ok": True,
                    "won_round": True,
                    "tournament_complete": False,
                    "explanation": f"VICTORY in {current_round['round_name']} against {current_round['opponent_name']}! Won ${current_round['prize_money']} & +{current_round['fame_reward']} Fame. Next round: {next_r['round_name']}.",
                }
            else:
                game.active_tournament = None
                return {
                    "ok": True,
                    "won_round": True,
                    "tournament_complete": True,
                    "explanation": f"TOURNAMENT CHAMPION! You won the {active['name']} trophy, ${current_round['prize_money']}, and +{current_round['fame_reward']} Fame!",
                }
        else:
            game.active_tournament = None
            game.player.street_cred = max(0, getattr(game.player, "street_cred", 50) - 3)
            return {
                "ok": False,
                "won_round": False,
                "tournament_complete": True,
                "explanation": f"Eliminated in {current_round['round_name']} by {current_round['opponent_name']}. Better luck next season!",
            }
