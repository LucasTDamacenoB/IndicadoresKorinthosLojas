"""
config.py — Constantes globais, mapeamento de PDVs e paleta institucional O Boticário (IAF 2026)
Dashboard Visão Mensal Fechada — CP Korinthos (Código 10063)
"""

# ═══════════════════════════════════════════════════════════════════
# MAPEAMENTO OFICIAL DOS 9 PDVs
# ═══════════════════════════════════════════════════════════════════

PDV_MAP = {
    "17110": {"sigla": "ITA 17110", "nome": "LOJA ITA", "cidade": "Itapetininga", "local": "Rua"},
    "16945": {"sigla": "SHO 16945", "nome": "LOJA SHO", "cidade": "Itapetininga", "local": "Shopping"},
    "17760": {"sigla": "PAB 17760", "nome": "LOJA PAB", "cidade": "Itapetininga", "local": "Hipermercado"},
    "16881": {"sigla": "IVA 16881", "nome": "LOJA IVA", "cidade": "Itapeva", "local": "Rua"},
    "5317":  {"sigla": "IRE 5317",  "nome": "LOJA IRE", "cidade": "Itararé", "local": "Rua"},
    "12690": {"sigla": "MAX 12690", "nome": "LOJA MAX", "cidade": "Itapeva", "local": "Hipermercado"},
    "16946": {"sigla": "COB 16946", "nome": "LOJA COB", "cidade": "Capão Bonito", "local": "Rua"},
    "16874": {"sigla": "API 16874", "nome": "LOJA API", "cidade": "Apiaí", "local": "Rua"},
    "16949": {"sigla": "ANG 16949", "nome": "LOJA ANG", "cidade": "Angatuba", "local": "Rua"},
}

PDV_EXTRA = {}
ALL_PDVS = {**PDV_MAP, **PDV_EXTRA}
TARGET_PDVS = list(PDV_MAP.keys())


def get_pdv_label(pdv_code: str) -> str:
    """Retorna label formatada para exibição institucional (ex: ITA 17110)."""
    pdv_str = str(pdv_code).strip().lstrip("0")
    for key, info in ALL_PDVS.items():
        if key == pdv_str or key.lstrip("0") == pdv_str:
            return info["sigla"]
    return f"PDV {pdv_str}"


def get_pdv_sigla(pdv_code: str) -> str:
    """Retorna a sigla/nome do PDV."""
    pdv_str = str(pdv_code).strip().lstrip("0")
    for key, info in ALL_PDVS.items():
        if key == pdv_str or key.lstrip("0") == pdv_str:
            return info.get("nome", info["sigla"])
    return pdv_str


def normalize_pdv(pdv_code) -> str:
    """Normaliza código PDV removendo zeros à esquerda e sufixo .0 de float."""
    s = str(pdv_code).strip()
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return s.lstrip("0")


# ═══════════════════════════════════════════════════════════════════
# PALETA DE CORES INSTITUCIONAL — O BOTICÁRIO (IAF 2026)
# ═══════════════════════════════════════════════════════════════════

COLORS = {
    # Verdes Institucionais O Boticário
    "boticario_dark_green": "#004225",
    "boticario_emerald": "#1B4D3E",
    "boticario_green": "#0DAB01",
    "boticario_forest": "#2D6A4F",
    "boticario_mint": "#E8F5E9",
    "boticario_light_green": "#D8F3DC",

    # Fundos
    "bg_primary": "#F8F9FA",
    "bg_secondary": "#FFFFFF",
    "bg_card": "#FFFFFF",
    "bg_card_hover": "#F1F5F9",

    # Textos High-Contrast
    "text_primary": "#0F172A",
    "text_secondary": "#334155",
    "text_muted": "#64748B",
    "text_light": "#94A3B8",

    # Acentos Nobres
    "gold": "#D4AF37",
    "gold_dark": "#B8860B",
    "gold_light": "#FEF9C3",
    "accent_primary": "#004225",
    "accent_secondary": "#1B4D3E",

    # Semânticos IAF
    "success": "#059669",
    "success_bg": "#ECFDF5",
    "danger": "#DC2626",
    "danger_bg": "#FEF2F2",
    "warning": "#D97706",
    "warning_bg": "#FFFBEB",
    "info": "#2563EB",
    "info_bg": "#EFF6FF",

    # Paleta de Gráficos (Plotly)
    "chart_palette": [
        "#004225",  # Boticário Dark Green
        "#059669",  # Emerald
        "#0DAB01",  # Fresh Green
        "#2563EB",  # Royal Blue
        "#7C3AED",  # Violet
        "#D97706",  # Amber
        "#DB2777",  # Pink/Skin
        "#0D9488",  # Teal
        "#4F46E5",  # Indigo
    ],
}

# ═══════════════════════════════════════════════════════════════════
# TIPOS DE ARQUIVO (para identificação automática)
# ═══════════════════════════════════════════════════════════════════

FILE_TYPE_RESUMO = "resumo_performance"
FILE_TYPE_RECEITA = "receita_canal"
FILE_TYPE_FIDELIDADE = "fidelidade"
FILE_TYPE_LOJA_DIGITAL = "loja_digital"
FILE_TYPE_CUIDADOS_FACIAIS = "cuidados_faciais"
FILE_TYPE_ID_CLIENTE = "id_cliente"
FILE_TYPE_CATEGORIAS = "receita_por_categoria"
FILE_TYPE_NPS_MELHORES = "nps_melhores"
FILE_TYPE_NPS_PIORES = "nps_piores"
FILE_TYPE_NPS_GERAL = "nps_geral"
FILE_TYPE_UNKNOWN = "unknown"

# ═══════════════════════════════════════════════════════════════════
# METAS OFICIAIS BOOK IAF 2026
# ═══════════════════════════════════════════════════════════════════

METAS_IAF_2026 = {
    "nps": {
        "meta": 90.9,
        "pontos": 35,
        "pilar": "Gestão Comercial",
        "tipo": "Oficial",
        "descricao": "NPS (Loja + E-comm CR + Prateleira Infinita + Serviços)",
    },
    "tme": {
        "meta_segundos": 7 * 60,  # 00:07:00
        "meta_texto": "00:07:00",
        "pontos": 35,
        "pilar": "Experiência Omni & Digital",
        "tipo": "Oficial",
        "descricao": "Tempo Médio de Espera (Ativo + Receptivo)",
        "habilitador": 0.95,  # Taxa Atendimento >= 95%
    },
    "conversao_digital": {
        "meta": 0.10,  # 10%
        "pilar": "Experiência Omni & Digital",
        "tipo": "Meta Interna Franquia",
        "descricao": "Taxa de Conversão da Loja Digital",
    },
    "id_cliente_cpf": {
        "meta": 1.15,  # 115%
        "pontos": 25,
        "pilar": "Experiência Omni & Digital",
        "tipo": "Oficial",
        "descricao": "% Atendimentos com CPF (com e sem compra) / Total Boletos",
    },
    "id_cliente_2min": {
        "meta": 0.90,  # > 90% válidos ou < 30% curto
        "meta_teto_2min": 0.30,  # vermelho se > 30% boletos < 2min
        "pilar": "Experiência Omni & Digital",
        "tipo": "Meta Interna",
        "descricao": "% Boletos com abertura do ID até emissão < 2 minutos",
    },
    "desafio_fidelidade": {
        "meta": 0.20,  # 20.00%
        "pontos": "IAF LAB",
        "pilar": "IAF LAB 2026",
        "tipo": "LAB (Inovação)",
        "descricao": "Penetração de Boletos com Desafios Concluídos no Beautybox",
    },
    "skin_lojas": {
        "meta": 0.021,  # 2.1% (Regional SP)
        "pontos": 25,
        "pilar": "Gestão Comercial",
        "tipo": "Oficial",
        "descricao": "Share GMV Cuidados Faciais + Marca Botik no Canal Loja",
    },
    "itens_boleto": {
        "meta": 2.50,
        "pilar": "Produtividade & Alavancas",
        "tipo": "Oficial",
        "descricao": "Quantidade Média de Itens por Boleto (IPB)",
    },
    "boleto_turbinado": {
        "meta": 0.31,  # 31%
        "pilar": "Produtividade & Alavancas",
        "tipo": "IAF LAB",
        "descricao": "Penetração de Boletos Turbinados no Ciclo",
    },
    "boleto_promocional": {
        "meta": 0.33,  # 33%
        "pilar": "Produtividade & Alavancas",
        "tipo": "IAF LAB",
        "descricao": "Penetração de Boletos Promocionais no Ciclo",
    },
    "resgate_fidelidade": {
        "meta": 0.52,  # 52%
        "pontos": 25,
        "pilar": "Fidelização",
        "tipo": "Oficial",
        "descricao": "Participação de Resgate de Pontos Fidelidade nos Boletos",
    },
    "conversao_fluxo": {
        "meta": 0.28,  # 28% (Meta LAB)
        "pilar": "Produtividade & Alavancas",
        "tipo": "IAF LAB",
        "descricao": "Conversão de Ação de Fluxo (Brindes Resgatados com Compra Adicional)",
    },
    "receita_pef": {
        "meta": 1.00,  # 100%
        "pontos": 100,
        "pilar": "Gestão Comercial",
        "tipo": "Oficial",
        "descricao": "Atingimento da Meta PEF do Franqueado (Receita Canal Loja)",
    },
}

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DO PDF E STREAMLIT
# ═══════════════════════════════════════════════════════════════════

APP_CONFIG = {
    "page_title": "Painel de Indicadores — CP Korinthos",
    "page_icon": "🌿",
    "layout": "wide",
    "empresa": "O Boticário",
    "cp_nome": "CP Korinthos (10063)",
}

PDF_CONFIG = {
    "page_format": "A4",
    "orientation": "L",
    "margin_left": 12,
    "margin_right": 12,
    "margin_top": 16,
    "margin_bottom": 12,
    "font_family": "Helvetica",
    "font_size_title": 18,
    "font_size_subtitle": 12,
    "font_size_header": 10,
    "font_size_body": 8,
    "font_size_small": 7,
    "color_header_bg": (0, 66, 37),      # #004225 Boticário
    "color_header_text": (255, 255, 255),
    "color_row_alt": (245, 247, 246),
    "color_row_normal": (255, 255, 255),
    "color_text": (15, 23, 42),
    "color_accent": (13, 171, 1),        # #0DAB01
    "color_success": (5, 150, 105),
    "color_danger": (220, 38, 38),
    "color_border": (203, 213, 225),
}
