import random

def check_for_band_drama(player, band):
    """
    Checks for drama events based on band chemistry and member satisfaction.
    Returns a dict with 'event_triggered': bool, 'message': str, 'effect_applied': bool.
    """
    result = {'event_triggered': False, 'message': "", 'effect_applied': False}

    if not band or len(band.members) <= 1:
        return result

    # Check Chemistry
    if band.chemistry < 30:
        if random.random() < 0.2: # 20% chance of chemistry drama
            result['event_triggered'] = True
            result['message'] = "The atmosphere in the rehearsal room is toxic. (Chemistry -5)"
            band.update_chemistry(-5)
            return result

    # Check Individual Members
    for member in band.members:
        if member == player: continue

        # Satisfaction Check
        if member.satisfaction < 30:
            if random.random() < 0.3:
                result['event_triggered'] = True
                result['message'] = f"{member.name} is visibly unhappy with the band's direction."
                # Risk of quitting if very low
                if member.satisfaction < 10 and random.random() < 0.5:
                     result['message'] += f" {member.name} threatens to QUIT if things don't improve!"
                return result

        # Ego Check (Demand Spotlight)
        if member.ego > 70:
            if random.random() < 0.1:
                result['event_triggered'] = True
                result['message'] = f"{member.name} complains about not getting enough solos. (Ego Clash)"
                member.satisfaction -= 5
                band.update_chemistry(-2)
                return result

        # Creative Control Check (triggered if player writes too many songs solo? - Logic needs state access)
        # For now, just random based on desire
        if member.creative_control_desire > 60:
             if random.random() < 0.05:
                 result['event_triggered'] = True
                 result['message'] = f"{member.name} demands more creative input on the next album."
                 member.satisfaction -= 2
                 return result

    return result

def resolve_weekly_wages(player, band):
    """
    Deducts wages. Returns report string.
    """
    if not band or len(band.members) <= 1:
        return None

    report = []
    total_wages = 0
    for member in band.members:
        if member == player: continue

        wage = member.wage_demand
        if player.money >= wage:
            player.money -= wage
            member.satisfaction = min(100, member.satisfaction + 2) # Paid happy
            total_wages += wage
        else:
            member.satisfaction -= 10 # Unpaid unhappy
            report.append(f"Could not pay {member.name} (${wage}). They are furious.")

    if total_wages > 0:
        report.append(f"Paid total wages of ${total_wages}.")

    return "\n".join(report)


def check_creative_friction(player, band, action_type: str) -> str:
    """
    Triggers creative friction when commercial/indie decisions clash with band member values.
    """
    if not band or len(band.members) <= 1:
        return ""

    messages = []
    if action_type == "signed_major_label":
        for member in band.members:
            if member == player:
                continue
            if getattr(member, "indie_authenticity_preference", 0.7) > 0.6:
                member.satisfaction = max(0, member.satisfaction - 15)
                messages.append(f"{member.name} hates signing with a major label ('We sold out!').")
        band.update_chemistry(-10)
    elif action_type == "diy_gig_success":
        for member in band.members:
            if member == player:
                continue
            member.satisfaction = min(100, member.satisfaction + 5)
        band.update_chemistry(5)

    return "\n".join(messages)

