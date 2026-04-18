import re

with open('game/contract.py', 'r') as f:
    content = f.read()

# Update negotiate signature and logic in Contract class
search_str = """    def negotiate(self, player_fame, player_charisma_trait=False):"""
replace_str = """    def negotiate(self, player_fame, player_charisma_trait=False, manager_skill=0):"""
content = content.replace(search_str, replace_str)

search_str2 = """        roll = random.random()
        if player_charisma_trait:
            roll += 0.15

        if roll > difficulty:"""
replace_str2 = """        roll = random.random()
        if player_charisma_trait:
            roll += 0.15

        # Manager skill adds a bonus directly to the roll (up to +0.25 at skill 5)
        roll += (manager_skill * 0.05)

        if roll > difficulty:"""
content = content.replace(search_str2, replace_str2)

with open('game/contract.py', 'w') as f:
    f.write(content)
