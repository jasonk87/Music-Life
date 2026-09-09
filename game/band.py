class Band:
    def __init__(self, name, leader):
        self.name = name
        self.members = [leader] # The player is the leader and first member
        self.band_skills = self.calculate_band_skills()
        self.chemistry = 50 # 0-100
        self.funds = 0 # Independent band fund (optional, could just use player money)

    def add_member(self, new_member):
        if new_member not in self.members:
            self.members.append(new_member)
            self.recalculate_skills()
            # Initial chemistry impact: usually drops slightly when adding new person
            self.chemistry = max(0, self.chemistry - 10)
            print(f"{new_member.name} has joined {self.name}!")

    def remove_member(self, member):
        if member in self.members and member != self.members[0]: # Cannot remove leader
            self.members.remove(member)
            self.recalculate_skills()
            self.chemistry = max(0, self.chemistry - 5)

    def update_chemistry(self, amount):
        self.chemistry = max(0, min(100, self.chemistry + amount))

    def recalculate_skills(self):
        self.band_skills = self.calculate_band_skills()

    def calculate_band_skills(self):
        # A simple average of all members' skills for now.
        # This could be made more complex later (e.g., highest skill takes precedence).
        if not self.members:
            return {}

        total_skills = {}
        for member in self.members:
            for skill, value in member.skills.items():
                if skill not in total_skills:
                    total_skills[skill] = 0
                total_skills[skill] += value

        # Average the skills
        avg_skills = {skill: round(value / len(self.members), 1) for skill, value in total_skills.items()}
        return avg_skills

    def __str__(self):
        member_names = [member.name for member in self.members]
        return f"Band: {self.name} (Members: {', '.join(member_names)})"


class BandMember:
    def __init__(self, name: str, role: str = "Guitar", skill_level: int = 5, wage_demand: int = 50):
        self.name = name
        self.role = role
        self.skills = {
            "songwriting": skill_level,
            "guitar": skill_level,
            "vocals": skill_level,
            "stage_presence": skill_level,
            "electronic": skill_level,
        }
        self.satisfaction = 70
        self.ego = 50
        self.creative_control_desire = 50
        self.wage_demand = wage_demand
        self.indie_authenticity_preference = 0.7

