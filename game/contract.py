class Contract:
    def __init__(self, label_name, advance_money, royalty_rate, marketing_budget_per_release):
        self.label_name = label_name
        self.advance_money = advance_money
        self.royalty_rate = royalty_rate  # e.g., 0.15 for 15%
        self.marketing_budget_per_release = marketing_budget_per_release
        self.is_active = True

    def __str__(self):
        return (f"Record Deal with {self.label_name}\n"
                f" - Advance: ${self.advance_money}\n"
                f" - Royalty Rate: {self.royalty_rate * 100}%\n"
                f" - Marketing per Release: ${self.marketing_budget_per_release}")
