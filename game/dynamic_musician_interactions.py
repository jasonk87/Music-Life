from __future__ import annotations

from typing import Dict, Any, Optional

from game.game_time import current_game_time
from game.dynamic_musicians import AutonomousMusician


class DynamicMusicianInteractions:
    """Handles deep, organic player interactions with autonomous AI touring musicians."""

    @staticmethod
    def hang_out_and_chat(player, musician: AutonomousMusician) -> Dict[str, Any]:
        musician.affinity_with_player = min(100.0, musician.affinity_with_player + 12.0)
        player.stress = max(0, player.stress - 15)
        musician.stress = max(0, musician.stress - 15)

        summary = (
            f"🍻 HUNG OUT WITH {musician.name} ({musician.genre}) in {musician.current_city}!\n"
            f"- Swapped tour van breakdown stories and songwriting techniques over coffee & drinks.\n"
            f"- Affinity: +12 (Now {musician.affinity_with_player:.0f}/100)\n"
            f"- Stress reduced by 15 points."
        )
        return {"ok": True, "musician": musician, "explanation": summary}

    @staticmethod
    def jam_and_cowrite_song(player, musician: AutonomousMusician, song) -> Dict[str, Any]:
        if musician.affinity_with_player < 20.0:
            return {"ok": False, "explanation": f"Need at least 20 Affinity with {musician.name} to write together (Current: {musician.affinity_with_player:.0f})."}

        song.song_quality = min(1.0, song.song_quality + 0.12)
        musician.affinity_with_player = min(100.0, musician.affinity_with_player + 15.0)
        player.energy = max(0, player.energy - 15)

        summary = (
            f"🎸 BACKSTAGE CO-WRITING JAM WITH {musician.name}!\n"
            f"- Blended your style with {musician.genre} riffs on '{song.title}'.\n"
            f"- Song Composition Quality: +0.12 (Now {song.song_quality:.2f})\n"
            f"- Affinity with {musician.name}: +15 (Now {musician.affinity_with_player:.0f}/100)"
        )
        return {"ok": True, "song": song, "explanation": summary}

    @staticmethod
    def propose_coheadlining_tour(player, musician: AutonomousMusician) -> Dict[str, Any]:
        if musician.affinity_with_player < 40.0:
            return {"ok": False, "explanation": f"{musician.name} wants to know you better before committing to a co-headlining tour (Need 40+ Affinity, currently {musician.affinity_with_player:.0f})."}

        if musician.co_headlining_with_player:
            return {"ok": False, "explanation": f"You are already on a joint co-headlining tour with {musician.name}."}

        musician.co_headlining_with_player = True
        player.fame = min(1000, player.fame + 25)

        summary = (
            f"🤝 CO-HEADLINING TOUR AGREEMENT SIGNED WITH {musician.name}!\n"
            f"- Joint tour announced across major cities!\n"
            f"- Concert Hype Multiplier: +30% on all joint dates\n"
            f"- Shared travel convoys and cross-pollinating fanbases (+25 Fame)."
        )
        return {"ok": True, "musician": musician, "explanation": summary}

    @staticmethod
    def offer_album_production(player, musician: AutonomousMusician) -> Dict[str, Any]:
        if musician.affinity_with_player < 30.0:
            return {"ok": False, "explanation": f"Need at least 30 Affinity with {musician.name} to pitch production services (Current: {musician.affinity_with_player:.0f})."}

        production_fee = 3500
        player.money += production_fee
        musician.funds = max(0, musician.funds - production_fee)
        musician.affinity_with_player = min(100.0, musician.affinity_with_player + 20.0)
        player.fame = min(1000, player.fame + 15)

        summary = (
            f"🎛️ PRODUCED NEW LP FOR {musician.name}!\n"
            f"- Dialed in analog tracking, drum gating, and vocal saturation in the studio.\n"
            f"- Producer Advance Fee Deposited: +${production_fee:,}\n"
            f"- Earned 3 Producer Points on record royalties & +15 Fame!"
        )
        return {"ok": True, "fee": production_fee, "explanation": summary}

    @staticmethod
    def sign_to_player_label_imprint(player, label_imprint, musician: AutonomousMusician) -> Dict[str, Any]:
        if not label_imprint:
            return {"ok": False, "explanation": "You don't own an active Indie Label Imprint."}

        if musician.affinity_with_player < 50.0:
            return {"ok": False, "explanation": f"{musician.name} requires at least 50 Affinity to sign their masters to your imprint (Current: {musician.affinity_with_player:.0f})."}

        if musician.is_signed_to_player_label:
            return {"ok": False, "explanation": f"{musician.name} is already signed to your label."}

        advance_cost = 4000
        if player.money < advance_cost:
            return {"ok": False, "explanation": f"Need ${advance_cost:,} for artist signing advance."}

        player.money -= advance_cost
        musician.funds += advance_cost
        musician.is_signed_to_player_label = True

        from game.label_imprint import SignedArtist
        signed = SignedArtist(
            npc_id=musician.artist_id,
            name=musician.name,
            genre=musician.genre,
            skill_level=musician.skill_level,
            royalty_split=0.50,
            advance_paid=advance_cost,
        )
        label_imprint.roster[musician.artist_id] = signed
        player.fame = min(1000, player.fame + 30)

        summary = (
            f"📜 SIGNED {musician.name} TO {label_imprint.label_name}!\n"
            f"- Paid Signing Advance: -${advance_cost:,}\n"
            f"- Contract Terms: 50/50 net master profit split\n"
            f"- Added to Label Roster. Label Prestige +30 Fame!"
        )
        return {"ok": True, "artist": signed, "explanation": summary}
