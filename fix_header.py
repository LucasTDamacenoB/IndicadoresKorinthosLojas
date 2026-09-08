import sys
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'st.markdown(textwrap.dedent(f"""\n    <div style="background: linear-gradient(135deg',
    'render_html(f"""\n    <div style="background: linear-gradient(135deg'
)
content = content.replace('    """))', '    """)')

content = content.replace("st.html(\"<div style='background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 20px; margin-bottom: 20px;'>\")", "")
content = content.replace("st.html(\"</div>\")", "")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('modules/visualizations.py', 'r', encoding='utf-8') as f:
    vis = f.read()

# Replace status badges with icons only
vis = vis.replace('✓ META BATIDA', '✓')
vis = vis.replace('✕ ABAIXO DA META', '✕')

with open('modules/visualizations.py', 'w', encoding='utf-8') as f:
    f.write(vis)

print('Done!')
