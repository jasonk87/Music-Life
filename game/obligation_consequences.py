from game.game_time import current_game_time


class ObligationConsequenceEngine:
    """Applies downstream penalties/risk impacts based on canonical obligation reason codes."""

    def apply_resolution(self, player, resolution, game_log):
        if not resolution or not resolution.item or not isinstance(resolution.item.details, dict):
            return

        details = resolution.item.details
        eval_stamp = details.get("obligation_evaluated_at")
        if not eval_stamp:
            return

        # Idempotency: do not apply twice for same evaluation snapshot.
        if details.get("obligation_consequence_applied_at") == eval_stamp:
            return

        category = (resolution.item.category or "").lower()
        reason_code = resolution.reason_code

        # Base status consequences.
        if resolution.status == "late_but_possible":
            player.stress = min(100, player.stress + 2)
            if "gig" in category:
                player.fame = max(0, player.fame - 1)
                game_log.add_log_message("You arrive late; the crowd notices the rushed setup (-1 fame).")
        elif resolution.status in {"unreachable", "missed"}:
            player.stress = min(100, player.stress + 6)

        # Canonical reason consequences.
        if reason_code == "insufficient_funds":
            player.stress = min(100, player.stress + 4)
            game_log.add_log_message("Cash flow pressure spikes your stress (+4).")
        elif reason_code == "no_viable_transport":
            player.stress = min(100, player.stress + 3)
            game_log.add_log_message("Being stranded adds stress (+3).")
        elif reason_code == "travel_time_exceeds_available_window":
            player.stress = min(100, player.stress + 5)
            game_log.add_log_message("Missing the window puts you under serious pressure (+5 stress).")
        elif reason_code == "vehicle_unavailable_or_broken":
            tow_cost = min(player.money, 60)
            player.money -= tow_cost
            player.stress = min(100, player.stress + 4)
            game_log.add_log_message(f"Vehicle trouble costs ${tow_cost} in emergency logistics and raises stress (+4).")
        elif reason_code == "currently_in_another_city":
            if "gig" in category or "job" in category:
                player.fame = max(0, player.fame - 2)
                game_log.add_log_message("Professional reliability takes a hit for poor routing (-2 fame).")
        elif reason_code == "energy_threshold_too_high":
            player.health = max(0, player.health - 1)
            player.stress = min(100, player.stress + 2)
            game_log.add_log_message("Running on empty hits your health (-1) and stress (+2).")

        # Risk flag consequences (lighter touch).
        for flag in resolution.risk_flags:
            if flag == "energy_risk_threshold_high":
                player.energy = max(0, player.energy - 2)
            elif flag == "stress_risk_threshold_high":
                player.health = max(0, player.health - 1)
            elif flag == "long_trip_fatigue_risk":
                player.energy = max(0, player.energy - 5)

        if resolution.risk_flags:
            game_log.add_log_message("Travel strain compounds due to current risk profile.")

        details["obligation_consequence_applied_at"] = eval_stamp
        details["obligation_consequence_time"] = current_game_time.get_time_string_for_schedule()
