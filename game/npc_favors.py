from __future__ import annotations

from typing import Dict, Any, Optional

from game.game_time import current_game_time
from game.npc_system import NPC, NPCSystem


class NPCFavorsSystem:
    """Handles calling in high-value social favors from allied NPCs."""

    @staticmethod
    def request_booker_prime_slot_favor(player, npc: NPC) -> Dict[str, Any]:
        if npc.role != "BOOKER":
            return {"ok": False, "explanation": f"{npc.name} is not a venue booker."}

        if npc.affinity < 40.0:
            return {"ok": False, "explanation": f"Need at least 40 Affinity with {npc.name} to request prime weekend slots (Current: {npc.affinity:.0f})."}

        if npc.favors_available <= 0:
            return {"ok": False, "explanation": f"{npc.name} has already helped you out recently. Build more rapport first."}

        npc.favors_available -= 1
        npc.favors_used += 1
        player.fame = min(1000, player.fame + 20)
        player.money += 2500  # Advance / sold out guarantee boost

        memory = f"Day {current_game_time.day}: Hooked up {player.name} with prime Friday headlining slot at {npc.poi_id}."
        npc.memories.append(memory)

        summary = (
            f"🌟 BOOKER FAVOR FROM {npc.name}!\n"
            f"- Secured prime sold-out Friday night headlining slot at {npc.poi_id}!\n"
            f"- Guaranteed Box Office Advance: +$2,500\n"
            f"- Hype & Fame: +20 Fame"
        )
        return {"ok": True, "bonus_money": 2500, "explanation": summary}

    @staticmethod
    def request_engineer_tape_saturation_favor(player, npc: NPC, song) -> Dict[str, Any]:
        if npc.role != "ENGINEER":
            return {"ok": False, "explanation": f"{npc.name} is not a studio tracking engineer."}

        if npc.affinity < 40.0:
            return {"ok": False, "explanation": f"Need at least 40 Affinity with {npc.name} to request free tape mastering (Current: {npc.affinity:.0f})."}

        if not song.is_recorded:
            return {"ok": False, "explanation": f"'{song.title}' must be recorded before running analog master tape compression."}

        song.recording_quality = min(1.0, song.recording_quality + 0.12)
        npc.favors_used += 1

        memory = f"Day {current_game_time.day}: Ran analog tape compression master for {player.name}'s track '{song.title}'."
        npc.memories.append(memory)

        summary = (
            f"🎛️ ANALOG ENGINEER FAVOR FROM {npc.name}!\n"
            f"- Ran '{song.title}' through vintage Studer 2-inch tape machine and custom Fairchild tube compressors!\n"
            f"- Master Recording Quality Boosted: +0.12 (Now {song.recording_quality:.2f})"
        )
        return {"ok": True, "song": song, "explanation": summary}

    @staticmethod
    def request_musician_cowrite_favor(player, npc: NPC, song) -> Dict[str, Any]:
        if npc.role != "MUSICIAN":
            return {"ok": False, "explanation": f"{npc.name} is not a session musician/songwriter."}

        if npc.affinity < 35.0:
            return {"ok": False, "explanation": f"Need at least 35 Affinity with {npc.name} for a co-writing session (Current: {npc.affinity:.0f})."}

        song.song_quality = min(1.0, song.song_quality + 0.15)
        player.stress = max(0, player.stress - 15)
        npc.favors_used += 1

        memory = f"Day {current_game_time.day}: Co-wrote and arranged song '{song.title}' with {player.name}."
        npc.memories.append(memory)

        summary = (
            f"🎸 CO-WRITING SESSION WITH {npc.name}!\n"
            f"- Jammed backstage in {npc.city}, trading chord inversions and unforgettable melody hooks on '{song.title}'.\n"
            f"- Songwriting Composition Quality: +0.15 (Now {song.song_quality:.2f})\n"
            f"- Stress reduced by 15."
        )
        return {"ok": True, "song": song, "explanation": summary}
