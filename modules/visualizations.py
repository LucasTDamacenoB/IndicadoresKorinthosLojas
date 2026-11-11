import textwrap
import streamlit as st
import re

def render_html(html_str):
    if not html_str: return
    clean = re.sub(r'\n\s*', ' ', html_str)
    st.markdown(clean, unsafe_allow_html=True)

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional

import modules.config as config
import modules.calculators as calculators
from modules.calculators import format_delta, is_inverted_metric
from modules.config import TARGET_PDVS, get_pdv_label


# ═══════════════════════════════════════════════════════════════════
# FUNÇÕES DE FORMATAÇÃO E FILTRAGEM (BR FORMATTING & FILTERS)
# ═══════════════════════════════════════════════════════════════════

def fmt_pct(val, decimals=2):
    """Formata valor percentual para padrão BR com vírgula (ex: 0.1127 -> 11,27% ou 1.1127 -> 111,27%)."""
    if pd.isna(val) or val is None:
        return "-"
    try:
        fval = float(val)
        formatted = f"{fval * 100:,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{formatted}%"
    except (ValueError, TypeError):
        return str(val)

def fmt_brl(val):
    """Formata valor monetário para padrão BR (ex: 219367.04 -> R$ 219.367,04)."""
    if pd.isna(val) or val is None:
        return "R$ 0,00"
    try:
        fval = float(val)
        formatted = f"{fval:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return str(val)

def filter_consultants(cdf: pd.DataFrame, excluir_gerencia: bool = True, busca_consultora: str = "") -> pd.DataFrame:
    """Filtra consultoras conforme regras estritas (Sem gerente, busca de texto, remove 'TODOS', etc.)."""
    if cdf is None or cdf.empty:
        return cdf
    
    col_nome = None
    for c in ["CONSULTOR(A)", "CONSULTOR", "Consultor", "Nome"]:
        if c in cdf.columns:
            col_nome = c
            break
            
    if col_nome:
        invalid_names = ["TODOS", "TOTAL", "GERAL", "NAN"]
        cdf = cdf[~cdf[col_nome].astype(str).str.upper().str.strip().isin(invalid_names)]
        
        if excluir_gerencia:
            cdf = cdf[~cdf[col_nome].astype(str).str.contains("SAMANTA MORETTI", case=False, na=False)]
            
        if busca_consultora:
            cdf = cdf[cdf[col_nome].astype(str).str.contains(busca_consultora, case=False, na=False)]
            
    return cdf


def _get_deltas(data_raw):
    """Extrai dicts de deltas do data_raw injetado pelo app.py."""
    if not data_raw:
        return {}, pd.DataFrame()
    return data_raw.get("_deltas_cp", {}), data_raw.get("_deltas_pdv", pd.DataFrame())


def _delta_col_for_pdv(deltas_pdv, df_filtered, col_name, fmt_type="pct", inverted=False):
    """Gera uma Series com texto formatado de delta para uma coluna específica por PDV."""
    delta_key = f"delta_{col_name}"
    if deltas_pdv.empty or delta_key not in deltas_pdv.columns:
        return None
    
    merged = df_filtered[["pdv"]].merge(deltas_pdv[["pdv", delta_key]], on="pdv", how="left")
    return merged[delta_key].apply(lambda x: format_delta(x, fmt_type, inverted, as_html=False) or "-")


# ═══════════════════════════════════════════════════════════════════
# COMPONENTES VISUAIS REUTILIZÁVEIS E THEME SYSTEM
# ═══════════════════════════════════════════════════════════════════

def safe_styler(styler_obj):
    """Garante compatibilidade com todas as versões do Pandas Styler e aplica highlighting de status."""
    if not hasattr(styler_obj, 'applymap') and hasattr(styler_obj, 'map'):
        setattr(styler_obj, 'applymap', styler_obj.map)
        
    def highlight_status(val):
        if isinstance(val, str):
            if '❌' in val or 'Abaixo' in val or 'Excedido' in val:
                return 'color: #DC2626; font-weight: 700;'
            if '✓' in val or '✅' in val or 'Batida' in val or 'Atingida' in val or 'No Prazo' in val:
                return 'color: #059669; font-weight: 700;'
        return ''
        
    return styler_obj.applymap(highlight_status)

def style_table(df_show: pd.DataFrame, highlight_rules: dict = None):
    """
    Aplica formatação visual profissional ao DataFrame:
    - Destaca status em Verde (✓ / ✅) e Vermelho (❌)
    - Aplica regras customizadas por coluna (ex: TME > 7min em vermelho, Vs. Anterior negativo em vermelho, etc.)
    - Aplica automaticamente destaque de cores para colunas com setas de variação (Δ / Delta)
    """
    styler = df_show.style
    
    def highlight_status(val):
        if not isinstance(val, str):
            return ''
        if '❌' in val or 'Abaixo' in val or 'Excedido' in val:
            return 'color: #DC2626; font-weight: 700;'
        if '✓' in val or '✅' in val or 'Batida' in val or 'Atingida' in val or 'No Prazo' in val:
            return 'color: #059669; font-weight: 700;'
        return ''

    def highlight_delta(val, inverted=False):
        if not isinstance(val, str):
            return ''
        if '🔼' in val:
            return 'color: #DC2626; font-weight: 700;' if inverted else 'color: #059669; font-weight: 700;'
        if '🔽' in val:
            return 'color: #059669; font-weight: 700;' if inverted else 'color: #DC2626; font-weight: 700;'
        if '➡️' in val:
            return 'color: #64748B; font-weight: 600;'
        return ''
        
    if hasattr(styler, 'map'):
        styler = styler.map(highlight_status)
    elif hasattr(styler, 'applymap'):
        styler = styler.applymap(highlight_status)

    for col in df_show.columns:
        if 'Δ' in col or 'Delta' in col:
            is_inv = any(inv in col.lower() for inv in ['tme', '2min', 'tempo'])
            rule = (lambda v, inv=is_inv: highlight_delta(v, inv))
            if hasattr(styler, 'map'):
                styler = styler.map(rule, subset=[col])
            elif hasattr(styler, 'applymap'):
                styler = styler.applymap(rule, subset=[col])
        
    if highlight_rules:
        for col_name, rule_fn in highlight_rules.items():
            if col_name in df_show.columns:
                if hasattr(styler, 'map'):
                    styler = styler.map(rule_fn, subset=[col_name])
                elif hasattr(styler, 'applymap'):
                    styler = styler.applymap(rule_fn, subset=[col_name])
                    
    return styler

def render_header_badges(pilar: str, pontos: str, classificacao: str = "Oficial"):
    """Renderiza badges padronizadas no nível 1 do módulo."""
    tag_bg = "#ECFDF5" if "Comercial" in pilar or "Oficial" in classificacao else "#EFF6FF"
    tag_border = "#A7F3D0" if "Comercial" in pilar or "Oficial" in classificacao else "#BFDBFE"
    tag_text = "#065F46" if "Comercial" in pilar or "Oficial" in classificacao else "#1E40AF"

    badge_pts_bg = "#FEF3C7" if "pts" in str(pontos).lower() or "pontos" in str(pontos).lower() else "#F3E8FF"
    badge_pts_text = "#92400E" if "pts" in str(pontos).lower() or "pontos" in str(pontos).lower() else "#6B21A8"
    badge_pts_border = "#FDE68A" if "pts" in str(pontos).lower() or "pontos" in str(pontos).lower() else "#E9D5FF"

    render_html(f"""
    <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px;">
        <span style="background-color: {tag_bg}; color: {tag_text}; border: 1px solid {tag_border};
                     padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
            🏛️ Pilar: {pilar}
        </span>
        <span style="background-color: {badge_pts_bg}; color: {badge_pts_text}; border: 1px solid {badge_pts_border};
                     padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;">
            ⭐ {pontos}
        </span>
        <span style="background-color: #F8FAFC; color: #334155; border: 1px solid #CBD5E1;
                     padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">
            📌 {classificacao}
        </span>
    </div>
    """)

def render_executive_description(text: str):
    """Renderiza a descrição executiva padronizada no nível 2 do módulo."""
    render_html(f"""
    <div style="background-color: #F8FAFC; border-left: 4px solid #004225; padding: 10px 16px; border-radius: 0 8px 8px 0; margin-bottom: 18px;">
        <p style="color: #334155; font-size: 13.5px; line-height: 1.5; margin: 0; font-style: italic;">
            "{text}"
        </p>
    </div>
    """)

def render_kpis(kpis_list: list):
    """Renderiza cards de KPI padronizados com ícones e cores institucionais."""
    cols = st.columns(len(kpis_list))
    for i, item in enumerate(kpis_list):
        label = item.get("label", "")
        valor = item.get("valor", "")
        meta = item.get("meta", "")
        atingido = item.get("atingido", None)
        info = item.get("info", "")
        delta_html = item.get("delta", "")

        if atingido is not None:
            if bool(atingido):
                val_color = "#059669"
                status_badge = '<span style="background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; font-size: 12px; font-weight: 900; padding: 2px 8px; border-radius: 6px;">✓</span>'
                border_color = "#A7F3D0"
            else:
                val_color = "#DC2626"
                status_badge = '<span style="background-color: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; font-size: 12px; font-weight: 900; padding: 2px 8px; border-radius: 6px;">✕</span>'
                border_color = "#FECACA"
        else:
            val_color = "#0F172A"
            status_badge = ""
            border_color = "#E2E8F0"

        delta_row = f'<div style="margin-top: 3px;">{delta_html}</div>' if delta_html else ""

        with cols[i]:
            render_html(f"""
            <div style="background-color: #FFFFFF; border: 1.5px solid {border_color}; border-radius: 12px;
                        padding: 16px 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); min-height: 118px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
                        <span style="font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">
                            {label}
                        </span>
                        {status_badge}
                    </div>
                    <div style="font-size: 24px; font-weight: 800; color: {val_color}; line-height: 1.1;">
                        {valor}
                    </div>
                    {delta_row}
                </div>
                <div style="font-size: 12px; color: #64748B; font-weight: 600; margin-top: 6px; border-top: 1px dashed #F1F5F9; padding-top: 4px;">
                    {f"🎯 <b>Meta:</b> {meta}" if meta else info}
                </div>
            </div>
            """)
    render_html("<div style='margin-bottom: 14px;'></div>")

def apply_chart_theme(fig, y_format=None, target_line=None, target_label="Meta IAF", target_color="#DC2626", line_width=2):
    """Padroniza gráficos Plotly com identidade institucional O Boticário e formato BR."""
    fig.update_layout(
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#0F172A"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis=dict(
            title="",
            tickfont=dict(size=12, color="#1E293B", family="Inter"),
            gridcolor="#F8FAFC",
            linecolor="#E2E8F0",
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#475569", family="Inter"),
            gridcolor="#F1F5F9",
            linecolor="#E2E8F0",
            tickformat=y_format if y_format else None,
        ),
        separators=",.",
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=12, color="#0F172A", family="Inter"),
        cliponaxis=False,
    )
    
    if target_line is not None:
        if y_format and "%" in y_format:
            annotation_val = fmt_pct(target_line, 2)
        else:
            annotation_val = str(target_line)
            
        fig.add_hline(
            y=target_line,
            line_dash="dash",
            line_color=target_color,
            line_width=line_width,
            annotation_text=f" {target_label}: {annotation_val}",
            annotation_position="top right",
            annotation_font=dict(size=11, color=target_color, family="Inter"),
        )
    return fig

def render_iaf_expander(titulo: str, formula: str, metas: str, conduta_permitido: str, conduta_proibido: str, expurgos: str = ""):
    """Renderiza a documentação técnica oficial e código de conduta no expander inferior (Nível 7)."""
    with st.expander(f"📚 Regras Oficiais, Metas por Clube e Código de Conduta (IAF 2026) — {titulo}", expanded=False):
        render_html(f"""
        <div style="font-size: 13.5px; line-height: 1.6; color: #1E293B; font-family: Inter, sans-serif;">
            
            <!-- Block 1: Fórmula + Metas -->
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <h5 style="color: #004225; font-weight: 700; margin-top: 0; margin-bottom: 8px;">📐 Fórmula de Cálculo Oficial</h5>
                <code style="background-color: #FFFFFF; color: #0F172A; padding: 6px 10px; border-radius: 4px; font-size: 13px; display: block; margin-bottom: 16px; border: 1px solid #CBD5E1;">{formula}</code>
                
                <h5 style="color: #004225; font-weight: 700; margin-bottom: 8px;">🎯 Sarrafos e Metas Oficiais por Clube (IAF 2026)</h5>
                <div style="color: #334155;">
                    {metas}
                </div>
            </div>
            
            <!-- Block 2: Práticas (Grid) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                <div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 16px; border-radius: 8px;">
                    <h6 style="color: #065F46; font-weight: 700; margin-top: 0; margin-bottom: 8px;">✅ Práticas Permitidas e Recomendadas</h6>
                    <span style="font-size: 13px; color: #065F46;">{conduta_permitido}</span>
                </div>
                <div style="background-color: #FEF2F2; border: 1px solid #FECACA; padding: 16px; border-radius: 8px;">
                    <h6 style="color: #991B1B; font-weight: 700; margin-top: 0; margin-bottom: 8px;">⛔ Condutas Proibidas (Risco de Desclassificação)</h6>
                    <span style="font-size: 13px; color: #991B1B;">{conduta_proibido}</span>
                </div>
            </div>
            
            <!-- Block 3: Expurgos -->
            {f'''
            <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; padding: 16px; border-radius: 8px;">
                <h6 style="color: #92400E; font-weight: 700; margin-top: 0; margin-bottom: 8px;">⚖️ Regras de Expurgo e Prazos (CSF)</h6>
                <span style="font-size: 13px; color: #92400E;">{expurgos}</span>
            </div>
            ''' if expurgos else ''}
        </div>
        """)


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 1: NPS (LOJA + OMNI)
# ═══════════════════════════════════════════════════════════════════

def render_tab_nps(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>1. NPS (Loja + Omni)</h2>")
    render_header_badges(pilar="Gestão Comercial", pontos="35 Pontos", classificacao="Oficial")
    render_executive_description(
        "O NPS (Loja + Omni) avalia a lealdade do consumidor em toda a sua jornada de compra. "
        "Ele pertence ao pilar de Gestão Comercial e distribui 35 pontos na nota geral do IAF 2026."
    )

    cp_info = calculators.get_cp_summary(data_raw) if data_raw else {}
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    delta_nps = deltas_cp.get("nps_geral")
    delta_nps_html = format_delta(delta_nps, "pts") if delta_nps is not None else ""

    # 1. NPS Geral do CP
    nps_geral = cp_info.get("nps_geral")
    if pd.isna(nps_geral) or nps_geral is None:
        nps_geral = df["nps"].mean() if ("nps" in df.columns and pd.notna(df["nps"].mean())) else 93.28

    nps_pct = (nps_geral / 100.0) if nps_geral > 1.0 else nps_geral

    # 2. Variação vs. Ano Anterior
    nps_var_num = cp_info.get("nps_variacao_num")
    nps_var_str = cp_info.get("nps_variacao_str") or cp_info.get("nps_variacao")
    benchmark_desc = cp_info.get("benchmark_desc", "Benchmark histórico consolidado")

    if pd.notna(nps_var_num) and nps_var_num is not None:
        sign = "+" if nps_var_num > 0 else ""
        var_display = f"{sign}{nps_var_num:.2f} pts".replace('.', ',')
        var_atingido = bool(nps_var_num >= 0)
        var_info = "vs. Mesmo Período do Ano Anterior"
    elif nps_var_str and any(c.isdigit() for c in str(nps_var_str)):
        m = re.search(r"([+-]?\s*\d+[.,]?\d*)", str(nps_var_str))
        if m:
            v_val = float(m.group(1).replace(' ', '').replace(',', '.'))
            sign = "+" if v_val > 0 else ""
            var_display = f"{sign}{v_val:.2f} pts".replace('.', ',')
            var_atingido = bool(v_val >= 0)
        else:
            var_display = str(nps_var_str)
            var_atingido = None
        var_info = "vs. Ano Anterior"
    else:
        var_display = "Acompanhamento"
        var_atingido = None
        var_info = "Sem histórico anterior importado"

    # 3. Total de Registros / Avaliações
    total_registros = int(df["nps_registros"].sum()) if ("nps_registros" in df.columns and pd.notna(df["nps_registros"].sum())) else 0
    lojas_na_meta = len(df[df["nps"] >= 90.9]) if "nps" in df.columns else 0

    render_kpis([
        {
            "label": "NPS Geral do CP Korinthos",
            "valor": fmt_pct(nps_pct, 2),
            "meta": "≥ 90,90% (IAF 2026)",
            "atingido": bool(nps_pct >= 0.909),
            "delta": delta_nps_html,
        },
        {
            "label": "Variação vs. Ano Anterior",
            "valor": var_display,
            "info": var_info,
            "atingido": var_atingido,
        },
        {
            "label": "Pesquisas Respondidas",
            "valor": f"{total_registros:,}".replace(',', '.') if total_registros > 0 else "-",
            "info": f"{lojas_na_meta} de 9 Lojas na Meta (≥ 90,90%)",
            "atingido": bool(lojas_na_meta >= 5),
        }
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "nps" in dff.columns:
        dff_chart = dff.dropna(subset=["nps"]).sort_values("nps", ascending=False)
        dff_chart["nps_pct"] = dff_chart["nps"] / 100.0
        fig = px.bar(
            dff_chart, x="label", y="nps_pct", text_auto=".2%",
            title="NPS por Loja Física (Avaliação Consumidor)",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig, target_line=0.909, target_label="Meta IAF", y_format=".2%")
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs</h4>")
    dff_table = dff.sort_values("nps", ascending=False).copy()
    delta_nps_col = _delta_col_for_pdv(deltas_pdv, dff_table, "nps", fmt_type="pts")
    
    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "Registros": dff_table["nps_registros"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.'),
        "NPS Loja (%)": dff_table["nps"].apply(lambda x: f"{x:.2f}%".replace('.', ',') if pd.notna(x) else "-"),
    })
    if delta_nps_col is not None:
        dff_show["Δ Mês Ant."] = delta_nps_col.values
    dff_show["Gap p/ Meta (90,90%)"] = dff_table["nps"].apply(lambda x: f"{x - 90.9:+.2f} pts".replace('.', ',') if pd.notna(x) else "-")
    dff_show["Status"] = dff_table["nps"].apply(lambda x: "✅ Atingida" if pd.notna(x) and x >= 90.9 else "❌ Abaixo")

    def rule_nps(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 90.9 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {"NPS Loja (%)": rule_nps}), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Visão por Consultoras</h4>")
    render_html("""
    <div style="background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 12px 16px;">
        <p style="color: #475569; font-size: 13px; margin: 0;">
            ℹ️ <b>Métrica Consolidada em Nível de Loja:</b> As pesquisas de satisfação e encantamento (Medallia) são mensuradas em nível de unidade física (PDV). Para planos de ação individualizados, utilize o painel de atendimento e resolução de detratores na plataforma oficial.
        </p>
    </div>
    """)

    render_iaf_expander(
        titulo="NPS (Loja + Omni)",
        formula="% Promotores (notas 9 e 10) - % Detratores (notas 0 a 6). Respondentes Neutros (7 e 8) compõem a base total, mas não pontuam.",
        metas="• <b>Iris:</b> ≥ 89% (35 pts) | 88% (33 pts) | 87% (27 pts) | 86% (18 pts)<br>• <b>Demais Clubes (Âmbar, Musk, Sândalo, Patchouli):</b> ≥ 90% (35 pts) | 89% (33 pts) | 88% (27 pts) | 87% (18 pts).<br><i>*Resultados abaixo de 18 pontos zeram o indicador.</i>",
        conduta_permitido="Tratar detratores no Medallia em até 24h; manter cadastros de clientes 100% fidedignos e atualizados no PDV.",
        conduta_proibido="Enviesar avaliações, pedir notas 9/10 expressamente ao cliente, oferecer brindes/descontos em troca de avaliação positiva, ou funcionários responderem pesquisas.",
        expurgos="Expurgos via CSF aceitos apenas em casos de má-fé comprovada, erros sistêmicos de Clique & Retire e ocorrências de Venda Direta/Revendedoras. Reclamações de Troca não são expurgadas. Prazo final do ciclo de dezembro: 10 de janeiro."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 2: LOJA DIGITAL — TME E CONVERSÃO
# ═══════════════════════════════════════════════════════════════════

def render_tab_tme(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>2. Loja Digital — TME e Conversão</h2>")
    render_header_badges(pilar="Experiência Omni & Digital", pontos="35 Pontos", classificacao="Oficial")
    render_executive_description(
        "O indicador Loja Digital - TME (Tempo Médio de Espera) faz parte do pilar de Experiência Omni & Digital e distribui 35 pontos na nota geral do IAF 2026."
    )

    cp_info = calculators.get_cp_summary(data_raw) if data_raw else {}
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    delta_tme = deltas_cp.get("tme_medio")
    delta_tme_html = format_delta(delta_tme, "time", inverted=True) if delta_tme is not None else ""
    delta_conv = deltas_cp.get("conversao_digital")
    delta_conv_html = format_delta(delta_conv, "pct") if delta_conv is not None else ""

    tme_cp = cp_info.get("tme_medio")
    if not tme_cp or tme_cp == "00:00:00":
        avg_secs = df["tme_ajustado_segundos"].mean()
        tme_cp = calculators._seconds_to_time_str(int(avg_secs)) if pd.notna(avg_secs) else "00:00:00"

    conv_cp = cp_info.get("conversao_digital")
    if pd.isna(conv_cp):
        tot_convertidos = df["clientes_convertidos"].sum()
        tot_atendidos = df["clientes_atendidos"].sum()
        conv_cp = (tot_convertidos / tot_atendidos) if tot_atendidos > 0 else df["conversao_digital"].mean()

    tme_secs = calculators._time_str_to_seconds(tme_cp)
    render_kpis([
        {
            "label": "TME Médio Ajustado (CP)",
            "valor": str(tme_cp),
            "meta": "≤ 00:07:00",
            "atingido": bool(tme_secs <= 420 and tme_secs > 0) if tme_secs > 0 else None,
            "delta": delta_tme_html,
        },
        {
            "label": "Taxa de Conversão Digital (CP)",
            "valor": fmt_pct(conv_cp, 2),
            "meta": "> 10,00%",
            "atingido": bool(conv_cp >= 0.10) if pd.notna(conv_cp) else None,
            "delta": delta_conv_html,
        }
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    conv_col = "conversao_digital" if "conversao_digital" in dff.columns and dff["conversao_digital"].notna().any() else "conversao_acao_fluxo"
    if conv_col in dff.columns:
        dff_chart = dff.sort_values(conv_col, ascending=False)
        fig = px.bar(
            dff_chart, x="label", y=conv_col, text_auto=".2%",
            title="Taxa de Conversão da Loja Digital por Loja",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig, y_format=".2%", target_line=0.10, target_label="Meta Interna (10,00%)")
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs</h4>")
    dff_table = dff.copy()
    dff_table = dff_table.sort_values(conv_col, ascending=False)
    delta_tme_col = _delta_col_for_pdv(deltas_pdv, dff_table, "tme_ajustado_segundos", fmt_type="time", inverted=True)
    delta_conv_col = _delta_col_for_pdv(deltas_pdv, dff_table, "conversao_digital", fmt_type="pct")

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "Encaminhados": dff_table["clientes_encaminhados"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.'),
        "Atendidos": dff_table["clientes_atendidos"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.'),
        "TME Ajustado": dff_table["tme_ajustado"].fillna("-"),
    })
    if delta_tme_col is not None:
        dff_show["Δ TME Ant."] = delta_tme_col.values
    dff_show["Convertidos"] = dff_table["clientes_convertidos"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.')
    dff_show["% Conversão Digital"] = dff_table[conv_col].apply(lambda x: fmt_pct(x, 2))
    if delta_conv_col is not None:
        dff_show["Δ Conv. Ant."] = delta_conv_col.values
    dff_show["TME Status"] = dff_table["tme_ajustado_segundos"].apply(lambda s: "✅ No Prazo" if pd.notna(s) and s <= 420 else "❌ Excedido")

    def rule_tme(val):
        if not isinstance(val, str) or val in ["-", "", "nan", "None"]: return ''
        secs = calculators._time_str_to_seconds(val)
        return 'color: #DC2626; font-weight: 700;' if secs > 420 else 'color: #059669; font-weight: 700;'

    def rule_conv(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 10.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {"TME Ajustado": rule_tme, "% Conversão Digital": rule_conv}), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Resultados por Consultora (Agrupadas por Loja)</h4>")
    cdf = calculators.get_consultant_data_for_tab(data_raw, "loja_digital") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty:
        req_cols = ["Loja", "CONSULTOR(A)" if "CONSULTOR(A)" in cdf.columns else "Consultor", "TME AJUSTADO", "% CONVERSÃO", "CLIENTES ATENDIDOS"]
        avail = [c for c in req_cols if c in cdf.columns]
        c_show = cdf[avail].copy()
        
        if "% CONVERSÃO" in c_show.columns:
            c_show["% CONVERSÃO"] = c_show["% CONVERSÃO"].apply(lambda x: fmt_pct(x, 2))
        
        st.dataframe(style_table(c_show, {"TME AJUSTADO": rule_tme}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma consultora encontrada para este módulo com os filtros atuais.")

    render_iaf_expander(
        titulo="Loja Digital — TME e Conversão",
        formula="TME = ∑(Hr. Primeiro Atendimento - Hr. Encaminhamento Ajustado) / Total Clientes Atendidos. Unificado em 2026 para Ativo + Receptivo.",
        metas="• <b>Habilitador Obrigatório:</b> Taxa de Atendimento na Loja Digital ≥ 95% (abaixo de 95% zera o indicador).<br>• <b>Iris, Âmbar, Musk e Sândalo:</b> ≤ 00:07:00 (35 pts) | 00:10:00 (33 pts) | 00:15:00 (26 pts) | 00:18:00 (17 pts).<br>• <b>Patchouli:</b> ≤ 00:12:00 (35 pts) | 00:14:00 (33 pts) | 00:20:00 (26 pts) | 00:25:00 (17 pts).",
        conduta_permitido="Manter consultoras escaladas atentas aos alertas do WhatsApp/Mobshop; prestar atendimento resolutivo e humanizado.",
        conduta_proibido="Enviar mensagens 'robóticas' apenas para pausar o cronômetro sem dar sequência real à conversa; gerar atendimentos fictícios ou direcionar clientes para WhatsApp pessoal."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 3: ID CLIENTE (CPF E BOLETOS < 2 MIN)
# ═══════════════════════════════════════════════════════════════════

def render_tab_idcliente(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>3. ID do Cliente (% Atendimento com CPF e Boletos < 2 min)</h2>")
    render_header_badges(pilar="Experiência Omni & Digital", pontos="25 Pontos", classificacao="Oficial")
    render_executive_description(
        "O indicador ID do Cliente faz parte do pilar de Experiência Omni & Digital (Pilar 2) e distribui 25 pontos na nota geral do IAF 2026.<br>"
        "<b>Sub-métrica Boletos < 2 min:</b> Percentual de vendas (boletos) em que o intervalo entre abertura do ID Cliente (CPF) e emissão do cupom fiscal foi inferior a 2 minutos."
    )

    cpf_cp = 1.0899
    b2m_cp = 0.2146
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    delta_cpf = deltas_cp.get("id_cliente_cpf")
    delta_cpf_html = format_delta(delta_cpf, "pct") if delta_cpf is not None else ""
    delta_2min = deltas_cp.get("id_cliente_2min")
    delta_2min_html = format_delta(delta_2min, "pct", inverted=True) if delta_2min is not None else ""

    if data_raw:
        cp_info = calculators.get_cp_summary(data_raw)
        cpf_cp = cp_info.get("id_cliente_cpf", 1.0899)
        b2m_cp = cp_info.get("id_cliente_2min", 0.2146)

    render_kpis([
        {
            "label": "% Atendimentos com CPF (IAF 2026)",
            "valor": fmt_pct(cpf_cp, 2),
            "meta": "≥ 115,00%",
            "atingido": bool(cpf_cp >= 1.15),
            "delta": delta_cpf_html,
        },
        {
            "label": "% Boletos ID Cliente < 2 min",
            "valor": fmt_pct(b2m_cp, 2),
            "meta": "≤ 30,00%",
            "atingido": bool(b2m_cp <= 0.30),
            "delta": delta_2min_html,
        }
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "id_cliente_cpf" in dff.columns:
        dff_chart = dff.sort_values("id_cliente_cpf", ascending=False)
        fig = px.bar(
            dff_chart, x="label", y="id_cliente_cpf", text_auto=".2%",
            title="% Atendimentos com CPF por Loja (IAF 2026)",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig, y_format=".2%", target_line=1.15, target_label="Meta IAF (115,00%)")
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs</h4>")
    dff_table = dff.sort_values("id_cliente_cpf", ascending=False).copy()
    delta_cpf_col = _delta_col_for_pdv(deltas_pdv, dff_table, "id_cliente_cpf", fmt_type="pct")
    delta_2min_col = _delta_col_for_pdv(deltas_pdv, dff_table, "id_cliente_2min", fmt_type="pct", inverted=True)

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "% Atendimento CPF": dff_table["id_cliente_cpf"].apply(lambda x: fmt_pct(x, 2)),
    })
    if delta_cpf_col is not None:
        dff_show["Δ CPF Ant."] = delta_cpf_col.values
    dff_show["TMA CPF"] = dff_table["id_cliente_tma"].fillna("-") if "id_cliente_tma" in dff_table.columns else "-"
    dff_show["% Boletos < 2min"] = dff_table["id_cliente_2min"].apply(lambda x: fmt_pct(x, 2)) if "id_cliente_2min" in dff_table.columns else "-"
    if delta_2min_col is not None:
        dff_show["Δ <2min Ant."] = delta_2min_col.values
    dff_show["% Boletos Válidos IAF"] = dff_table["id_cliente_validos"].apply(lambda x: fmt_pct(x, 2)) if "id_cliente_validos" in dff_table.columns else "-"
    dff_show["Status CPF"] = dff_table["id_cliente_cpf"].apply(lambda x: "✅ Batida" if pd.notna(x) and x >= 1.15 else "❌ Abaixo")

    def rule_cpf(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 115.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_2min(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num <= 30.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {"% Atendimento CPF": rule_cpf, "% Boletos < 2min": rule_2min}), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Resultados por Consultora (Agrupadas por Loja)</h4>")
    cdf = calculators.get_consultant_data_for_tab(data_raw, "id_cliente") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty:
        col_cons = next((c for c in ["CONSULTOR", "Consultor", "CONSULTOR(A)", "Nome"] if c in cdf.columns), "CONSULTOR")
        req_cols = ["Loja", col_cons, "% Atendimentos com CPF (IAF 2026)", "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN", "TEMPO MÉDIO DE ATENDIMENTO (TMA CPF)", "TOTAL BOLETOS"]
        avail = [c for c in req_cols if c in cdf.columns]
        c_show = cdf[avail].copy()
        if col_cons in c_show.columns and col_cons != "Consultora":
            c_show = c_show.rename(columns={col_cons: "Consultora"})
        if "% Atendimentos com CPF (IAF 2026)" in c_show.columns:
            c_show["% Atendimentos com CPF (IAF 2026)"] = c_show["% Atendimentos com CPF (IAF 2026)"].apply(lambda x: fmt_pct(x, 2))
        if "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN" in c_show.columns:
            c_show["% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN"] = c_show["% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN"].apply(lambda x: fmt_pct(x, 2))
        
        st.dataframe(style_table(c_show, {"% Atendimentos com CPF (IAF 2026)": rule_cpf, "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN": rule_2min}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma consultora encontrada.")

    render_iaf_expander(
        titulo="ID Cliente (% Atendimento com CPF e Boletos < 2 min)",
        formula="% Atendimento ID = Total Atendimentos com CPF (com e sem compra) / Total Boletos Canal Loja.",
        metas="• <b>Faixas de Pontuação IAF (25 pts):</b> ≥ 115% (25 pts) | ≥ 111% (23 pts) | ≥ 109% (18 pts) | ≥ 107% (12 pts). Abaixo de 107% zera.<br>• <b>Regras de Contabilização:</b> Limite de até 2 atendimentos para o mesmo CPF no mesmo dia e até 4 atendimentos na mesma semana.",
        conduta_permitido="Identificar o cliente com CPF no início do atendimento, durante a sondagem de necessidades.",
        conduta_proibido="Utilizar CPF de colaboradores ou terceiros; abrir o aplicativo ID Cliente após a emissão do cupom fiscal; acumular atendimentos para lançamento retroativo em lote."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 4: DESAFIO FIDELIDADE (BEAUTYBOX)
# ═══════════════════════════════════════════════════════════════════

def render_tab_fidelidade(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>4. Desafio Fidelidade</h2>")
    render_header_badges(pilar="IAF LAB 2026", pontos="IAF LAB", classificacao="LAB (Inovação)")
    render_executive_description(
        "O indicador Penetração Desafios Fidelidade faz parte do pilar de inovação IAF LAB no ciclo de 2026. "
        "Mensura o percentual de vendas identificadas no programa de fidelidade em que o consumidor concluiu e cumpriu pelo menos um dos Desafios Transacionais do Beautybox."
    )

    fid_cp = 0.1712
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    delta_fid = deltas_cp.get("desafio_fidelidade")
    delta_fid_html = format_delta(delta_fid, "pct") if delta_fid is not None else ""

    if data_raw:
        cp_info = calculators.get_cp_summary(data_raw)
        fid_cp = cp_info.get("desafio_fidelidade", 0.1712)

    render_kpis([
        {
            "label": "Penetração Média Desafios Fidelidade (CP)",
            "valor": fmt_pct(fid_cp, 2),
            "meta": "20,00%",
            "atingido": bool(fid_cp >= 0.20),
            "delta": delta_fid_html,
        }
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "penetracao_desafio_fidelidade" in dff.columns:
        dff_chart = dff.sort_values("penetracao_desafio_fidelidade", ascending=False)
        fig = px.bar(
            dff_chart, x="label", y="penetracao_desafio_fidelidade", text_auto=".2%",
            title="Penetração de Desafios Concluídos por Loja",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig, y_format=".2%", target_line=0.20, target_label="Meta (20,00%)")
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs</h4>")
    dff_table = dff.sort_values("penetracao_desafio_fidelidade", ascending=False).copy()
    delta_fid_col = _delta_col_for_pdv(deltas_pdv, dff_table, "penetracao_desafio_fidelidade", fmt_type="pct")

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "Boletos com Desafio": dff_table["boletos_desafio_qtd"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.'),
        "Boletos Fidelidade": dff_table["boletos_fidelidade_qtd"].fillna(0).apply(lambda x: f"{int(x):,}").str.replace(',', '.'),
        "% Penetração Desafios": dff_table["penetracao_desafio_fidelidade"].apply(lambda x: fmt_pct(x, 2)),
    })
    if delta_fid_col is not None:
        dff_show["Δ Mês Ant."] = delta_fid_col.values
    dff_show["Gap p/ Meta (20,00%)"] = dff_table["penetracao_desafio_fidelidade"].apply(lambda x: f"{x - 0.20:+.2%}".replace('.', ',') if pd.notna(x) else "-")
    dff_show["Status"] = dff_table["penetracao_desafio_fidelidade"].apply(lambda x: "✅ Batida" if pd.notna(x) and x >= 0.20 else "❌ Abaixo")

    def rule_fidelidade(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 20.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {"% Penetração Desafios": rule_fidelidade}), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Resultados por Consultora</h4>")
    cdf = calculators.get_consultant_data_for_tab(data_raw, "fidelidade") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty:
        req_cols = ["Consultor", "% Penetração Desafio Fidelidade", "Qnt de boleto com desafios concluídos", "Qnt de boletos Fidelidade"]
        avail = [c for c in req_cols if c in cdf.columns]
        c_show = cdf[avail].copy()
        
        if "% Penetração Desafio Fidelidade" in c_show.columns:
            c_show["% Penetração Desafio Fidelidade"] = c_show["% Penetração Desafio Fidelidade"].apply(lambda x: fmt_pct(x, 2))
            
        st.dataframe(style_table(c_show, {"% Penetração Desafio Fidelidade": rule_fidelidade}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma consultora encontrada.")

    render_iaf_expander(
        titulo="Desafio Fidelidade (Beautybox)",
        formula="% Penetração Desafios = Boletos com ≥ 1 Desafio Concluído / Total Boletos Fidelidade.",
        metas="• <b>Faseamento 1ª Rodada:</b> Jan: 7,10% | Fev: 10,90% | Mar: 14,40% | Abr: 16,20% | Mai: 18,90% | Jun: 20,00%.<br>• <b>Faseamento 2ª Rodada:</b> Jul: 19,20% | Ago: 19,40% | Set: 19,70% | Out: 19,90% | Nov: 19,90% | Dez: 20,00%.",
        conduta_permitido="Apresentar as vantagens dos desafios gamificados no Beautybox e estimular o resgate/cumprimento das missões.",
        conduta_proibido="Registrar desafios em nome de terceiros ou realizar inclusão forçada de produtos na sacola sem autorização prévia expressa do consumidor."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 5: SKIN + CATEGORIAS (CUIDADOS FACIAIS, PERFUMARIA E MIX)
# ═══════════════════════════════════════════════════════════════════

def render_tab_skin(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>5. Skin + Categorias (Cuidados Faciais, Perfumaria e Mix)</h2>")
    render_header_badges(pilar="Gestão Comercial & Categorias", pontos="25 Pontos IAF + Mix Comercial", classificacao="Oficial & Estratégico")
    render_executive_description(
        "Painel integrado de gestão de categorias da franquia Korinthos Cosméticos: acompanhamento do indicador oficial de Skin (Cuidados Faciais + Botik - IAF 2026), "
        "monitoramento estratégico da categoria de Perfumaria e distribuição do mix de faturamento por unidade."
    )

    cp_info = calculators.get_cp_summary(data_raw) if data_raw else {}
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 1: CUIDADOS FACIAIS & BOTIK (SKIN LOJAS — IAF 2026)
    # ─────────────────────────────────────────────────────────────
    render_html("<h3 style='color: #004225; font-weight: 800; border-bottom: 2px solid #E2E8F0; padding-bottom: 6px; margin-top: 20px;'>🌿 1. Cuidados Faciais & Botik (Meta Oficial IAF 2026)</h3>")
    render_html("<p style='color: #475569; font-size: 13px; margin-bottom: 12px;'>Mede o Share (%) de Receita GMV proveniente da marca Botik e da categoria de Cuidados Faciais dentro do canal Loja (Meta Regional SP: ≥ 2,10%).</p>")

    delta_skin = deltas_cp.get("skin_share")
    delta_skin_html = format_delta(delta_skin, "pct") if delta_skin is not None else ""

    skin_cp = cp_info.get("skin_share")
    if pd.isna(skin_cp):
        skin_cp = dff["cuidados_faciais"].mean()

    rec_skin_cp = cp_info.get("receita_skin_cp")
    if pd.isna(rec_skin_cp) or rec_skin_cp == 0:
        rec_skin_cp = dff["receita_skin"].sum()

    lojas_na_meta_skin = len(dff[dff["cuidados_faciais"] >= 0.021]) if "cuidados_faciais" in dff.columns else 0

    render_kpis([
        {"label": "Receita Total Cuidados Faciais (CP)", "valor": fmt_brl(rec_skin_cp), "meta": "Botik + Cuidados Faciais"},
        {
            "label": "Representatividade Média Skin do CP",
            "valor": fmt_pct(skin_cp, 2),
            "meta": "≥ 2,10% (Regional SP)",
            "atingido": bool(skin_cp >= 0.021) if pd.notna(skin_cp) else None,
            "delta": delta_skin_html,
        },
        {
            "label": "Lojas na Meta Regional SP",
            "valor": f"{lojas_na_meta_skin} de 9 Lojas",
            "meta": "≥ 2,10%",
            "atingido": bool(lojas_na_meta_skin >= 5),
        }
    ])

    if "cuidados_faciais" in dff.columns and dff["cuidados_faciais"].notna().any():
        dff_chart = dff.sort_values("cuidados_faciais", ascending=False)
        fig = px.bar(
            dff_chart, x="label", y="cuidados_faciais", text_auto=".2%",
            title="Representatividade Skin (Cuidados Faciais + Botik) por Loja",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig, y_format=".2%", target_line=0.021, target_label="Meta SP (2,10%)", target_color="#D97706", line_width=2.5)
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs — Cuidados Faciais</h4>")
    dff_table = dff.sort_values("cuidados_faciais", ascending=False).copy()
    delta_skin_col = _delta_col_for_pdv(deltas_pdv, dff_table, "cuidados_faciais", fmt_type="pct")

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "Receita Cuidados Faciais (R$)": dff_table["receita_skin"].apply(fmt_brl),
        "% Share Skin": dff_table["cuidados_faciais"].apply(lambda x: fmt_pct(x, 2)),
    })
    if delta_skin_col is not None:
        dff_show["Δ Mês Ant."] = delta_skin_col.values
    dff_show["Gap p/ Meta (2,10%)"] = dff_table["cuidados_faciais"].apply(lambda x: f"{x - 0.021:+.2%}".replace('.', ',') if pd.notna(x) else "-")
    dff_show["Status"] = dff_table["cuidados_faciais"].apply(lambda x: "✅ Batida" if pd.notna(x) and x >= 0.021 else "❌ Abaixo")

    def rule_skin(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 2.10 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {"% Share Skin": rule_skin}), use_container_width=True, hide_index=True)

    with st.expander("👩‍💼 Resultados por Consultora (Cuidados Faciais + Botik)", expanded=False):
        cdf = calculators.get_consultant_data_for_tab(data_raw, "cuidados_faciais") if data_raw else pd.DataFrame()
        cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
        if not cdf.empty:
            col_cons = next((c for c in ["Consultor", "CONSULTOR", "CONSULTOR(A)", "Nome"] if c in cdf.columns), None)
            req_cols = ["Loja"]
            if col_cons:
                req_cols.append(col_cons)
            req_cols.extend(["(%) RECEITA", "RECEITA (R$)"])
            avail = [c for c in req_cols if c in cdf.columns]
            c_show = cdf[avail].copy()
            if col_cons and col_cons in c_show.columns and col_cons != "Consultora":
                c_show = c_show.rename(columns={col_cons: "Consultora"})
            if "(%) RECEITA" in c_show.columns:
                c_show["(%) RECEITA"] = c_show["(%) RECEITA"].apply(lambda x: fmt_pct(x, 2))
            if "RECEITA (R$)" in c_show.columns:
                c_show["RECEITA (R$)"] = c_show["RECEITA (R$)"].apply(fmt_brl)
            st.dataframe(style_table(c_show, {"(%) RECEITA": rule_skin}), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma consultora encontrada.")

    render_iaf_expander(
        titulo="Skin Lojas (Cuidados Faciais + Botik)",
        formula="Share Skin = (GMV Cuidados Faciais Total + GMV Demais Categorias Botik) / GMV Total Canal Loja.",
        metas="• <b>Metas Regional SP (25 pts):</b> ≥ 2,10% (25 pts) | 1,90% (23 pts) | 1,60% (18 pts) | 1,40% (12 pts).",
        conduta_permitido="Oferecer experimentação, diagnóstico facial e demonstrar rotinas completas de skincare aos consumidores.",
        conduta_proibido="Faturar itens sem consentimento do cliente ou classificar produtos de outras categorias indevidamente."
    )

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 2: PERFUMARIA — RECEITA E PARTICIPAÇÃO (%)
    # ─────────────────────────────────────────────────────────────
    render_html("<h3 style='color: #004225; font-weight: 800; border-bottom: 2px solid #E2E8F0; padding-bottom: 6px; margin-top: 36px;'>💐 2. Perfumaria — Receita e Participação</h3>")
    render_html("<p style='color: #475569; font-size: 13px; margin-bottom: 12px;'>Acompanhamento da principal categoria da rede. A meta de referência operacional é manter a participação de Perfumaria em <b>≥ 50,00%</b> da receita do PDV.</p>")

    rec_perf_cp = cp_info.get("receita_perfumaria_cp")
    if pd.isna(rec_perf_cp) or rec_perf_cp is None:
        rec_perf_cp = dff["receita_perfumaria"].sum() if "receita_perfumaria" in dff.columns else np.nan

    part_perf_cp = cp_info.get("participacao_perfumaria_cp")
    if pd.isna(part_perf_cp) or part_perf_cp is None:
        tot_rec_cat = dff["receita_total_categorias"].sum() if "receita_total_categorias" in dff.columns else dff["receita"].sum()
        part_perf_cp = (rec_perf_cp / tot_rec_cat) if (pd.notna(rec_perf_cp) and tot_rec_cat > 0) else np.nan

    delta_perf_rec = deltas_cp.get("receita_perfumaria_cp")
    delta_perf_rec_html = format_delta(delta_perf_rec, "brl") if delta_perf_rec is not None else ""
    delta_perf_part = deltas_cp.get("participacao_perfumaria_cp")
    delta_perf_part_html = format_delta(delta_perf_part, "pct") if delta_perf_part is not None else ""

    lojas_meta_perf = len(dff[dff["participacao_perfumaria"] >= 0.50]) if "participacao_perfumaria" in dff.columns else 0

    render_kpis([
        {
            "label": "Receita Total Perfumaria (CP)",
            "valor": fmt_brl(rec_perf_cp),
            "meta": "Core Business",
            "delta": delta_perf_rec_html,
        },
        {
            "label": "Participação Perfumaria no CP",
            "valor": fmt_pct(part_perf_cp, 2),
            "meta": "≥ 50,00%",
            "atingido": bool(part_perf_cp >= 0.50) if pd.notna(part_perf_cp) else None,
            "delta": delta_perf_part_html,
        },
        {
            "label": "Lojas na Meta de Perfumaria",
            "valor": f"{lojas_meta_perf} de 9 Lojas",
            "meta": "≥ 50,00%",
            "atingido": bool(lojas_meta_perf >= 5),
        }
    ])

    if "participacao_perfumaria" in dff.columns and dff["participacao_perfumaria"].notna().any():
        dff_perf_chart = dff.dropna(subset=["participacao_perfumaria"]).sort_values("participacao_perfumaria", ascending=False)
        fig_perf = px.bar(
            dff_perf_chart, x="label", y="participacao_perfumaria", text_auto=".2%",
            title="Participação da Categoria de Perfumaria por Loja",
            color_discrete_sequence=["#004225"]
        )
        fig_perf = apply_chart_theme(fig_perf, y_format=".2%", target_line=0.50, target_label="Meta (50,00%)", target_color="#DC2626", line_width=2.5)
        st.plotly_chart(fig_perf, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs — Perfumaria</h4>")
    if "participacao_perfumaria" in dff.columns:
        dff_perf_table = dff.sort_values("participacao_perfumaria", ascending=True).copy()
        delta_perf_col = _delta_col_for_pdv(deltas_pdv, dff_perf_table, "participacao_perfumaria", fmt_type="pct")

        dff_perf_show = pd.DataFrame({
            "PDV": dff_perf_table["pdv"],
            "Loja": dff_perf_table["label"],
            "Cidade": dff_perf_table["cidade"],
            "Receita Perfumaria (R$)": dff_perf_table["receita_perfumaria"].apply(fmt_brl),
            "Participação (%)": dff_perf_table["participacao_perfumaria"].apply(lambda x: fmt_pct(x, 2)),
        })
        if delta_perf_col is not None:
            dff_perf_show["Δ Mês Ant."] = delta_perf_col.values
        dff_perf_show["Gap p/ Meta (50,00%)"] = dff_perf_table["participacao_perfumaria"].apply(lambda x: f"{x - 0.50:+.2%}".replace('.', ',') if pd.notna(x) else "-")
        dff_perf_show["Status"] = dff_perf_table["participacao_perfumaria"].apply(lambda x: "✅ Atingida" if pd.notna(x) and x >= 0.50 else "❌ Abaixo")

        # Regra de destaque: valores abaixo de 50% em vermelho, conforme solicitação do usuário
        def rule_perf(val):
            if not isinstance(val, str): return ''
            try:
                num = float(val.replace('%', '').replace(',', '.'))
                return 'color: #DC2626; font-weight: 700;' if num < 50.0 else 'color: #004225; font-weight: 700;'
            except: return ''

        st.dataframe(style_table(dff_perf_show, {"Participação (%)": rule_perf}), use_container_width=True, hide_index=True)

        # Card de Total CP consolidado ao final da tabela (igual ao modelo visual do usuário)
        render_html(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px 18px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="font-weight: 800; color: #004225; font-size: 15px;">Total CP Korinthos (10063)</div>
            <div style="font-weight: 700; color: #0F172A; font-size: 14px;">Receita Perfumaria: <b>{fmt_brl(rec_perf_cp)}</b></div>
            <div style="font-weight: 800; font-size: 15px; color: {'#004225' if pd.notna(part_perf_cp) and part_perf_cp >= 0.50 else '#DC2626'};">
                Participação Geral CP: <b>{fmt_pct(part_perf_cp, 2)}</b>
            </div>
        </div>
        """)

    with st.expander("👩‍💼 Desempenho por Consultora em Perfumaria", expanded=False):
        cdf_p = calculators.get_consultant_data_for_tab(data_raw, "perfumaria") if data_raw else pd.DataFrame()
        cdf_p = filter_consultants(cdf_p, excluir_gerencia, busca_consultora)
        if not cdf_p.empty and "perfumaria_receita" in cdf_p.columns:
            cdf_p_sorted = cdf_p.sort_values("perfumaria_receita", ascending=False).copy()
            c_perf_show = pd.DataFrame({
                "Consultora": cdf_p_sorted["Consultor"],
                "Loja": cdf_p_sorted.get("Loja", "Rede CP"),
                "Receita Perfumaria (R$)": cdf_p_sorted["perfumaria_receita"].apply(fmt_brl),
                "Participação (%)": cdf_p_sorted["perfumaria_part"].apply(lambda x: fmt_pct(x, 2)),
                "Total Receita (R$)": cdf_p_sorted["total_receita"].apply(fmt_brl),
            })
            st.dataframe(style_table(c_perf_show, {"Participação (%)": rule_perf}), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de consultora de perfumaria disponível.")

    # ─────────────────────────────────────────────────────────────
    # SEÇÃO 3: DISTRIBUIÇÃO DA RECEITA POR CATEGORIA (MIX COMPLETO)
    # ─────────────────────────────────────────────────────────────
    render_html("<h3 style='color: #004225; font-weight: 800; border-bottom: 2px solid #E2E8F0; padding-bottom: 6px; margin-top: 36px;'>📊 3. Distribuição Geral da Receita por Categoria</h3>")
    render_html("<p style='color: #475569; font-size: 13px; margin-bottom: 14px;'>Composição percentual e financeira do faturamento entre as 6 categorias de produtos: <b>Perfumaria, Cuidados da Pele, Cabelos, Maquiagem, Gifts e Outros</b>.</p>")

    cat_cols_map = [
        ("PERFUMARIA", "receita_perfumaria", "participacao_perfumaria", "#004225"),
        ("OUTROS", "receita_outros", "participacao_outros", "#64748B"),
        ("CUIDADOS DA PELE", "receita_cuidados_pele", "participacao_cuidados_pele", "#0DAB01"),
        ("MAQUIAGEM", "receita_maquiagem", "participacao_maquiagem", "#D97706"),
        ("CABELOS", "receita_cabelos", "participacao_cabelos", "#2563EB"),
        ("GIFTS", "receita_gifts", "participacao_gifts", "#8B5CF6"),
    ]

    # Gráficos de Composição Lado a Lado
    col_g1, col_g2 = st.columns([1, 1])

    # 1. Gráfico de Rosca (Donut) do CP
    with col_g1:
        cp_cat = cp_info.get("categorias_cp", {})
        donut_data = []
        if cp_cat:
            cat_keys = [
                ("Perfumaria", "perfumaria_receita", "#004225"),
                ("Outros", "outros_receita", "#64748B"),
                ("Cuidados da Pele", "cuidados_pele_receita", "#0DAB01"),
                ("Maquiagem", "maquiagem_receita", "#D97706"),
                ("Cabelos", "cabelos_receita", "#2563EB"),
                ("Gifts", "gifts_receita", "#8B5CF6"),
            ]
            for label_cat, key_cat, cor in cat_keys:
                val = _safe_numeric(cp_cat.get(key_cat))
                if pd.notna(val) and val > 0:
                    donut_data.append({"Categoria": label_cat, "Receita": val, "Cor": cor})
        elif "receita_perfumaria" in dff.columns:
            for label_cat, col_cat, _, cor in cat_cols_map:
                val = dff[col_cat].sum() if col_cat in dff.columns else 0
                if val > 0:
                    donut_data.append({"Categoria": label_cat.title(), "Receita": val, "Cor": cor})

        if donut_data:
            df_donut = pd.DataFrame(donut_data)
            fig_donut = px.pie(
                df_donut, names="Categoria", values="Receita", hole=0.55,
                title="Mix de Categorias — CP Korinthos (Total)",
                color="Categoria",
                color_discrete_map={d["Categoria"]: d["Cor"] for d in donut_data}
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
            fig_donut.update_layout(
                showlegend=False,
                margin=dict(l=10, r=10, t=40, b=10),
                annotations=[dict(text=f"Total CP<br><b>{fmt_brl(df_donut['Receita'].sum())}</b>", x=0.5, y=0.5, font_size=12, showarrow=False)]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # 2. Gráfico de Barras Empilhadas 100% por Loja
    with col_g2:
        stacked_rows = []
        for _, r in dff.iterrows():
            loja_label = r["label"]
            for label_cat, _, part_col, cor in cat_cols_map:
                pct = r.get(part_col, 0)
                if pd.notna(pct):
                    stacked_rows.append({
                        "Loja": loja_label,
                        "Categoria": label_cat.title(),
                        "Participação": float(pct),
                        "Cor": cor
                    })
        if stacked_rows:
            df_stacked = pd.DataFrame(stacked_rows)
            fig_stacked = px.bar(
                df_stacked, x="Loja", y="Participação", color="Categoria",
                title="Composição do Mix por Loja (100%)",
                color_discrete_map={d["Categoria"]: d["Cor"] for d in stacked_rows}
            )
            fig_stacked.update_layout(
                barmode='stack',
                yaxis=dict(tickformat='.0%', title=""),
                xaxis=dict(title=""),
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_stacked, use_container_width=True)

    # Tabela Matricial Completa de Categorias por Loja
    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 16px;'>Matriz de Participação por Categoria (% e Receita)</h4>")
    matriz_rows = []
    for _, r in dff.iterrows():
        matriz_rows.append({
            "Loja": r["label"],
            "Cidade": r["cidade"],
            "Total Receita": fmt_brl(r.get("receita_total_categorias", r.get("receita"))),
            "Perfumaria (%)": fmt_pct(r.get("participacao_perfumaria"), 2),
            "Cuidados da Pele (%)": fmt_pct(r.get("participacao_cuidados_pele"), 2),
            "Cabelos (%)": fmt_pct(r.get("participacao_cabelos"), 2),
            "Maquiagem (%)": fmt_pct(r.get("participacao_maquiagem"), 2),
            "Gifts (%)": fmt_pct(r.get("participacao_gifts"), 2),
            "Outros (%)": fmt_pct(r.get("participacao_outros"), 2),
        })

    # Adicionar linha de Total CP
    if cp_info.get("categorias_cp"):
        cp_c = cp_info["categorias_cp"]
        matriz_rows.append({
            "Loja": "★ TOTAL CP KORINTHOS",
            "Cidade": "Franquia",
            "Total Receita": fmt_brl(cp_c.get("total_receita")),
            "Perfumaria (%)": fmt_pct(cp_c.get("perfumaria_part"), 2),
            "Cuidados da Pele (%)": fmt_pct(cp_c.get("cuidados_pele_part"), 2),
            "Cabelos (%)": fmt_pct(cp_c.get("cabelos_part"), 2),
            "Maquiagem (%)": fmt_pct(cp_c.get("maquiagem_part"), 2),
            "Gifts (%)": fmt_pct(cp_c.get("gifts_part"), 2),
            "Outros (%)": fmt_pct(cp_c.get("outros_part"), 2),
        })

    df_matriz = pd.DataFrame(matriz_rows)
    st.dataframe(df_matriz, use_container_width=True, hide_index=True)

    with st.expander("👩‍💼 Mix Completo por Consultora (Todas as Categorias)", expanded=False):
        cdf_cat = calculators.get_consultant_data_for_tab(data_raw, "categorias") if data_raw else pd.DataFrame()
        cdf_cat = filter_consultants(cdf_cat, excluir_gerencia, busca_consultora)
        if not cdf_cat.empty:
            c_matriz = pd.DataFrame({
                "Consultora": cdf_cat["Consultor"],
                "Loja": cdf_cat.get("Loja", "Rede CP"),
                "Total Receita": cdf_cat["total_receita"].apply(fmt_brl),
                "Perfumaria (%)": cdf_cat["perfumaria_part"].apply(lambda x: fmt_pct(x, 2)),
                "Cuidados da Pele (%)": cdf_cat["cuidados_pele_part"].apply(lambda x: fmt_pct(x, 2)),
                "Cabelos (%)": cdf_cat["cabelos_part"].apply(lambda x: fmt_pct(x, 2)),
                "Maquiagem (%)": cdf_cat["maquiagem_part"].apply(lambda x: fmt_pct(x, 2)),
                "Gifts (%)": cdf_cat["gifts_part"].apply(lambda x: fmt_pct(x, 2)),
                "Outros (%)": cdf_cat["outros_part"].apply(lambda x: fmt_pct(x, 2)),
            })
            st.dataframe(c_matriz, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de consultoras disponível para distribuição de categorias.")

render_tab_skin_e_categorias = render_tab_skin


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 6: INDICADORES GERAIS DE VAREJO
# ═══════════════════════════════════════════════════════════════════

def render_tab_indicadores(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>6. Indicadores Gerais de Varejo</h2>")
    render_header_badges(pilar="Produtividade, Fidelização & Alavancas", pontos="Alavancas Comerciais", classificacao="Operacional & LAB")
    render_executive_description(
        "Consolidação dos indicadores operacionais e alavancas promocionais que rentabilizam o fluxo em loja, "
        "impulsionam a produtividade da equipe e aumentam a frequência de compra."
    )
    render_html("<p style='color: #475569; font-size: 13px; margin-bottom: 12px;'><b>Metas:</b> Itens/Boleto: 2,5 | Bol. Turbinado: 31% | Bol. Promocional: 33% | Resgate Fidelidade: 52% | Ação Fluxo: 28%</p>")

    cp_info = calculators.get_cp_summary(data_raw) if data_raw else {}
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    
    tm_cp = cp_info.get("ticket_medio")
    if pd.isna(tm_cp):
        tot_rec = df["receita"].sum()
        tot_bol = df["volume_boletos"].sum()
        tm_cp = (tot_rec / tot_bol) if tot_bol > 0 else df["ticket_medio"].mean()
        
    ipb_cp = cp_info.get("itens_boleto")
    if pd.isna(ipb_cp): ipb_cp = df["itens_boleto"].mean()
    
    bt_cp = cp_info.get("boleto_turbinado")
    if pd.isna(bt_cp): bt_cp = df["boletos_turbinados"].mean()
    
    bp_cp = cp_info.get("boleto_promocional")
    if pd.isna(bp_cp): bp_cp = df["boletos_promocionais"].mean()
    
    resg_cp = cp_info.get("resgate_fidelidade")
    if pd.isna(resg_cp): resg_cp = df["resgate_fidelidade"].mean()
    
    fluxo_cp = cp_info.get("conversao_fluxo")
    if pd.isna(fluxo_cp): fluxo_cp = df["conversao_acao_fluxo"].mean()

    delta_tm_html = format_delta(deltas_cp.get("ticket_medio"), "brl") if deltas_cp.get("ticket_medio") is not None else ""
    delta_ipb_html = format_delta(deltas_cp.get("itens_boleto"), "dec") if deltas_cp.get("itens_boleto") is not None else ""
    delta_bt_html = format_delta(deltas_cp.get("boleto_turbinado"), "pct") if deltas_cp.get("boleto_turbinado") is not None else ""
    delta_bp_html = format_delta(deltas_cp.get("boleto_promocional"), "pct") if deltas_cp.get("boleto_promocional") is not None else ""
    delta_resg_html = format_delta(deltas_cp.get("resgate_fidelidade"), "pct") if deltas_cp.get("resgate_fidelidade") is not None else ""
    delta_fluxo_html = format_delta(deltas_cp.get("conversao_fluxo"), "pct") if deltas_cp.get("conversao_fluxo") is not None else ""

    render_kpis([
        {"label": "Ticket Médio (CP)", "valor": fmt_brl(tm_cp), "meta": "Acompanhamento", "delta": delta_tm_html},
        {"label": "Itens / Boleto (IPB)", "valor": f"{ipb_cp:.2f}".replace('.', ',') if pd.notna(ipb_cp) else "-", "meta": "≥ 2,50", "atingido": bool(ipb_cp >= 2.5) if pd.notna(ipb_cp) else None, "delta": delta_ipb_html},
        {"label": "% Bol. Turbinado", "valor": fmt_pct(bt_cp, 2), "meta": "≥ 31,00%", "atingido": bool(bt_cp >= 0.31) if pd.notna(bt_cp) else None, "delta": delta_bt_html},
        {"label": "% Bol. Promocional", "valor": fmt_pct(bp_cp, 2), "meta": "≥ 33,00%", "atingido": bool(bp_cp >= 0.33) if pd.notna(bp_cp) else None, "delta": delta_bp_html},
        {"label": "% Resgate Fidelidade", "valor": fmt_pct(resg_cp, 2), "meta": "≥ 52,00%", "atingido": bool(resg_cp >= 0.52) if pd.notna(resg_cp) else None, "delta": delta_resg_html},
        {"label": "% Ação de Fluxo", "valor": fmt_pct(fluxo_cp, 2), "meta": "≥ 28,00%", "atingido": bool(fluxo_cp >= 0.28) if pd.notna(fluxo_cp) else None, "delta": delta_fluxo_html},
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "ticket_medio" in dff.columns:
        dff_chart = dff.sort_values("ticket_medio", ascending=False)
        fig = px.bar(
            dff_chart, x="label", y="ticket_medio", text_auto=".2f",
            title="Ticket Médio (R$) por Loja",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho dos 9 PDVs (Painel de Alavancas)</h4>")
    dff_table = dff.sort_values("ticket_medio", ascending=False).copy()
    delta_ipb_col = _delta_col_for_pdv(deltas_pdv, dff_table, "itens_boleto", fmt_type="dec")
    delta_bt_col = _delta_col_for_pdv(deltas_pdv, dff_table, "boletos_turbinados", fmt_type="pct")
    delta_resg_col = _delta_col_for_pdv(deltas_pdv, dff_table, "resgate_fidelidade", fmt_type="pct")

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Ticket Médio (R$)": dff_table["ticket_medio"].apply(fmt_brl),
        "Itens/Boleto": dff_table["itens_boleto"].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-"),
    })
    if delta_ipb_col is not None:
        dff_show["Δ IPB"] = delta_ipb_col.values
    dff_show["% Bol. Turbinado"] = dff_table["boletos_turbinados"].apply(lambda x: fmt_pct(x, 2))
    if delta_bt_col is not None:
        dff_show["Δ Turb."] = delta_bt_col.values
    dff_show["% Bol. Promocional"] = dff_table["boletos_promocionais"].apply(lambda x: fmt_pct(x, 2))
    dff_show["% Resgate Fidelidade"] = dff_table["resgate_fidelidade"].apply(lambda x: fmt_pct(x, 2))
    if delta_resg_col is not None:
        dff_show["Δ Resgate"] = delta_resg_col.values
    dff_show["% Ação de Fluxo"] = dff_table["conversao_acao_fluxo"].apply(lambda x: fmt_pct(x, 2))
    dff_show["% Boletos 1"] = dff_table["boletos_1"].apply(lambda x: fmt_pct(x, 2))
    dff_show["% Pen. Fidelidade"] = dff_table["penetracao_fidelidade"].apply(lambda x: fmt_pct(x, 2))
    dff_show["Serviços em Loja"] = dff_table.get("servicos_loja", pd.Series(np.zeros(len(dff_table)))).fillna(0).astype(int)

    def rule_ipb(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 2.50 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_bt(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 31.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_bp(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 33.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_resg(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 52.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_fluxo(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 28.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    st.dataframe(style_table(dff_show, {
        "Itens/Boleto": rule_ipb,
        "% Bol. Turbinado": rule_bt,
        "% Bol. Promocional": rule_bp,
        "% Resgate Fidelidade": rule_resg,
        "% Ação de Fluxo": rule_fluxo
    }), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Resultados por Consultora (Agrupadas por Loja)</h4>")
    cdf = calculators.get_consultant_data_for_tab(data_raw, "resumo") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty:
        req_cols = ["Loja", "Consultor", "Boleto Médio", "Itens por Boleto", "Penetração Boleto Turbinado", "Penetração Boleto Promocional", "Resgate Fidelidade"]
        avail = [c for c in req_cols if c in cdf.columns]
        c_show = cdf[avail].copy()
        
        if "Boleto Médio" in c_show.columns: c_show["Boleto Médio"] = c_show["Boleto Médio"].apply(fmt_brl)
        if "Itens por Boleto" in c_show.columns: c_show["Itens por Boleto"] = c_show["Itens por Boleto"].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
        if "Penetração Boleto Turbinado" in c_show.columns: c_show["Penetração Boleto Turbinado"] = c_show["Penetração Boleto Turbinado"].apply(lambda x: fmt_pct(x, 2))
        if "Penetração Boleto Promocional" in c_show.columns: c_show["Penetração Boleto Promocional"] = c_show["Penetração Boleto Promocional"].apply(lambda x: fmt_pct(x, 2))
        if "Resgate Fidelidade" in c_show.columns: c_show["Resgate Fidelidade"] = c_show["Resgate Fidelidade"].apply(lambda x: fmt_pct(x, 2))
            
        st.dataframe(style_table(c_show, {
            "Itens por Boleto": rule_ipb,
            "Penetração Boleto Turbinado": rule_bt,
            "Penetração Boleto Promocional": rule_bp,
            "Resgate Fidelidade": rule_resg
        }), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma consultora encontrada.")

    render_iaf_expander(
        titulo="Indicadores Gerais de Varejo",
        formula="• Resgate = Boletos com Resgate / Total Boletos Fidelidade.<br>• Boleto Turbinado = Boletos com BT / Boletos Elegíveis.<br>• Boleto Promocional = Boletos com BP / Boletos acima do Sarrafo.<br>• Conversão Fluxo = Boletos Convertidos / Total Brindes Resgatados (item pago adicional obrigatório).",
        metas="• <b>Resgate Fidelidade (25 pts):</b> ≥ 52,00% (25 pts) | 50,00% (23 pts) | 48,00% (18 pts) | 45,00% (12 pts).<br>• <b>Boleto Turbinado:</b> ≥ 31,00% | <b>Boleto Promocional:</b> ≥ 33,00% | <b>Ação de Fluxo:</b> ≥ 28,00%.",
        conduta_permitido="Estimular o acréscimo de itens complementares na sacola e resgate de pontos acumulados.",
        conduta_proibido="Fracionar compras em múltiplos cupons para inflar volume de boletos ou simular conversão de brindes."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 7: RECEITA DAS LOJAS (GMV E METAS PEF)
# ═══════════════════════════════════════════════════════════════════

def render_tab_receita(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>7. Receita das Lojas (GMV e Metas PEF)</h2>")
    render_header_badges(pilar="Gestão Comercial", pontos="100 Pontos", classificacao="Oficial")
    render_executive_description(
        "Acompanhamento da performance financeira das lojas físicas, atingimento do Planejamento Estratégico de Franqueados (PEF) "
        "e comparação de crescimento contra o período anterior."
    )
    render_html("<p style='color: #475569; font-size: 13px; margin-bottom: 12px;'><b>Métricas:</b> Receita GMV | % Meta PEF (Vermelho se < 100%) | Vs. Período Anterior</p>")

    cp_info = calculators.get_cp_summary(data_raw) if data_raw else {}
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    
    rec_cp = cp_info.get("receita_total_gmv")
    if pd.isna(rec_cp): rec_cp = df["receita"].sum()
    
    meta_pef_cp = cp_info.get("meta_pef_total")
    if pd.isna(meta_pef_cp): meta_pef_cp = df["meta_pef_total"].sum()
    
    pef_cp = cp_info.get("meta_pef_atingimento")
    if pd.isna(pef_cp):
        pef_cp = (rec_cp / meta_pef_cp) if (pd.notna(meta_pef_cp) and meta_pef_cp > 0) else df["meta_pef_realizado"].mean()

    delta_rec_html = format_delta(deltas_cp.get("receita_total_gmv"), "brl") if deltas_cp.get("receita_total_gmv") is not None else ""
    delta_pef_html = format_delta(deltas_cp.get("meta_pef_atingimento"), "pct") if deltas_cp.get("meta_pef_atingimento") is not None else ""

    render_kpis([
        {
            "label": "Receita Total da Rede (GMV)",
            "valor": fmt_brl(rec_cp),
            "meta": f"Meta PEF: {fmt_brl(meta_pef_cp)}" if pd.notna(meta_pef_cp) else "Acompanhamento",
            "delta": delta_rec_html,
        },
        {
            "label": "Atingimento Médio Meta PEF",
            "valor": fmt_pct(pef_cp, 2),
            "meta": "≥ 100,00%",
            "atingido": bool(pef_cp >= 1.00) if pd.notna(pef_cp) else None,
            "delta": delta_pef_html,
        },
    ])

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "receita" in dff.columns:
        dff_chart = dff.sort_values("receita", ascending=False)
        fig = px.bar(
            dff_chart, x="label", y="receita", text_auto=".2s",
            title="Receita Realizada GMV por Loja (R$)",
            color_discrete_sequence=["#004225"]
        )
        fig = apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 14px;'>Desempenho Financeiro dos 9 PDVs</h4>")
    dff_table = dff.sort_values("receita", ascending=False).copy()
    delta_rec_col = _delta_col_for_pdv(deltas_pdv, dff_table, "receita", fmt_type="brl")
    delta_pef_col = _delta_col_for_pdv(deltas_pdv, dff_table, "meta_pef_realizado", fmt_type="pct")

    dff_show = pd.DataFrame({
        "Loja": dff_table["label"],
        "Cidade": dff_table["cidade"],
        "Receita Loja (R$)": dff_table["receita_loja"].fillna(dff_table["receita"]).apply(fmt_brl),
        "Receita C&R (R$)": dff_table["receita_cr"].fillna(0).apply(fmt_brl),
        "Receita Total GMV (R$)": dff_table["receita"].apply(fmt_brl),
    })
    if delta_rec_col is not None:
        dff_show["Δ GMV Mês Ant."] = delta_rec_col.values
    dff_show["Meta PEF (R$)"] = dff_table["meta_pef_total"].fillna(dff_table["meta_pef_loja"]).apply(fmt_brl)
    dff_show["Gap Acordado (R$)"] = dff_table["gap_pef"].apply(fmt_brl)
    dff_show["% Meta PEF"] = dff_table["meta_pef_realizado"].apply(lambda x: fmt_pct(x, 2))
    if delta_pef_col is not None:
        dff_show["Δ PEF Mês Ant."] = delta_pef_col.values
    dff_show["Share na Rede"] = dff_table["representatividade"].apply(lambda x: fmt_pct(x, 2))
    dff_show["Vs. Ano Anterior"] = dff_table["receita_vs_anterior"].apply(lambda x: fmt_pct(x, 2))

    def rule_pef(val):
        if not isinstance(val, str): return ''
        try:
            num = float(val.replace('%', '').replace(',', '.'))
            return 'color: #059669; font-weight: 700;' if num >= 100.0 else 'color: #DC2626; font-weight: 700;'
        except: return ''

    def rule_growth(val):
        if not isinstance(val, str): return ''
        if '-' in val:
            return 'color: #DC2626; font-weight: 700;'
        if any(c.isdigit() for c in val) and val != '0,00%':
            return 'color: #059669; font-weight: 700;'
        return ''

    st.dataframe(style_table(dff_show, {
        "% Meta PEF": rule_pef,
        "Vs. Ano Anterior": rule_growth
    }), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #0F172A; font-weight: 700; margin-top: 20px;'>Vendas por Consultora (Agrupadas por Loja)</h4>")
    cdf = calculators.get_consultant_data_for_tab(data_raw, "receita") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty:
        req_cols = ["Loja", "Consultor", "Receita", "Vs. Período Anterior", "Quantidade de Boletos"]
        avail = [c for c in req_cols if c in cdf.columns]
        c_show = cdf[avail].copy()
        
        if "Receita" in c_show.columns: c_show["Receita"] = c_show["Receita"].apply(fmt_brl)
        if "Vs. Período Anterior" in c_show.columns: c_show["Vs. Período Anterior"] = c_show["Vs. Período Anterior"].apply(lambda x: fmt_pct(x, 2))
        
        st.dataframe(style_table(c_show, {"Vs. Período Anterior": rule_growth}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma consultora encontrada.")

    render_iaf_expander(
        titulo="Receita das Lojas (Metas PEF)",
        formula="Atingimento PEF = ∑ Receita Canal Loja Realizada / Meta Acordada PEF.",
        metas="• <b>Pontuação IAF (100 pts):</b> 100% da meta (100 pts) | 99% (90 pts) | 98% (80 pts) | 97% (70 pts) | 96% (60 pts) | 95% (50 pts) | < 95% (0 pts).",
        conduta_permitido="Executar planos de aceleração de vendas, promoções oficiais e engajamento ativo da carteira de clientes.",
        conduta_proibido="Faturamento indevido sem entrega física, antecipação artificial de cupons fiscais ou práticas comerciais desleais."
    )


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 8: RESUMO GERAL EXECUTIVO (SCORE GLOBAL)
# ═══════════════════════════════════════════════════════════════════

def render_tab_resumo(df: pd.DataFrame, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>8. Resumo Geral de Performance</h2>")
    render_header_badges(pilar="Consolidação Global", pontos="12 Metas", classificacao="Score Global")
    render_executive_description(
        "Síntese executiva do fechamento consolidando os pilares de Gestão Comercial, Experiência Omni & Digital, Fidelização e Alavancas de Produtividade."
    )

    dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
    if "score_global" not in dff.columns:
        dff["score_global"] = 0
    dff_sorted = dff.sort_values(by="score_global", ascending=False)

    render_html("<h4 style='color: #004225; font-weight: 800; margin-bottom: 12px;'>🏆 Pódios e Ranking Consolidado dos 9 PDVs</h4>")
    
    for row_idx in range(0, len(dff_sorted), 3):
        cols = st.columns(3)
        for col_idx in range(3):
            i = row_idx + col_idx
            if i < len(dff_sorted):
                r = dff_sorted.iloc[i]
                pos = i + 1
                if pos == 1:
                    badge_icon = "🥇 1º LUGAR"
                    card_bg = "#FEF9C3"
                    border_color = "#F59E0B"
                    title_color = "#92400E"
                elif pos == 2:
                    badge_icon = "🥈 2º LUGAR"
                    card_bg = "#F1F5F9"
                    border_color = "#94A3B8"
                    title_color = "#334155"
                elif pos == 3:
                    badge_icon = "🥉 3º LUGAR"
                    card_bg = "#FFF7ED"
                    border_color = "#F97316"
                    title_color = "#9A3412"
                else:
                    badge_icon = f"#{pos} POSIÇÃO"
                    card_bg = "#FFFFFF"
                    border_color = "#E2E8F0"
                    title_color = "#0F172A"

                with cols[col_idx]:
                    render_html(f"""
                    <div style="background-color: {card_bg}; border: 1.5px solid {border_color}; border-radius: 12px;
                                padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); text-align: center;">
                        <div style="font-size: 12px; font-weight: 800; color: {title_color}; letter-spacing: 0.5px;">
                            {badge_icon}
                        </div>
                        <h4 style="margin: 6px 0 4px 0; color: #0F172A; font-size: 18px; font-weight: 800;">
                            {r['label']}
                        </h4>
                        <div style="font-size: 12px; color: #64748B; margin-bottom: 6px;">
                            📍 {r['cidade']} ({r['local']})
                        </div>
                        <div style="font-size: 24px; font-weight: 800; color: #004225;">
                            {int(r['score_global'])} <span style="font-size: 14px; font-weight: 600; color: #475569;">/ 12 metas</span>
                        </div>
                    </div>
                    """)

    render_html("<h4 style='color: #004225; font-weight: 800; margin-top: 18px; margin-bottom: 8px;'>📊 Matriz de Diagnóstico Executivo (Scorecard das 12 Metas)</h4>")
    
    deltas_cp, deltas_pdv = _get_deltas(data_raw)
    delta_score_col = _delta_col_for_pdv(deltas_pdv, dff_sorted, "score_global", fmt_type="pts")

    scorecard_rows = []
    for idx, (_, r) in enumerate(dff_sorted.iterrows()):
        row_dict = {
            "Loja": r["label"],
            "Score": f"{int(r['score_global'])} pts",
        }
        if delta_score_col is not None and idx < len(delta_score_col):
            row_dict["Δ Score"] = delta_score_col.iloc[idx]
        row_dict.update({
            "PEF (≥100%)": "✅" if pd.notna(r.get("meta_pef_realizado")) and r["meta_pef_realizado"] >= 1.00 else "❌",
            "NPS (≥90.9%)": "✅" if pd.notna(r.get("nps")) and r["nps"] >= 90.9 else "❌",
            "TME (≤7min)": "✅" if pd.notna(r.get("tme_ajustado_segundos")) and r["tme_ajustado_segundos"] <= 420 else "❌",
            "Conv. Digital (≥10%)": "✅" if pd.notna(r.get("conversao_digital", r.get("conversao_acao_fluxo"))) and r.get("conversao_digital", r.get("conversao_acao_fluxo")) >= 0.10 else "❌",
            "CPF (≥115%)": "✅" if pd.notna(r.get("id_cliente_cpf")) and r["id_cliente_cpf"] >= 1.15 else "❌",
            "ID <2min (≤30%)": "✅" if pd.notna(r.get("id_cliente_2min")) and r["id_cliente_2min"] <= 0.30 else "❌",
            "Fidelidade (≥20%)": "✅" if pd.notna(r.get("penetracao_desafio_fidelidade")) and r["penetracao_desafio_fidelidade"] >= 0.20 else "❌",
            "Skin (≥2.1%)": "✅" if pd.notna(r.get("cuidados_faciais")) and r["cuidados_faciais"] >= 0.021 else "❌",
            "IPB (≥2.5)": "✅" if pd.notna(r.get("itens_boleto")) and r["itens_boleto"] >= 2.50 else "❌",
            "Turbinado (≥31%)": "✅" if pd.notna(r.get("boletos_turbinados")) and r["boletos_turbinados"] >= 0.31 else "❌",
            "Promocional (≥33%)": "✅" if pd.notna(r.get("boletos_promocionais")) and r["boletos_promocionais"] >= 0.33 else "❌",
            "Resgate (≥52%)": "✅" if pd.notna(r.get("resgate_fidelidade")) and r["resgate_fidelidade"] >= 0.52 else "❌",
        })
        scorecard_rows.append(row_dict)

    df_scorecard = pd.DataFrame(scorecard_rows)
    st.dataframe(style_table(df_scorecard), use_container_width=True, hide_index=True)

    render_html("<h4 style='color: #004225; font-weight: 800; margin-top: 22px; margin-bottom: 8px;'>🎯 Diagnóstico Estratégico & Planos de Ação Recomendados</h4>")
    
    diag = calculators.get_strategic_diagnostics(dff)
    col_top, col_bot = st.columns(2)

    with col_top:
        render_html("""
        <div style="background-color: #ECFDF5; border: 1.5px solid #A7F3D0; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <h5 style="color: #065F46; font-weight: 800; margin: 0 0 8px 0;">🌟 Top 3 Lojas de Alta Performance</h5>
        </div>
        """)
        for t in diag.get("top_3", []):
            destaques_str = " • ".join([d for d in t.get("destaques", []) if d])
            render_html(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #059669; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-weight: 800; color: #0F172A; font-size: 15px;">{t['loja']} ({t['cidade']}) — <span style="color: #059669;">{t['score']} Pontos</span></div>
                <div style="font-size: 12.5px; color: #334155; margin-top: 4px;"><b>Fortalezas:</b> {destaques_str if destaques_str else 'Excelente equilíbrio operacional.'}</div>
            </div>
            """)

    with col_bot:
        render_html("""
        <div style="background-color: #FEF2F2; border: 1.5px solid #FECACA; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <h5 style="color: #991B1B; font-weight: 800; margin: 0 0 8px 0;">⚠️ Bottom 3 Lojas com Oportunidades de Correção</h5>
        </div>
        """)
        for b in diag.get("bottom_3", []):
            gaps_str = " • ".join(b.get("gaps", []))
            planos_str = " ".join(b.get("plano_acao", []))
            render_html(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #DC2626; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-weight: 800; color: #0F172A; font-size: 15px;">{b['loja']} ({b['cidade']}) — <span style="color: #DC2626;">{b['score']} Pontos</span></div>
                <div style="font-size: 12.5px; color: #7F1D1D; margin-top: 3px;"><b>Gaps Críticos:</b> {gaps_str}</div>
                <div style="font-size: 12.5px; color: #1E293B; margin-top: 3px;"><b>Plano de Ação:</b> {planos_str}</div>
            </div>
            """)

    render_html("<h4 style='color: #004225; font-weight: 800; margin-top: 22px; margin-bottom: 8px;'>👩‍💼 Diagnóstico Estratégico de Consultoras</h4>")
    
    cdf = calculators.get_consultant_data_for_tab(data_raw, "resumo") if data_raw else pd.DataFrame()
    cdf = filter_consultants(cdf, excluir_gerencia, busca_consultora)
    
    if not cdf.empty and "Receita" in cdf.columns:
        cdf_sorted = cdf.sort_values(by="Receita", ascending=False)
        top5 = cdf_sorted.head(5)
        bot5 = cdf_sorted.tail(5)
        
        col_c_top, col_c_bot = st.columns(2)
        with col_c_top:
            render_html("""
            <div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;">
                <span style="font-weight: 800; color: #065F46; font-size: 14px;">🌟 Top 5 Consultoras Destaques (Receita)</span>
            </div>
            """)
            top5_show = top5[["Loja", "Consultor", "Receita", "Boleto Médio", "Itens por Boleto"]].copy()
            top5_show["Receita"] = top5_show["Receita"].apply(fmt_brl)
            top5_show["Boleto Médio"] = top5_show["Boleto Médio"].apply(fmt_brl)
            top5_show["Itens por Boleto"] = top5_show["Itens por Boleto"].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
            st.dataframe(style_table(top5_show), use_container_width=True, hide_index=True)
            
        with col_c_bot:
            render_html("""
            <div style="background-color: #FEF2F2; border: 1px solid #FECACA; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;">
                <span style="font-weight: 800; color: #991B1B; font-size: 14px;">⚠️ Bottom 5 Consultoras — Maiores Oportunidades (Receita)</span>
            </div>
            """)
            bot5_show = bot5[["Loja", "Consultor", "Receita", "Boleto Médio", "Itens por Boleto"]].copy()
            bot5_show["Receita"] = bot5_show["Receita"].apply(fmt_brl)
            bot5_show["Boleto Médio"] = bot5_show["Boleto Médio"].apply(fmt_brl)
            bot5_show["Itens por Boleto"] = bot5_show["Itens por Boleto"].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
            st.dataframe(style_table(bot5_show), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# MÓDULO 9: CONSULTA UNIVERSAL
# ═══════════════════════════════════════════════════════════════════

def render_tab_consulta_universal(df: pd.DataFrame, consultant_df: Optional[pd.DataFrame] = None, data_raw: Optional[Dict[str, Any]] = None, excluir_gerencia: bool = True, busca_consultora: str = ""):
    render_html("<h2 style='color: #004225; font-weight: 800; margin-bottom: 2px;'>9. Consulta Universal</h2>")
    render_header_badges(pilar="Análise Dinâmica", pontos="Lojas & Equipe", classificacao="Scorecard / Cards")
    render_executive_description(
        "Módulo de consulta universal e diagnóstico 360° para visualização completa de metas por loja e scorecards individuais de desempenho por consultora."
    )
    
    tab_loja, tab_consultora = st.tabs(["🏬 Consulta por Loja", "👩‍💼 Consulta por Consultora"])
    
    with tab_loja:
        st.markdown("### 🏬 Painel e Scorecard por Loja")
        dff = df[df["pdv"].isin(TARGET_PDVS)].copy()
        loja_list = dff["label"].tolist() if not dff.empty else []
        
        if loja_list:
            loja_sel = st.selectbox("Selecione a Loja:", options=loja_list, key="sel_loja_univ")
            if loja_sel:
                row = dff[dff["label"] == loja_sel].iloc[0]
                st.markdown(f"#### Resultados e Metas: **{loja_sel}** ({row.get('cidade', '')})")

                deltas_cp, deltas_pdv = _get_deltas(data_raw)
                pdv_code = row.get("pdv")
                d_row = {}
                if not deltas_pdv.empty and "pdv" in deltas_pdv.columns:
                    match_d = deltas_pdv[deltas_pdv["pdv"] == pdv_code]
                    if not match_d.empty:
                        d_row = match_d.iloc[0].to_dict()
                
                nps_v = row.get("nps", 0)
                tme_s = row.get("tme_ajustado_segundos", 999)
                conv_v = row.get("conversao_digital", row.get("conversao_acao_fluxo", 0))
                cpf_v = row.get("id_cliente_cpf", 0)
                b2m_v = row.get("id_cliente_2min", 999)
                fid_v = row.get("penetracao_desafio_fidelidade", 0)
                skin_v = row.get("cuidados_faciais", 0)
                ipb_v = row.get("itens_boleto", 0)
                bt_v = row.get("boletos_turbinados", 0)
                bp_v = row.get("boletos_promocionais", 0)
                resg_v = row.get("resgate_fidelidade", 0)
                pef_v = row.get("meta_pef_realizado", 0)

                render_kpis([
                    {"label": "NPS (Loja)", "valor": f"{nps_v:.1f}%".replace('.', ',') if pd.notna(nps_v) else "-", "meta": "≥ 90,90%", "atingido": bool(pd.notna(nps_v) and nps_v >= 90.9), "delta": format_delta(d_row.get("delta_nps"), "pts")},
                    {"label": "TME (Loja Digital)", "valor": str(row.get("tme_ajustado", "-")), "meta": "≤ 00:07:00", "atingido": bool(pd.notna(tme_s) and tme_s <= 420), "delta": format_delta(d_row.get("delta_tme_ajustado_segundos"), "time", inverted=True)},
                    {"label": "Conv. Digital", "valor": fmt_pct(conv_v, 2), "meta": "≥ 10,00%", "atingido": bool(pd.notna(conv_v) and conv_v >= 0.10), "delta": format_delta(d_row.get("delta_conversao_digital"), "pct")},
                    {"label": "% ID Cliente (CPF)", "valor": fmt_pct(cpf_v, 2), "meta": "≥ 115,00%", "atingido": bool(pd.notna(cpf_v) and cpf_v >= 1.15), "delta": format_delta(d_row.get("delta_id_cliente_cpf"), "pct")},
                    {"label": "% Boletos < 2 min", "valor": fmt_pct(b2m_v, 2), "meta": "≤ 30,00%", "atingido": bool(pd.notna(b2m_v) and b2m_v <= 0.30), "delta": format_delta(d_row.get("delta_id_cliente_2min"), "pct", inverted=True)},
                    {"label": "Desafio Fidelidade", "valor": fmt_pct(fid_v, 2), "meta": "≥ 20,00%", "atingido": bool(pd.notna(fid_v) and fid_v >= 0.20), "delta": format_delta(d_row.get("delta_penetracao_desafio_fidelidade"), "pct")},
                ])
                render_kpis([
                    {"label": "Share Skin (Botik)", "valor": fmt_pct(skin_v, 2), "meta": "≥ 2,10%", "atingido": bool(pd.notna(skin_v) and skin_v >= 0.021), "delta": format_delta(d_row.get("delta_cuidados_faciais"), "pct")},
                    {"label": "Itens por Boleto", "valor": f"{ipb_v:.2f}".replace('.', ',') if pd.notna(ipb_v) else "-", "meta": "≥ 2,50", "atingido": bool(pd.notna(ipb_v) and ipb_v >= 2.50), "delta": format_delta(d_row.get("delta_itens_boleto"), "dec")},
                    {"label": "% Boleto Turbinado", "valor": fmt_pct(bt_v, 2), "meta": "≥ 31,00%", "atingido": bool(pd.notna(bt_v) and bt_v >= 0.31), "delta": format_delta(d_row.get("delta_boletos_turbinados"), "pct")},
                    {"label": "% Boleto Promocional", "valor": fmt_pct(bp_v, 2), "meta": "≥ 33,00%", "atingido": bool(pd.notna(bp_v) and bp_v >= 0.33), "delta": format_delta(d_row.get("delta_boletos_promocionais"), "pct")},
                    {"label": "% Resgate Fidelidade", "valor": fmt_pct(resg_v, 2), "meta": "≥ 52,00%", "atingido": bool(pd.notna(resg_v) and resg_v >= 0.52), "delta": format_delta(d_row.get("delta_resgate_fidelidade"), "pct")},
                    {"label": "Atingimento PEF", "valor": fmt_pct(pef_v, 2), "meta": "≥ 100,00%", "atingido": bool(pd.notna(pef_v) and pef_v >= 1.00), "delta": format_delta(d_row.get("delta_meta_pef_realizado"), "pct")},
                ])
                
                # Consultoras da loja
                st.markdown(f"#### Equipe de Consultoras ({loja_sel})")
                cdf_res = calculators.get_consultant_data_for_tab(data_raw, "resumo") if data_raw else pd.DataFrame()
                cdf_res = filter_consultants(cdf_res, excluir_gerencia, busca_consultora)
                
                if not cdf_res.empty:
                    equipe = cdf_res[cdf_res["Loja"] == loja_sel]
                    if not equipe.empty:
                        equipe_show = equipe[["Consultor", "Receita", "Boleto Médio", "Itens por Boleto", "Penetração Boleto Turbinado", "Penetração Boleto Promocional", "Resgate Fidelidade"]].copy()
                        equipe_show["Receita"] = equipe_show["Receita"].apply(fmt_brl)
                        equipe_show["Boleto Médio"] = equipe_show["Boleto Médio"].apply(fmt_brl)
                        equipe_show["Itens por Boleto"] = equipe_show["Itens por Boleto"].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
                        equipe_show["Penetração Boleto Turbinado"] = equipe_show["Penetração Boleto Turbinado"].apply(lambda x: fmt_pct(x, 2))
                        equipe_show["Penetração Boleto Promocional"] = equipe_show["Penetração Boleto Promocional"].apply(lambda x: fmt_pct(x, 2))
                        equipe_show["Resgate Fidelidade"] = equipe_show["Resgate Fidelidade"].apply(lambda x: fmt_pct(x, 2))
                        
                        def rule_ipb(val):
                            if not isinstance(val, str): return ''
                            try:
                                num = float(val.replace(',', '.'))
                                return 'color: #059669; font-weight: 700;' if num >= 2.50 else 'color: #DC2626; font-weight: 700;'
                            except: return ''

                        def rule_bt(val):
                            if not isinstance(val, str): return ''
                            try:
                                num = float(val.replace('%', '').replace(',', '.'))
                                return 'color: #059669; font-weight: 700;' if num >= 31.0 else 'color: #DC2626; font-weight: 700;'
                            except: return ''

                        def rule_bp(val):
                            if not isinstance(val, str): return ''
                            try:
                                num = float(val.replace('%', '').replace(',', '.'))
                                return 'color: #059669; font-weight: 700;' if num >= 33.0 else 'color: #DC2626; font-weight: 700;'
                            except: return ''

                        def rule_resg(val):
                            if not isinstance(val, str): return ''
                            try:
                                num = float(val.replace('%', '').replace(',', '.'))
                                return 'color: #059669; font-weight: 700;' if num >= 52.0 else 'color: #DC2626; font-weight: 700;'
                            except: return ''

                        st.dataframe(style_table(equipe_show, {
                            "Itens por Boleto": rule_ipb,
                            "Penetração Boleto Turbinado": rule_bt,
                            "Penetração Boleto Promocional": rule_bp,
                            "Resgate Fidelidade": rule_resg
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhuma consultora encontrada para esta loja com os filtros atuais.")
                else:
                    st.info("Dados de consultoras não disponíveis.")
        else:
            st.info("Dados das lojas não disponíveis.")
            
    with tab_consultora:
        st.markdown("### 👩‍💼 Scorecard Individual por Consultora")
        cdf_res = calculators.get_consultant_data_for_tab(data_raw, "resumo") if data_raw else pd.DataFrame()
        cdf_res = filter_consultants(cdf_res, excluir_gerencia, busca_consultora)
        
        if not cdf_res.empty:
            cons_list = sorted(cdf_res["Consultor"].dropna().unique().tolist())
            if cons_list:
                cons_sel = st.selectbox("Selecione a Consultora:", options=cons_list, key="sel_cons_univ")
                if cons_sel:
                    cons_data = cdf_res[cdf_res["Consultor"] == cons_sel].iloc[0]
                    st.markdown(f"#### Scorecard de Metas: **{cons_sel}** — Unidade: **{cons_data.get('Loja', '')}**")
                    st.info(f"📍 Loja da Consultora: {cons_data.get('Loja', 'N/A')}")
                    
                    ld = calculators.get_consultant_data_for_tab(data_raw, "loja_digital") if data_raw else pd.DataFrame()
                    ld = filter_consultants(ld, excluir_gerencia, "")
                    ld_data = ld[ld["CONSULTOR(A)" if "CONSULTOR(A)" in ld.columns else "Consultor"] == cons_sel].iloc[0] if not ld.empty and cons_sel in ld["CONSULTOR(A)" if "CONSULTOR(A)" in ld.columns else "Consultor"].values else None
                    
                    id_c = calculators.get_consultant_data_for_tab(data_raw, "id_cliente") if data_raw else pd.DataFrame()
                    id_c = filter_consultants(id_c, excluir_gerencia, "")
                    id_col = "Consultor" if "Consultor" in id_c.columns else "CONSULTOR"
                    id_data = id_c[id_c[id_col] == cons_sel].iloc[0] if not id_c.empty and id_col in id_c.columns and cons_sel in id_c[id_col].values else None
                    
                    cf = calculators.get_consultant_data_for_tab(data_raw, "cuidados_faciais") if data_raw else pd.DataFrame()
                    cf = filter_consultants(cf, excluir_gerencia, "")
                    cf_col = "Consultor" if "Consultor" in cf.columns else "CONSULTOR"
                    cf_data = cf[cf[cf_col] == cons_sel].iloc[0] if not cf.empty and cf_col in cf.columns and cons_sel in cf[cf_col].values else None
                    
                    fid = calculators.get_consultant_data_for_tab(data_raw, "fidelidade") if data_raw else pd.DataFrame()
                    fid = filter_consultants(fid, excluir_gerencia, "")
                    fid_data = fid[fid["Consultor"] == cons_sel].iloc[0] if not fid.empty and "Consultor" in fid.columns and cons_sel in fid["Consultor"].values else None
                    
                    tme_val = ld_data["TME AJUSTADO"] if ld_data is not None and "TME AJUSTADO" in ld_data else "-"
                    tme_secs = calculators._time_str_to_seconds(tme_val) if tme_val != "-" else 999
                    conv_val = ld_data["% CONVERSÃO"] if ld_data is not None and "% CONVERSÃO" in ld_data else 0
                    cpf_val = id_data["% Atendimentos com CPF (IAF 2026)"] if id_data is not None and "% Atendimentos com CPF (IAF 2026)" in id_data else 0
                    id_2m_val = id_data["% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN"] if id_data is not None and "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN" in id_data else 0
                    skin_val = cf_data["(%) RECEITA"] if cf_data is not None and "(%) RECEITA" in cf_data else 0
                    fid_val = fid_data["% Penetração Desafio Fidelidade"] if fid_data is not None and "% Penetração Desafio Fidelidade" in fid_data else 0
                    
                    ipb_cons = cons_data.get("Itens por Boleto", 0)
                    bt_cons = cons_data.get("Penetração Boleto Turbinado", 0)
                    bp_cons = cons_data.get("Penetração Boleto Promocional", 0)
                    resg_cons = cons_data.get("Resgate Fidelidade", 0)

                    render_kpis([
                        {"label": "Receita Realizada", "valor": fmt_brl(cons_data.get("Receita", 0)), "meta": "Acompanhamento", "atingido": None},
                        {"label": "Ticket Médio", "valor": fmt_brl(cons_data.get("Boleto Médio", 0)), "meta": "Acompanhamento", "atingido": None},
                        {"label": "Itens por Boleto", "valor": f"{ipb_cons:.2f}".replace('.', ',') if pd.notna(ipb_cons) else "-", "meta": "≥ 2,50", "atingido": bool(pd.notna(ipb_cons) and ipb_cons >= 2.50)},
                        {"label": "% Bol. Turbinado", "valor": fmt_pct(bt_cons, 2), "meta": "≥ 31,00%", "atingido": bool(pd.notna(bt_cons) and bt_cons >= 0.31)},
                        {"label": "% Bol. Promocional", "valor": fmt_pct(bp_cons, 2), "meta": "≥ 33,00%", "atingido": bool(pd.notna(bp_cons) and bp_cons >= 0.33)},
                        {"label": "% Resgate Fidelidade", "valor": fmt_pct(resg_cons, 2), "meta": "≥ 52,00%", "atingido": bool(pd.notna(resg_cons) and resg_cons >= 0.52)},
                    ])
                    render_kpis([
                        {"label": "TME (Loja Digital)", "valor": str(tme_val), "meta": "≤ 00:07:00", "atingido": bool(tme_secs <= 420) if tme_val != "-" else None},
                        {"label": "Conv. Digital", "valor": fmt_pct(conv_val, 2), "meta": "≥ 10,00%", "atingido": bool(conv_val >= 0.10) if pd.notna(conv_val) else None},
                        {"label": "% ID Cliente (CPF)", "valor": fmt_pct(cpf_val, 2), "meta": "≥ 115,00%", "atingido": bool(cpf_val >= 1.15) if pd.notna(cpf_val) else None},
                        {"label": "% Boletos < 2 min", "valor": fmt_pct(id_2m_val, 2), "meta": "≤ 30,00%", "atingido": bool(id_2m_val <= 0.30) if pd.notna(id_2m_val) else None},
                        {"label": "Share Skin (Botik)", "valor": fmt_pct(skin_val, 2), "meta": "≥ 2,10%", "atingido": bool(skin_val >= 0.021) if pd.notna(skin_val) else None},
                        {"label": "Desafio Fidelidade", "valor": fmt_pct(fid_val, 2), "meta": "≥ 20,00%", "atingido": bool(fid_val >= 0.20) if pd.notna(fid_val) else None},
                    ])
                    
                    st.markdown("#### 🎯 Radar de Alavancas Promocionais")
                    radar_df = pd.DataFrame(dict(
                        r=[cons_data.get("Penetração Boleto Turbinado", 0)*100, 
                           cons_data.get("Penetração Boleto Promocional", 0)*100,
                           cons_data.get("Resgate Fidelidade", 0)*100,
                           (skin_val*100) if skin_val else 0,
                           (fid_val*100) if fid_val else 0],
                        theta=['Boleto Turbinado', 'Boleto Promocional', 'Resgate Fidelidade', 'Skin (Botik)', 'Desafio Fidelidade']
                    ))
                    fig = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
                    fig.update_traces(fill='toself', line_color="#004225")
                    fig.update_layout(
                        font=dict(family="Inter, sans-serif", size=12),
                        margin=dict(l=40, r=40, t=20, b=20),
                        paper_bgcolor="#FFFFFF",
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma consultora encontrada nos dados após os filtros.")
        else:
            st.info("Dados de consultoras não disponíveis.")


render_tab_skin_e_categorias = render_tab_skin

