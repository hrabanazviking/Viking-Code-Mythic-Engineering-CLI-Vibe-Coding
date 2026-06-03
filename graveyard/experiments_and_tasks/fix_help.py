import re

with open("mythic_vibe_cli/app.py", "r") as f:
    content = f.read()

# We want to replace help="Some text" with help=_help("Some text") 
# but ONLY where it's part of an add_parser call or add_argument call?
# Actually, the requirement was to hide old commands. So replacing it inside add_parser is enough.
# Let's find lines with `add_parser(` and replace `help="..."` with `help=_help("...")`
# Note: we need to handle multi-line strings maybe? Usually help="something".

lines = content.split('\n')
in_parser = False
for i, line in enumerate(lines):
    if "add_parser(" in line or in_parser:
        in_parser = True
        # If it contains help=", we replace it
        if 'help="' in line and '_help("' not in line:
            lines[i] = re.sub(r'help="([^"]+)"', r'help=_help("\1")', line)
            in_parser = False
        elif 'help=(' in line:
            # We skip complex ones for now
            in_parser = False
        elif ')' in line:
            in_parser = False

with open("mythic_vibe_cli/app.py", "w") as f:
    f.write('\n'.join(lines))
