import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'import textwrap' not in content:
        content = 'import textwrap\n' + content

    content = re.sub(
        r'(st\.markdown\(\s*)(f\"\"\"[\s\S]*?\"\"\")(\s*,\s*unsafe_allow_html=True\s*\))',
        r'\1textwrap.dedent(\2)\3',
        content
    )
    content = re.sub(
        r'(st\.markdown\(\s*)(\"\"\"[\s\S]*?\"\"\")(\s*,\s*unsafe_allow_html=True\s*\))',
        r'\1textwrap.dedent(\2)\3',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

process_file('app.py')
process_file('modules/visualizations.py')
print('Fixed!')
