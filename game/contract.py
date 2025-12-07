import random

class Contract:
    def __init__(self, label_name, advance_money, royalty_rate, marketing_budget_per_release):
        self.label_name = label_name
        self.advance_money = advance_money
        self.royalty_rate = royalty_rate  # e.g., 0.15 for 15%
        self.marketing_budget_per_release = marketing_budget_per_release
        self.is_active = True

        # Negotiation State
        self.label_patience = 3 # Number of attempts before they rescind
        self.offer_quality = self.calculate_value()

    def calculate_value(self):
        # Rough heuristic for "how good is this offer"
        return self.advance_money + (self.royalty_rate * 100000) + (self.marketing_budget_per_release * 5)

    def negotiate(self, player_fame, player_charisma_trait=False):
        """
        Attempts to improve the contract.
        Returns (success: bool, message: str, offer_pulled: bool)
        """
        if self.label_patience <= 0:
            return False, "The label has lost patience. Take it or leave it.", False

        # Difficulty based on current offer value vs Fame
        # If offer is low compared to fame, easier to negotiate.
        # If offer is already generous, harder.

        target_value = player_fame * 50 # Baseline expectation
        current_value = self.calculate_value()

        difficulty = 0.5
        if current_value > target_value:
            difficulty += 0.3 # Greedy

        roll = random.random()
        if player_charisma_trait:
            roll += 0.15

        if roll > difficulty:
            # Success: Improve one aspect randomly
            improvement = random.choice(["advance", "royalty", "marketing"])
            if improvement == "advance":
                boost = int(self.advance_money * 0.2)
                self.advance_money += boost
                msg = f"They agreed to increase the advance by ${boost}!"
            elif improvement == "royalty":
                boost = 0.02
                if self.royalty_rate + boost <= 0.50:
                    self.royalty_rate += boost
                    msg = "They bumped the royalty rate by 2%!"
                else:
                    self.advance_money += 1000 # Fallback
                    msg = "They couldn't move on royalties, but added $1000 to the advance."
            else:
                boost = int(self.marketing_budget_per_release * 0.2)
                self.marketing_budget_per_release += boost
                msg = f"They increased the marketing budget by ${boost}."

            self.label_patience -= 1
            return True, msg, False
        else:
            # Failure
            self.label_patience -= 1
            if self.label_patience <= 0:
                return False, "They refused. 'That's our final offer. Don't push your luck.'", False

            # Risk of pulling offer?
            if random.random() < 0.1:
                return False, "They got offended by your greed! Offer RESCINDED.", True

            return False, "They wouldn't budge this time.", False

    def __str__(self):
        return (f"Record Deal with {self.label_name}\n"
                f" - Advance: ${self.advance_money}\n"
                f" - Royalty Rate: {self.royalty_rate * 100:.1f}%\n"
                f" - Marketing per Release: ${self.marketing_budget_per_release}")
