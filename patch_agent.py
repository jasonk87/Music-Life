import re

with open('game/game.py', 'r') as f:
    content = f.read()

# We need to find the `handle_agent_menu` definition
pattern = r'(    def handle_agent_menu\(self\):\n        opts = \{\n)(.*?)(        \}\n        choice = self\.ui\.present_choices\(opts, "Agent on the line: \'What can I do for you\?\'"\))'

def replacement(match):
    opts_dict = match.group(2)
    opts_dict = opts_dict.replace('"find_gig": "Find Gig (Immediate)",', '"find_gig": "Find Gig (Immediate)",\n            "seek_label": "Seek Record Deal",')
    return match.group(1) + opts_dict + match.group(3)

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('game/game.py', 'w') as f:
    f.write(content)
