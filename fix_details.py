import sys

def full_fix(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # In app.py, fix the sidebar logs which use st.markdown(f'<div...</div>')
    content = content.replace("st.markdown(f'<div", "render_html(f'<div")
    content = content.replace('st.markdown(f\"<div', 'render_html(f\"<div')
    
    # Also fix the header in app.py which is currently printed plain
    # Wait, the header in app.py is:
    # st.markdown(f\"\"\"
    # <div style=\"background...
    content = content.replace('st.markdown(f\"\"\"\n    <div style=\"background', 'render_html(f\"\"\"\n    <div style=\"background')
    
    # In visualizations.py, fix tab 7 to use receita instead of resumo for consultants
    if 'visualizations.py' in filepath:
        # Tab 7 consultant call: wait, there are two occurrences of `cdf = calculators.get_consultant_data_for_tab(data_raw, "resumo")`
        # We need to change the one in render_tab_receita.
        import re
        content = re.sub(
            r'(def render_tab_receita[\s\S]*?)get_consultant_data_for_tab\(data_raw, "resumo"\)',
            r'\1get_consultant_data_for_tab(data_raw, "receita")',
            content
        )
        
        # Tab 9 consultant store card
        search_str = 'st.markdown(f"#### Scorecard de Metas: **{cons_sel}** — Unidade: **{cons_data.get(\'Loja\', \'\')}**")'
        replace_str = search_str + '\n                    st.info(f"📍 Loja da Consultora: {cons_data.get(\'Loja\', \'N/A\')}")'
        content = content.replace(search_str, replace_str)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

full_fix('app.py')
full_fix('modules/visualizations.py')
print('Fixed!')
