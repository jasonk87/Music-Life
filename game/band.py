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
