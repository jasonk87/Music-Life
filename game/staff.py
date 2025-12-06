class StaffMember:
    def __init__(self, name, role, wage_per_week, skill_level=1):
        self.name = name
        self.role = role # "Roadie", "Bodyguard", "Manager"
        self.wage_per_week = wage_per_week
        self.skill_level = skill_level # 1-10
        self.satisfaction = 100

    def __str__(self):
        return f"{self.name} ({self.role}, Lvl {self.skill_level}) - ${self.wage_per_week}/wk"
