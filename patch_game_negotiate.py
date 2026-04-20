import re

with open('game/game.py', 'r') as f:
    content = f.read()

# Modify handle_phone_menu label_offers part
search_str = """            contract = self.player.pending_contracts[0]
            offer_options = {
                "accept": "Accept Offer",
                "negotiate": f"Negotiate Terms ({contract.label_patience} attempts left)",
                "decline": "Decline Offer",
                "back": "Decide later"
            }"""

replace_str = """            contract = self.player.pending_contracts[0]
            offer_options = {
                "accept": "Accept Offer",
                "negotiate": f"Negotiate Terms ({contract.label_patience} attempts left)",
            }
            if self.player.has_manager:
                offer_options["manager_negotiate"] = f"Ask Manager to Negotiate ({contract.label_patience} attempts left)"
            offer_options["decline"] = "Decline Offer"
            offer_options["back"] = "Decide later" """
content = content.replace(search_str, replace_str)


search_str2 = """            elif choice == "negotiate":
                has_charisma = self.player.has_trait("charismatic")
                success, msg, pulled = contract.negotiate(self.player.fame, has_charisma)
                self.GAME_LOG.add_log_message(msg)
                if pulled:
                    self.player.pending_contracts.pop(0)
                    self.phone_menu_state = "main" """

replace_str2 = """            elif choice == "negotiate":
                has_charisma = self.player.has_trait("charismatic")
                success, msg, pulled = contract.negotiate(self.player.fame, has_charisma)
                self.GAME_LOG.add_log_message(msg)
                if pulled:
                    self.player.pending_contracts.pop(0)
                    self.phone_menu_state = "main"
            elif choice == "manager_negotiate":
                manager_skill = 1
                for staff in self.player.staff:
                    if staff.role == "Manager":
                        manager_skill = staff.skill_level
                        break

                self.GAME_LOG.add_log_message("Manager: 'Let me handle this. I'll get us a better deal.'")
                has_charisma = self.player.has_trait("charismatic")
                success, msg, pulled = contract.negotiate(self.player.fame, has_charisma, manager_skill=manager_skill)
                self.GAME_LOG.add_log_message(msg)
                if pulled:
                    self.player.pending_contracts.pop(0)
                    self.phone_menu_state = "main" """
content = content.replace(search_str2, replace_str2)


with open('game/game.py', 'w') as f:
    f.write(content)
