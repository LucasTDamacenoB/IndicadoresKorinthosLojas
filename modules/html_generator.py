import os
import pandas as pd
from modules.config import get_pdv_label, TARGET_PDVS

def format_currency(val):
    if pd.isna(val): return "R$ 0,00"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(val):
    if pd.isna(val): return "0,0%"
    return f"{val*100:.1f}%".replace(".", ",")

def format_num(val, dec=1):
    if pd.isna(val): return "0"
    if dec == 0: return f"{int(val)}"
    return f"{val:.{dec}f}".replace(".", ",")

def check_color(val, meta, greater_is_better=True):
    if pd.isna(val): return "text-slate-700"
    if greater_is_better:
        return "text-emerald-600 font-bold" if val >= meta else "text-red-500 font-bold"
    else:
        return "text-emerald-600 font-bold" if val <= meta else "text-red-500 font-bold"

def get_base_html():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apresentação de Resultados - Visão Mensal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
        .custom-scrollbar::-webkit-scrollbar { height: 8px; width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="text-slate-800 antialiased h-screen flex overflow-hidden" x-data="{ activeTab: 'resumo' }">
    
    <!-- SIDEBAR -->
    <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 shadow-xl z-20">
        <div class="p-6 border-b border-slate-800">
            <h1 class="text-xl font-bold text-white leading-tight">CP Korinthos</h1>
            <p class="text-xs text-sky-400 font-medium mt-1">Resultados Fechamento</p>
        </div>
        <nav class="flex-1 overflow-y-auto py-4 custom-scrollbar">
            <ul class="flex flex-col space-y-1">
                <li><button @click="activeTab = 'resumo'" :class="activeTab === 'resumo' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-table-cells w-5 text-center text-sky-400"></i> Resumo Geral</button></li>
                <li><button @click="activeTab = 'nps'" :class="activeTab === 'nps' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-face-smile w-5 text-center"></i> 1. NPS</button></li>
                <li><button @click="activeTab = 'tme'" :class="activeTab === 'tme' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-stopwatch w-5 text-center"></i> 2. TME e Conversão</button></li>
                <li><button @click="activeTab = 'idcliente'" :class="activeTab === 'idcliente' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-id-card w-5 text-center"></i> 3. ID Cliente</button></li>
                <li><button @click="activeTab = 'fidelidade'" :class="activeTab === 'fidelidade' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-star w-5 text-center"></i> 4. Fidelidade</button></li>
                <li><button @click="activeTab = 'skin'" :class="activeTab === 'skin' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-pump-soap w-5 text-center"></i> 5. Skin Lojas</button></li>
                <li><button @click="activeTab = 'receita'" :class="activeTab === 'receita' ? 'bg-slate-800 text-white border-l-4 border-sky-400' : 'border-l-4 border-transparent'" class="w-full text-left px-6 py-3 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-3"><i class="fa-solid fa-sack-dollar w-5 text-center"></i> 6. Receita</button></li>
            </ul>
        </nav>
    </aside>

    <!-- MAIN CONTENT -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden bg-slate-50">
        <header class="bg-white px-8 py-5 shadow-sm z-10 border-b border-slate-200">
            <h2 class="text-2xl font-bold text-slate-800" x-text="
                activeTab === 'resumo' ? 'Resumo Geral de Performance' :
                activeTab === 'nps' ? '1. Experiência do Cliente (NPS)' :
                activeTab === 'tme' ? '2. TME e Conversão de Atendimento' :
                activeTab === 'idcliente' ? '3. ID Cliente (< 2min)' :
                activeTab === 'fidelidade' ? '4. Penetração Desafio Fidelidade' :
                activeTab === 'skin' ? '5. Cuidados Faciais (Skin Lojas)' :
                '6. Receita e Metas PEF'
            "></h2>
        </header>
        
        <div class="flex-1 overflow-y-auto p-6 lg:p-8 custom-scrollbar">
            {content_tabs}
        </div>
    </main>
</body>
</html>
"""

def _build_consultants_table(pdv, consultant_df, cols):
    if consultant_df is None or consultant_df.empty: return ""
    
    pdv_col = "PDV" if "PDV" in consultant_df.columns else "pdv"
    cons_col = "Consultor" if "Consultor" in consultant_df.columns else "consultor"
    
    pdv_df = consultant_df[consultant_df[pdv_col].astype(str) == pdv]
    if pdv_df.empty: return ""
    
    # Sort by revenue if available, otherwise by name
    if "Receita" in pdv_df.columns:
        pdv_df = pdv_df.sort_values("Receita", ascending=False)
    
    th_html = "".join([f"<th class='px-4 py-2 text-right font-semibold'>{c['label']}</th>" for c in cols])
    
    rows_html = ""
    for _, row in pdv_df.iterrows():
        name = str(row[cons_col])
        cells = ""
        for c in cols:
            val = row.get(c['key'])
            if pd.isna(val) and 'fallback' in c:
                val = row.get(c['fallback'])
            
            fmt_val = c['fmt'](val) if pd.notna(val) else "-"
            cells += f"<td class='px-4 py-2 text-right text-slate-600'>{fmt_val}</td>"
            
        rows_html += f"<tr class='hover:bg-slate-50 border-b border-slate-100 last:border-0'><td class='px-4 py-2 font-medium text-slate-700'>{name}</td>{cells}</tr>"
        
    return f"""
    <tr x-show="open" x-transition.opacity style="display: none;">
        <td colspan="{len(cols) + 1}" class="p-0 bg-slate-100">
            <div class="p-4 pl-12 border-b border-slate-200">
                <div class="flex items-center gap-2 mb-2">
                    <i class="fa-solid fa-users text-sky-600 text-xs"></i>
                    <h4 class="text-xs font-bold text-sky-800 uppercase tracking-wider">Desempenho da Equipe</h4>
                </div>
                <table class="min-w-full text-xs bg-white shadow-sm border border-slate-200 rounded overflow-hidden">
                    <thead class="bg-slate-50 text-slate-600 border-b border-slate-200">
                        <tr><th class="px-4 py-2 text-left font-semibold">Consultor</th>{th_html}</tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </td>
    </tr>
    """

def build_nps_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'nps'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600"># Registros</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">NPS <br><span class="text-xs font-normal">(Meta: 90.9)</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    # CP ROW
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-center">{format_num(cp_summary.get('nps_registros', 0), 0)}</td>
        <td class="px-6 py-4 text-center {check_color(cp_summary.get('nps_geral'), 90.9)}">{format_num(cp_summary.get('nps_geral'), 1)}</td>
    </tr>
    """
    
    # PDV ROWS
    cons_cols = [{"label": "NPS", "key": "nps", "fmt": lambda v: format_num(v, 1)}]
    
    # Sort
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("nps", ascending=False)
    for pdv, row in sorted_df.iterrows():
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-center text-slate-700">{format_num(row.get('nps_registros', 0), 0)}</td>
                <td class="px-6 py-4 text-center {check_color(row.get('nps'), 90.9)}">{format_num(row.get('nps'), 1)}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def build_tme_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'tme'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">TME Ajustado <br><span class="text-xs font-normal">(Meta: 07m)</span></th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">Conversão <br><span class="text-xs font-normal">(Meta: 10%)</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    tme_val = cp_summary.get('tme_ajustado_segundos', 0) / 60.0 if pd.notna(cp_summary.get('tme_ajustado_segundos')) else 0
    # CP ROW
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-center {check_color(tme_val, 7, False)}">-</td>
        <td class="px-6 py-4 text-center {check_color(cp_summary.get('conversao_acao_fluxo', 0)*100, 10)}">{format_pct(cp_summary.get('conversao_acao_fluxo'))}</td>
    </tr>
    """
    
    # PDV ROWS
    cons_cols = [
        {"label": "Conversão Ação Fluxo", "key": "Conversão Ação Fluxo", "fallback": "conversao_acao_fluxo", "fmt": lambda v: format_pct(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("tme_ajustado_segundos", ascending=True)
    for pdv, row in sorted_df.iterrows():
        t_val = row.get('tme_ajustado_segundos', 0) / 60.0 if pd.notna(row.get('tme_ajustado_segundos')) else 0
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-center {check_color(t_val, 7, False)}">{row.get('tme_ajustado', '-')}</td>
                <td class="px-6 py-4 text-center {check_color(row.get('conversao_acao_fluxo', 0)*100, 10)}">{format_pct(row.get('conversao_acao_fluxo'))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def build_receita_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'receita'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-right font-semibold text-slate-600">Receita Total</th>
                    <th class="px-6 py-3 text-right font-semibold text-slate-600">% Meta PEF</th>
                    <th class="px-6 py-3 text-right font-semibold text-slate-600">Vol. Boletos</th>
                    <th class="px-6 py-3 text-right font-semibold text-slate-600">Ticket Médio</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    # CP ROW
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-right">{format_currency(cp_summary.get('receita_total'))}</td>
        <td class="px-6 py-4 text-right {check_color(cp_summary.get('meta_pef_realizado', 0)*100, 100)}">{format_pct(cp_summary.get('meta_pef_realizado', 0))}</td>
        <td class="px-6 py-4 text-right">{format_num(cp_summary.get('volume_boletos', 0), 0)}</td>
        <td class="px-6 py-4 text-right">{format_currency(cp_summary.get('ticket_medio'))}</td>
    </tr>
    """
    
    # PDV ROWS
    cons_cols = [
        {"label": "Receita", "key": "Receita", "fallback": "receita", "fmt": lambda v: format_currency(v)},
        {"label": "Boletos", "key": "Quantidade de Boletos", "fallback": "volume_boletos", "fmt": lambda v: format_num(v, 0)},
        {"label": "Ticket Médio", "key": "Boleto Médio", "fallback": "ticket_medio", "fmt": lambda v: format_currency(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("receita", ascending=False)
    for pdv, row in sorted_df.iterrows():
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-right text-slate-700 font-semibold">{format_currency(row.get('receita'))}</td>
                <td class="px-6 py-4 text-right {check_color(row.get('meta_pef_realizado', 0)*100, 100)}">{format_pct(row.get('meta_pef_realizado', 0))}</td>
                <td class="px-6 py-4 text-right text-slate-700">{format_num(row.get('volume_boletos', 0), 0)}</td>
                <td class="px-6 py-4 text-right text-slate-700">{format_currency(row.get('ticket_medio'))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def build_resumo_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'resumo'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm whitespace-nowrap">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-4 py-3 text-left font-semibold text-slate-600 border-r border-slate-200">PDV</th>
                    <th class="px-4 py-3 text-right font-semibold text-slate-600">Receita</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600 border-x border-slate-200">NPS</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600">TME</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600 border-r border-slate-200">Conv.</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600">ID < 2m</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600">Fidelid.</th>
                    <th class="px-4 py-3 text-center font-semibold text-slate-600 border-l border-slate-200">Skin</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    tme_val = cp_summary.get('tme_ajustado_segundos', 0) / 60.0 if pd.notna(cp_summary.get('tme_ajustado_segundos')) else 0
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-4 py-4 border-r border-sky-200 flex justify-between">CP KORINTHOS</td>
        <td class="px-4 py-4 text-right">{format_currency(cp_summary.get('receita_total'))}</td>
        <td class="px-4 py-4 text-center border-x border-sky-200 {check_color(cp_summary.get('nps_geral'), 90.9)}">{format_num(cp_summary.get('nps_geral'), 1)}</td>
        <td class="px-4 py-4 text-center {check_color(tme_val, 7, False)}">-</td>
        <td class="px-4 py-4 text-center border-r border-sky-200 {check_color(cp_summary.get('conversao_acao_fluxo', 0)*100, 10)}">{format_pct(cp_summary.get('conversao_acao_fluxo', 0))}</td>
        <td class="px-4 py-4 text-center">-</td>
        <td class="px-4 py-4 text-center {check_color(cp_summary.get('penetracao_desafio_fidelidade', 0)*100, 20)}">{format_pct(cp_summary.get('penetracao_desafio_fidelidade', 0))}</td>
        <td class="px-4 py-4 text-center border-l border-sky-200 {check_color(cp_summary.get('cuidados_faciais', 0)*100, 2.1)}">{format_pct(cp_summary.get('cuidados_faciais', 0))}</td>
    </tr>
    """
    
    cons_cols = [
        {"label": "Receita", "key": "Receita", "fallback": "receita", "fmt": lambda v: format_currency(v)},
        {"label": "NPS", "key": "nps", "fmt": lambda v: format_num(v, 1)},
        {"label": "Conversão", "key": "Conversão Ação Fluxo", "fmt": lambda v: format_pct(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("receita", ascending=False)
    for pdv, row in sorted_df.iterrows():
        t_val = row.get('tme_ajustado_segundos', 0) / 60.0 if pd.notna(row.get('tme_ajustado_segundos')) else 0
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors border-b border-slate-100">
                <td class="px-4 py-4 font-medium text-slate-800 border-r border-slate-200 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-4 py-4 text-right text-slate-700 font-semibold">{format_currency(row.get('receita'))}</td>
                <td class="px-4 py-4 text-center border-x border-slate-200 {check_color(row.get('nps'), 90.9)}">{format_num(row.get('nps'), 1)}</td>
                <td class="px-4 py-4 text-center {check_color(t_val, 7, False)}">{row.get('tme_ajustado', '-')}</td>
                <td class="px-4 py-4 text-center border-r border-slate-200 {check_color(row.get('conversao_acao_fluxo', 0)*100, 10)}">{format_pct(row.get('conversao_acao_fluxo', 0))}</td>
                <td class="px-4 py-4 text-center {check_color(row.get('id_cliente_2m', 0)*100, 30, False)}">{format_pct(row.get('id_cliente_2m', 0))}</td>
                <td class="px-4 py-4 text-center {check_color(row.get('penetracao_desafio_fidelidade', 0)*100, 20)}">{format_pct(row.get('penetracao_desafio_fidelidade', 0))}</td>
                <td class="px-4 py-4 text-center border-l border-slate-200 {check_color(row.get('cuidados_faciais', 0)*100, 2.1)}">{format_pct(row.get('cuidados_faciais', 0))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</table></div>"
    return html

def build_idcliente_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'idcliente'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">ID Cliente <br><span class="text-xs font-normal">(Meta: 115%)</span></th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">ID Cliente < 2m <br><span class="text-xs font-normal">(Meta: 30%)</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-center {check_color(cp_summary.get('id_cliente', 0)*100, 115)}">{format_pct(cp_summary.get('id_cliente', 0))}</td>
        <td class="px-6 py-4 text-center">-</td>
    </tr>
    """
    
    cons_cols = [
        {"label": "% Boletos ID Cliente", "key": "% Boletos ID Cliente", "fmt": lambda v: format_pct(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("id_cliente", ascending=False)
    for pdv, row in sorted_df.iterrows():
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-center {check_color(row.get('id_cliente', 0)*100, 115)}">{format_pct(row.get('id_cliente', 0))}</td>
                <td class="px-6 py-4 text-center {check_color(row.get('id_cliente_2m', 0)*100, 30, False)}">{format_pct(row.get('id_cliente_2m', 0))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def build_fidelidade_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'fidelidade'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">Penetração Fidelidade <br><span class="text-xs font-normal">(Meta: 20%)</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-center {check_color(cp_summary.get('penetracao_desafio_fidelidade', 0)*100, 20)}">{format_pct(cp_summary.get('penetracao_desafio_fidelidade', 0))}</td>
    </tr>
    """
    
    cons_cols = [
        {"label": "Penetração Fidelidade", "key": "Penetração Boletos Fidelidade", "fmt": lambda v: format_pct(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("penetracao_desafio_fidelidade", ascending=False)
    for pdv, row in sorted_df.iterrows():
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-center {check_color(row.get('penetracao_desafio_fidelidade', 0)*100, 20)}">{format_pct(row.get('penetracao_desafio_fidelidade', 0))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def build_skin_tab(df, cp_summary, consultant_df):
    html = """
    <div x-show="activeTab === 'skin'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="px-6 py-3 text-left font-semibold text-slate-600">PDV</th>
                    <th class="px-6 py-3 text-center font-semibold text-slate-600">Skin Lojas <br><span class="text-xs font-normal">(Meta: 2.1%)</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
    """
    
    html += f"""
    <tr class="bg-sky-50 text-slate-900 border-b-2 border-sky-200 font-bold">
        <td class="px-6 py-4">CP KORINTHOS</td>
        <td class="px-6 py-4 text-center {check_color(cp_summary.get('cuidados_faciais', 0)*100, 2.1)}">{format_pct(cp_summary.get('cuidados_faciais', 0))}</td>
    </tr>
    """
    
    cons_cols = [
        {"label": "Cuidados Faciais", "key": "Penetração Cuidados Faciais", "fmt": lambda v: format_pct(v)}
    ]
    
    sorted_df = df[df.index.isin(TARGET_PDVS)].sort_values("cuidados_faciais", ascending=False)
    for pdv, row in sorted_df.iterrows():
        cons_html = _build_consultants_table(pdv, consultant_df, cons_cols)
        html += f"""
        <tbody x-data="{{ open: false }}" class="group">
            <tr @click="open = !open" class="hover:bg-slate-50 cursor-pointer transition-colors">
                <td class="px-6 py-4 font-medium text-slate-800 flex justify-between items-center">
                    {get_pdv_label(pdv)} 
                    <i class="fa-solid fa-chevron-down text-xs text-slate-400 group-hover:text-sky-500 transition-colors" :class="open ? 'rotate-180' : ''"></i>
                </td>
                <td class="px-6 py-4 text-center {check_color(row.get('cuidados_faciais', 0)*100, 2.1)}">{format_pct(row.get('cuidados_faciais', 0))}</td>
            </tr>
            {cons_html}
        </tbody>
        """
        
    html += "</tbody></table></div>"
    return html

def generate_html(df, cp_summary, consultant_df, output_path):
    """Generates the static HTML dashboard from scratch directly."""
    base_html = get_base_html()
    
    tabs_html = ""
    tabs_html += build_resumo_tab(df, cp_summary, consultant_df)
    tabs_html += build_nps_tab(df, cp_summary, consultant_df)
    tabs_html += build_tme_tab(df, cp_summary, consultant_df)
    tabs_html += build_idcliente_tab(df, cp_summary, consultant_df)
    tabs_html += build_fidelidade_tab(df, cp_summary, consultant_df)
    tabs_html += build_skin_tab(df, cp_summary, consultant_df)
    tabs_html += build_receita_tab(df, cp_summary, consultant_df)
    
    final_html = base_html.replace("{content_tabs}", tabs_html)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
