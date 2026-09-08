import logging
import re
import textwrap
import sys
import os

# Garante que o diretório raiz do projeto esteja no sys.path (essencial para o Streamlit Cloud / Linux)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st


def render_html(html_str):
    if not html_str:
        return
    clean = re.sub(r"\n\s*", " ", html_str)
    st.markdown(clean, unsafe_allow_html=True)


import importlib
import pandas as pd

import modules.calculators as calculators
import modules.config as config
import modules.data_loader as data_loader
import modules.pdf_report as pdf_report
import modules.visualizations as visualizations

importlib.reload(config)
importlib.reload(data_loader)
importlib.reload(calculators)
importlib.reload(visualizations)
importlib.reload(pdf_report)

from modules.calculators import build_consolidated, get_consultant_data, get_cp_summary
from modules.config import APP_CONFIG, TARGET_PDVS, get_pdv_label
from modules.data_loader import auto_discover_local_files, load_all_files
from modules.pdf_report import generate_pdf_report
from modules.visualizations import (
    render_tab_consulta_universal,
    render_tab_fidelidade,
    render_tab_idcliente,
    render_tab_indicadores,
    render_tab_nps,
    render_tab_receita,
    render_tab_resumo,
    render_tab_skin,
    render_tab_tme,
)

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM O BOTICÁRIO
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Painel de Indicadores — CP Korinthos",
    page_icon=APP_CONFIG.get("page_icon", "🌿"),
    layout=APP_CONFIG.get("layout", "wide"),
    initial_sidebar_state="expanded",
)

st.html(
    textwrap.dedent("""
<style>
    /* Tipografia Inter / Segoe UI */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #0F172A;
    }
    
    .stApp {
        background-color: #F8F9FA;
    }

    /* Sidebar Institucional */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #1E293B !important;
        font-weight: 600;
    }

    /* Header e Navegação */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Abas Institucionais - Verde O Boticário */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #FFFFFF;
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F8FAFC;
        border-radius: 8px;
        color: #334155 !important;
        font-weight: 700;
        font-size: 13.5px;
        padding: 8px 16px;
        border: 1px solid #E2E8F0;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E8F5E9;
        color: #004225 !important;
        border-color: #A7F3D0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004225 !important;
        color: #FFFFFF !important;
        border: 1px solid #004225 !important;
        box-shadow: 0 2px 6px rgba(0, 66, 37, 0.25);
    }
    .stTabs [aria-selected="true"] span {
        color: #FFFFFF !important;
    }

    /* Dataframes e Tabelas */
    .stDataFrame {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        background: #FFFFFF;
    }

    /* Uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #004225;
        border-radius: 12px;
        padding: 12px;
        background: #F8FAF9;
    }
    [data-testid="stFileUploader"] label {
        color: #004225 !important;
        font-weight: 700 !important;
    }

    /* Botões */
    .stDownloadButton button,
    .stDownloadButton button p,
    .stDownloadButton button span,
    .stDownloadButton button div {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    .stDownloadButton > button {
        background-color: #004225 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background-color: #1B4D3E !important;
        box-shadow: 0 4px 12px rgba(0, 66, 37, 0.25) !important;
        color: #FFFFFF !important;
    }

    /* Selectbox */
    .stSelectbox label {
        color: #004225 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
    }
    
    /* Standardize KPI card heights */
    .kpi-card { min-height: 110px; display: flex; flex-direction: column; justify-content: space-between; }
</style>
""")
)


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.html(
        textwrap.dedent("""
    <div style="text-align: center; padding: 10px 0 16px 0;">
        <div style="font-size: 38px; margin-bottom: 2px;">🌿</div>
        <div style="font-size: 19px; font-weight: 900; color: #004225; letter-spacing: 0.5px;">
            PAINEL DE INDICADORES
        </div>
        <div style="font-size: 12px; color: #0DAB01; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;">
            CP Korinthos (10063)
        </div>
        <div style="height: 3px; background: linear-gradient(90deg, transparent, #004225, #0DAB01, transparent);
                    margin: 12px 0;"></div>
    </div>
    """)
    )

    st.html("#### 📁 Importar / Atualizar Planilhas")
    uploaded_files = st.file_uploader(
        "Carregue planilhas .xlsx adicionais:",
        type=["xlsx"],
        accept_multiple_files=True,
        help="Caso deseje substituir os dados automáticos, arraste aqui os novos arquivos do Gestão Integrada.",
    )

    pdf_placeholder = st.empty()
    info_placeholder = st.empty()


# ═══════════════════════════════════════════════════════════════════
# CARREGAMENTO E CONSOLIDAÇÃO DE DADOS
# ═══════════════════════════════════════════════════════════════════


local_files = auto_discover_local_files()
if uploaded_files:
    data = load_all_files(uploaded_files, base_files=local_files)
else:
    data = load_all_files(local_files)

df = build_consolidated(data)
cp_summary = get_cp_summary(data)
consultant_df = get_consultant_data(data)
periodo_exibicao = data.get("_periodo", "Período Atual") if data else "Período Atual"


# ═══════════════════════════════════════════════════════════════════
# CONTEÚDO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

if df is not None and not df.empty:
    # Log de arquivos na sidebar
    with info_placeholder.container():
        with st.expander("📋 Planilhas Processadas", expanded=False):
            for log_line in data.get("_log", []):
                render_html(
                    f'<div style="font-size: 12px; color: #334155; margin-bottom: 3px;">{log_line}</div>'
                )

    # Botão de exportação PDF na sidebar
    with pdf_placeholder.container():
        st.html("#### 📄 Relatório Executivo")
        try:
            pdf_bytes = generate_pdf_report(df, cp_summary, data_raw=data)
            st.download_button(
                label="⬇️ Baixar Relatório PDF",
                data=pdf_bytes,
                file_name=f"relatorio_iaf2026_cp_korinthos_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Exportação PDF: {e}")

    # ─── HEADER INSTITUCIONAL ─────────────────────────────────────
    render_html(f"""
    <div style="background: linear-gradient(135deg, #004225 0%, #1B4D3E 100%); padding: 22px 28px; border-radius: 14px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,66,37,0.15); color: #FFFFFF;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <div style="font-size: 13px; font-weight: 800; color: #A7F3D0; text-transform: uppercase; letter-spacing: 1px;">
                    O Boticário • Programa IAF 2026
                </div>
                <h1 style="color: #FFFFFF; font-size: 28px; font-weight: 900; margin: 4px 0 2px 0; letter-spacing: -0.5px;">
                    Painel de Indicadores — CP Korinthos (10063)
                </h1>
                <div style="font-size: 14px; color: #E2E8F0; font-weight: 500;">
                    Franquia Korinthos Cosméticos • 9 Unidades Operacionais
                </div>
            </div>
            <div style="background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 10px; padding: 10px 18px; text-align: right;">
                <div style="font-size: 11px; font-weight: 700; color: #A7F3D0; text-transform: uppercase; letter-spacing: 0.5px;">Competência</div>
                <div style="font-size: 18px; font-weight: 800; color: #FFFFFF;">{periodo_exibicao}</div>
            </div>
        </div>
    </div>
    """)

    # ─── FILTROS GLOBAIS ──────────────────────────────────────────
    excluir_gerencia = st.checkbox(
        "Desconsiderar Gerência Geral (Samanta Moretti Da Costa)",
        value=True,
        key="excluir_gerencia",
    )

    # Aplicar filtro de loja aos dataframes (filtros de consultora serão passados as tabs)
    df_filtered = df.copy()
    consultant_df_filtered = consultant_df.copy() if consultant_df is not None else None
    busca_consultora = ""  # No longer filtered at top level

    # ─── 9 MÓDULOS ANALÍTICOS (ABAS) ──────────────────────────────
    tab_1, tab_2, tab_3, tab_4, tab_5, tab_6, tab_7, tab_8, tab_9 = st.tabs(
        [
            "1 | NPS",
            "2 | TME e Conversão",
            "3 | ID Cliente",
            "4 | Fidelidade",
            "5 | Skin Lojas",
            "6 | Indicadores Gerais",
            "7 | Receita Lojas",
            "8 | Resumo Geral",
            "9 | Consulta Universal",
        ]
    )

    with tab_1:
        render_tab_nps(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_2:
        render_tab_tme(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_3:
        render_tab_idcliente(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_4:
        render_tab_fidelidade(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_5:
        render_tab_skin(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_6:
        render_tab_indicadores(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_7:
        render_tab_receita(
            df_filtered,
            consultant_df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_8:
        render_tab_resumo(
            df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

    with tab_9:
        render_tab_consulta_universal(
            df_filtered,
            data_raw=data,
            excluir_gerencia=excluir_gerencia,
            busca_consultora=busca_consultora,
        )

else:
    st.html(
        textwrap.dedent("""
    <div style="text-align: center; padding: 60px 20px; background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0; max-width: 600px; margin: 40px auto;">
        <div style="font-size: 50px; margin-bottom: 10px;">🌿</div>
        <h2 style="color: #004225; font-weight: 800;">Carregando Fechamento Mensal</h2>
        <p style="color: #64748B; font-size: 14px;">
            Nenhuma planilha encontrada automaticamente na pasta <code>Dados/</code>. Por favor, arraste as planilhas do ciclo pelo menu lateral.
        </p>
    </div>
    """)
    )
