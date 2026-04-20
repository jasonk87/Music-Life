import re

with open('game/game.py', 'r') as f:
    content = f.read()

# Fix LOCATIONS -> WORLD_MAP
search_str = """                for loc in self.LOCATIONS.values():"""
replace_str = """                for loc in self.WORLD_MAP.values():"""
content = content.replace(search_str, replace_str)

with open('game/game.py', 'w') as f:
    f.write(content)
