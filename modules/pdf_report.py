"""
pdf_report.py — Geração de relatório PDF profissional paginado
Acompanhamento de Indicadores (IAF 2026) — CP Korinthos
"""

import io
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import pandas as pd
import numpy as np
from fpdf import FPDF

from modules.config import PDF_CONFIG, COLORS, PDV_MAP, APP_CONFIG, get_pdv_label, get_pdv_sigla, METAS_IAF_2026
from modules import calculators

logger = logging.getLogger(__name__)


class RelatorioPDF(FPDF):
    """Relatório PDF profissional com layout paginado, cards visuais e tipografia institucional."""

    def __init__(self, titulo: str, periodo: str, cp_nome: str):
        super().__init__(
            orientation=PDF_CONFIG["orientation"],
            unit="mm",
            format=PDF_CONFIG["page_format"],
        )
        self.titulo = titulo
        self.periodo = periodo
        self.cp_nome = cp_nome
        self.set_auto_page_break(auto=True, margin=PDF_CONFIG["margin_bottom"] + 4)
        self._is_cover = False

    def cell(self, *args, **kwargs):
        """Override cell para sanitizar texto automaticamente sem perder acentuação."""
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = self._safe(kwargs["text"])
        elif len(args) >= 3 and isinstance(args[2], str):
            args = list(args)
            args[2] = self._safe(args[2])
            args = tuple(args)
        return super().cell(*args, **kwargs)

    def header(self):
        """Cabeçalho moderno em todas as páginas (exceto capa)."""
        if self._is_cover:
            return

        self.set_fill_color(0, 66, 37)  # Verde Boticário escuro
        self.rect(0, 0, 300, 14, "F")
        self.set_fill_color(13, 171, 1)  # Linha verde viva
        self.rect(0, 14, 300, 1.2, "F")

        self.set_font(PDF_CONFIG["font_family"], "B", 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(PDF_CONFIG["margin_left"], 3)
        self.cell(140, 8, f"{self.cp_nome} - {self.titulo}", 0, 0, "L")

        self.set_font(PDF_CONFIG["font_family"], "B", 9)
        self.set_text_color(167, 243, 208)
        self.set_xy(180, 3)
        self.cell(100, 8, f"Período: {self.periodo}", 0, 0, "R")

        self.ln(16)

    def footer(self):
        """Rodapé institucional com numeração de página."""
        if self._is_cover:
            return

        self.set_y(-11)
        self.set_font(PDF_CONFIG["font_family"], "I", 7.5)
        self.set_text_color(120, 130, 140)
        self.cell(0, 8, 'O Boticário • Programa IAF 2026 | Franquia Korinthos Cosméticos', 0, 0, 'L')
        self.cell(0, 8, f'Página {self.page_no()}/{{nb}}', 0, 0, 'R')

    @staticmethod
    def _safe(text: str) -> str:
        """Sanitiza texto preservando 100% dos acentos em Português e tratando caracteres fora do Latin-1."""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        replacements = {
            '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2026': '...', '•': '-',
            '≥': '>=', '≤': '<=', '±': '+-', '✓': '[OK]', '✕': '[GAP]',
            '🏬': '', '🏆': '', '🌟': '', '⚠️': '', '🥇': '1º', '🥈': '2º', '🥉': '3º',
            '👩‍💼': '', '🌿': '', '📄': '', '📁': '', '🎯': '', '🏛️': '', '✅': '[OK]', '❌': '[GAP]'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        try:
            text.encode('latin-1')
        except UnicodeEncodeError:
            text = text.encode('latin-1', errors='replace').decode('latin-1')
        return text

    def _section_title(self, text: str):
        self.set_font(PDF_CONFIG["font_family"], "B", 13)
        self.set_text_color(0, 66, 37)
        self.cell(0, 7.5, text, 0, 1, "L")
        
        self.set_fill_color(0, 66, 37)
        self.rect(PDF_CONFIG["margin_left"], self.get_y(), 50, 1.5, "F")
        self.ln(3.5)

    def _section_subtitle(self, text: str):
        self.set_font(PDF_CONFIG["font_family"], "B", 10)
        self.set_text_color(51, 65, 85)
        self.cell(0, 6.5, text, 0, 1, "L")
        self.ln(1)

    def _safe_int(self, val, default=0):
        if pd.isna(val) or val is None:
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def _format_val(self, val, fmt_type):
        if pd.isna(val) or val is None: return "-"
        try:
            if fmt_type == "pct": return f"{float(val)*100:.2f}%".replace('.', ',')
            if fmt_type == "float2": return f"{float(val):.2f}".replace('.', ',')
            if fmt_type == "float1": return f"{float(val):.2f}".replace('.', ',')
            if fmt_type == "nps": return f"{float(val):.2f}%".replace('.', ',')
            if fmt_type == "int":
                i_val = self._safe_int(val, None)
                return f"{i_val:,}".replace(',', '.') if i_val is not None else "-"
            if fmt_type == "money": return f"R$ {float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            pass
        return str(val)

    # 1. CAPA EXECUTIVA MODERNA
    def cover_page(self):
        self._is_cover = True
        self.add_page()
        page_w, page_h = self.w, self.h

        # Fundo elegante degradê escuro
        self.set_fill_color(15, 23, 42)  # Azul/Ardósia escuro premium
        self.rect(0, 0, page_w, page_h, "F")

        # Faixas de identidade visual O Boticário
        self.set_fill_color(0, 66, 37)  # Verde Boticário
        self.rect(0, 0, page_w, 7, "F")
        self.set_fill_color(13, 171, 1)  # Verde brilhante
        self.rect(0, 7, page_w, 2, "F")
        self.set_fill_color(0, 66, 37)
        self.rect(0, 0, 7, page_h, "F")

        # Card Central com moldura
        block_w = page_w - 70
        block_h = 105
        block_x = 35
        block_y = (page_h - block_h) / 2 - 5

        self.set_fill_color(30, 41, 59)
        self.rect(block_x, block_y, block_w, block_h, "F")
        self.set_draw_color(51, 65, 85)
        self.rect(block_x, block_y, block_w, block_h, "D")

        # Topo decorativo do card
        self.set_fill_color(0, 66, 37)
        self.rect(block_x, block_y, block_w, 4, "F")

        # Tag superior
        self.set_font(PDF_CONFIG["font_family"], "B", 11)
        self.set_text_color(167, 243, 208)
        self.set_xy(block_x, block_y + 16)
        self.cell(block_w, 8, "O BOTICÁRIO • PROGRAMA IAF 2026", 0, 1, "C")

        # TÍTULO PRINCIPAL ATUALIZADO
        self.set_font(PDF_CONFIG["font_family"], "B", 26)
        self.set_text_color(255, 255, 255)
        self.set_xy(block_x, block_y + 26)
        self.cell(block_w, 14, "ACOMPANHAMENTO DE INDICADORES", 0, 1, "C")

        # Linha divisória fina
        self.set_fill_color(13, 171, 1)
        self.rect(page_w / 2 - 35, block_y + 44, 70, 1.5, "F")

        # Subtítulo Unidade
        self.set_font(PDF_CONFIG["font_family"], "B", 13.5)
        self.set_text_color(226, 232, 240)
        self.set_xy(block_x, block_y + 49)
        self.cell(block_w, 8, "CP Korinthos (10063) • 9 Unidades Operacionais", 0, 1, "C")

        # Bloco dinâmico do período
        self.set_fill_color(15, 23, 42)
        box_p_w = 120
        box_p_h = 16
        box_p_x = (page_w - box_p_w) / 2
        box_p_y = block_y + 64
        self.rect(box_p_x, box_p_y, box_p_w, box_p_h, "F")
        self.set_draw_color(0, 66, 37)
        self.rect(box_p_x, box_p_y, box_p_w, box_p_h, "D")

        self.set_font(PDF_CONFIG["font_family"], "B", 11)
        self.set_text_color(167, 243, 208)
        self.set_xy(box_p_x, box_p_y + 3.5)
        self.cell(box_p_w, 8, f"Período de Análise: {self.periodo}", 0, 1, "C")

        # Rodapé da capa
        self.set_font(PDF_CONFIG["font_family"], "I", 9)
        self.set_text_color(148, 163, 184)
        self.set_xy(0, page_h - 22)
        self.cell(page_w, 6, f"Relatório Executivo gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", 0, 1, "C")
        self._is_cover = False

    # 2. PÁGINA DE KPIS GERAIS DO CP
    def kpi_page(self, cp_summary: dict, df: pd.DataFrame):
        self.add_page()
        self._section_title("Visão Consolidada da Franquia (CP Korinthos)")

        receita = cp_summary.get("receita_total_gmv")
        if pd.isna(receita) or not receita:
            receita = df["receita"].sum() if ("receita" in df.columns and pd.notna(df["receita"].sum())) else 0

        nps = cp_summary.get("nps_geral")
        if pd.isna(nps):
            nps = df["nps"].mean() if ("nps" in df.columns and pd.notna(df["nps"].mean())) else 0

        boletos = cp_summary.get("volume_boletos")
        if pd.isna(boletos) or not boletos:
            boletos = df["volume_boletos"].sum() if ("volume_boletos" in df.columns and pd.notna(df["volume_boletos"].sum())) else 0

        ticket = cp_summary.get("ticket_medio")
        if pd.isna(ticket) or not ticket:
            ticket = (receita / boletos) if (pd.notna(boletos) and boletos > 0 and pd.notna(receita)) else 0

        meta_pef = cp_summary.get("meta_pef_atingimento")
        if pd.isna(meta_pef) or not meta_pef:
            meta_pef = df["meta_pef_realizado"].mean() if ("meta_pef_realizado" in df.columns and pd.notna(df["meta_pef_realizado"].mean())) else 0

        boletos_int = self._safe_int(boletos, 0)
        boletos_display = f"{boletos_int:,}".replace(',', '.') if boletos_int > 0 else "-"

        kpis = [
            ("Receita Total (GMV)", f"R$ {float(receita):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(receita) else "-"),
            ("NPS Geral", f"{float(nps):.2f}%".replace('.', ',') if pd.notna(nps) else "-"),
            ("Volume Boletos", boletos_display),
            ("Ticket Médio", f"R$ {float(ticket):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(ticket) else "-"),
            ("Atingimento PEF", f"{float(meta_pef)*100:.2f}%".replace('.', ',') if pd.notna(meta_pef) else "-"),
        ]

        box_w = 51
        gap = 5
        total_w = len(kpis) * box_w + (len(kpis) - 1) * gap
        start_x = (self.w - total_w) / 2
        y_pos = self.get_y() + 2

        for i, (label, value) in enumerate(kpis):
            x = start_x + i * (box_w + gap)
            
            self.set_fill_color(248, 250, 252)
            self.set_draw_color(226, 232, 240)
            self.rect(x, y_pos, box_w, 26, "DF")
            
            self.set_fill_color(0, 66, 37)
            self.rect(x, y_pos, box_w, 2.5, "F")
            
            self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
            self.set_text_color(100, 116, 139)
            self.set_xy(x, y_pos + 4)
            self.cell(box_w, 5, label.upper(), 0, 0, "C")
            
            self.set_font(PDF_CONFIG["font_family"], "B", 12)
            self.set_text_color(15, 23, 42)
            self.set_xy(x, y_pos + 11)
            self.cell(box_w, 8, value, 0, 0, "C")

        self.set_y(y_pos + 34)
        self._section_subtitle("Representatividade e Atingimento por Unidade Operacional")
        
        headers = ["Loja / Unidade", "Cidade", "Receita Realizada (R$)", "Share Rede (%)", "Meta PEF (%)", "Volume Boletos"]
        rows = []
        for _, row in df.sort_values("receita", ascending=False).iterrows():
            rows.append([
                f"{row['nome_loja']} ({row['pdv']})",
                row.get("cidade", "-"),
                self._format_val(row.get("receita"), "money"),
                self._format_val(row.get("representatividade"), "pct"),
                self._format_val(row.get("meta_pef_realizado"), "pct"),
                self._format_val(row.get("volume_boletos"), "int"),
            ])
        self._draw_table(headers, rows, [48, 38, 48, 28, 28, 28])

    # 3. SCORECARD EXECUTIVO POR LOJA (1 PÁGINA EXCLUSIVA POR LOJA)
    def store_pages(self, df: pd.DataFrame, data_raw):
        cdf = calculators.get_consultant_data_for_tab(data_raw, "resumo") if data_raw else pd.DataFrame()
        
        # Filtro estrito: remover Samanta e registros de cabeçalho/total
        if not cdf.empty and "Consultor" in cdf.columns:
            cdf = cdf[~cdf["Consultor"].astype(str).str.contains("SAMANTA MORETTI", case=False, na=False)]
            cdf = cdf[~cdf["Consultor"].astype(str).str.upper().str.strip().isin(["TODOS", "TOTAL", "GERAL", "NAN"])]

        for _, row in df.sort_values("score_global", ascending=False).iterrows():
            self.add_page()
            
            # Título formatado exato: "LOJA IVA - Itapeva (16881)"
            store_header_title = f"{row['nome_loja']} - {row['cidade']} ({row['pdv']})"
            score = self._safe_int(row.get('score_global'), 0)

            # Banner Superior da Loja
            self.set_fill_color(0, 66, 37)
            self.rect(PDF_CONFIG["margin_left"], self.get_y(), self.w - 2 * PDF_CONFIG["margin_left"], 13, "F")
            
            self.set_font(PDF_CONFIG["font_family"], "B", 12)
            self.set_text_color(255, 255, 255)
            self.set_xy(PDF_CONFIG["margin_left"] + 4, self.get_y() + 2.5)
            self.cell(150, 8, store_header_title, 0, 0, "L")
            
            self.set_font(PDF_CONFIG["font_family"], "B", 10.5)
            self.set_text_color(167, 243, 208)
            self.cell(110, 8, f"Score IAF: {score} / 12 Metas Batidas", 0, 0, "R")
            self.ln(16)

            # CARDS DE INDICADORES (Grid compacto 2 colunas x 6 linhas)
            self._section_subtitle("Scorecard de Metas da Loja (IAF 2026)")
            indicators = [
                ("1. NPS (Loja)", row.get("nps"), 90.90, "nps", True, "Meta: >= 90,90%"),
                ("2. TME Loja Digital", row.get("tme_ajustado_segundos"), 420, "time", False, "Meta: <= 07:00"),
                ("3. % ID Cliente (CPF)", row.get("id_cliente_cpf"), 1.15, "pct", True, "Meta: >= 115,00%"),
                ("4. % Boletos < 2 min", row.get("id_cliente_2min"), 0.30, "pct", False, "Meta: <= 30,00%"),
                ("5. Desafio Fidelidade", row.get("penetracao_desafio_fidelidade"), 0.20, "pct", True, "Meta: >= 20,00%"),
                ("6. Share Skin (Botik)", row.get("cuidados_faciais"), 0.021, "pct", True, "Meta: >= 2,10%"),
                ("7. % Meta PEF", row.get("meta_pef_realizado"), 1.00, "pct", True, "Meta: >= 100,00%"),
                ("8. Itens por Boleto", row.get("itens_boleto"), 2.50, "float2", True, "Meta: >= 2,50"),
                ("9. % Boleto Turbinado", row.get("boletos_turbinados"), 0.31, "pct", True, "Meta: >= 31,00%"),
                ("10. % Boleto Promocional", row.get("boletos_promocionais"), 0.33, "pct", True, "Meta: >= 33,00%"),
                ("11. % Resgate Fidelidade", row.get("resgate_fidelidade"), 0.52, "pct", True, "Meta: >= 52,00%"),
                ("12. % Ação de Fluxo", row.get("conversao_acao_fluxo"), 0.28, "pct", True, "Meta: >= 28,00%"),
            ]

            x_start = PDF_CONFIG["margin_left"]
            y_start = self.get_y() + 1
            card_w = 132
            card_h = 7.8
            
            for idx, (label, val, meta, fmt, is_higher_better, meta_str) in enumerate(indicators):
                col = idx % 2
                row_num = idx // 2
                x = x_start + (col * (card_w + 6))
                y = y_start + (row_num * (card_h + 1.8))

                is_ok = False
                val_str = "-"
                if pd.notna(val):
                    if fmt == "time":
                        val_str = str(row.get("tme_ajustado", "-"))
                        is_ok = (val <= meta and val > 0)
                    else:
                        val_str = self._format_val(val, fmt)
                        is_ok = (val >= meta) if is_higher_better else (val <= meta)

                bg_color = (240, 253, 244) if is_ok else (254, 242, 242)
                border_color = (167, 243, 208) if is_ok else (254, 202, 202)
                self.set_fill_color(*bg_color)
                self.set_draw_color(*border_color)
                self.rect(x, y, card_w, card_h, "DF")

                # Label
                self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                self.set_text_color(30, 41, 59)
                self.set_xy(x + 2.5, y + 1.4)
                self.cell(48, 5, label, 0, 0, "L")

                # Meta
                self.set_font(PDF_CONFIG["font_family"], "I", 7)
                self.set_text_color(100, 116, 139)
                self.set_xy(x + 50, y + 1.4)
                self.cell(32, 5, meta_str, 0, 0, "L")

                # Valor
                val_color = (5, 150, 105) if is_ok else (220, 38, 38)
                self.set_font(PDF_CONFIG["font_family"], "B", 8)
                self.set_text_color(*val_color)
                self.set_xy(x + 82, y + 1.4)
                self.cell(28, 5, val_str, 0, 0, "R")

                # Badge
                badge_bg = (5, 150, 105) if is_ok else (220, 38, 38)
                self.set_fill_color(*badge_bg)
                self.rect(x + 113, y + 1.4, 16, 5, "F")
                self.set_font(PDF_CONFIG["font_family"], "B", 6.5)
                self.set_text_color(255, 255, 255)
                self.set_xy(x + 113, y + 1.4)
                self.cell(16, 5, "[OK]" if is_ok else "[GAP]", 0, 0, "C")

            self.set_y(y_start + (6 * (card_h + 1.8)) + 3)

            # TABELA DE CONSULTORAS DA LOJA (MAIOR ESPAÇO E DESTAQUE VERMELHO)
            self._section_subtitle("Desempenho Individual da Equipe de Consultoras")
            if not cdf.empty:
                store_label = row["label"]
                store_cdf = cdf[cdf["Loja"] == store_label].copy()

                if not store_cdf.empty:
                    headers = ["Consultor(a)", "Receita (R$)", "Boleto Médio", "Itens/Bol.", "% Bol. Turbinado", "% Resgate Fid."]
                    col_widths = [68, 40, 36, 28, 38, 38]
                    
                    self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                    self.set_fill_color(0, 66, 37)
                    self.set_text_color(255, 255, 255)
                    self.set_draw_color(226, 232, 240)
                    for i, h in enumerate(headers):
                        self.cell(col_widths[i], 6, h, 1, 0, "C", True)
                    self.ln()

                    self.set_font(PDF_CONFIG["font_family"], "", 7.5)

                    for r_idx, c_row in store_cdf.iterrows():
                        if self.get_y() + 6 > self.h - 14:
                            self.add_page()
                            self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                            self.set_fill_color(0, 66, 37)
                            self.set_text_color(255, 255, 255)
                            for i, h in enumerate(headers):
                                self.cell(col_widths[i], 6, h, 1, 0, "C", True)
                            self.ln()
                            self.set_font(PDF_CONFIG["font_family"], "", 7.5)

                        bg_row = (248, 250, 252) if r_idx % 2 == 0 else (255, 255, 255)
                        self.set_fill_color(*bg_row)
                        
                        consultor = str(c_row.get("Consultor", "-"))
                        receita = c_row.get("Receita")
                        bol_medio = c_row.get("Boleto Médio")
                        itens_bol = c_row.get("Itens por Boleto")
                        bol_turb = c_row.get("Penetração Boleto Turbinado")
                        resg_fid = c_row.get("Resgate Fidelidade")

                        self.set_text_color(30, 41, 59)
                        self.cell(col_widths[0], 6, consultor[:30], 1, 0, "L", True)
                        self.cell(col_widths[1], 6, self._format_val(receita, "money"), 1, 0, "R", True)
                        self.cell(col_widths[2], 6, self._format_val(bol_medio, "money"), 1, 0, "R", True)

                        # Itens / Bol (Meta >= 2.5)
                        val_str = self._format_val(itens_bol, "float2")
                        color_ipb = (220, 38, 38) if (pd.notna(itens_bol) and float(itens_bol) < 2.50) else (5, 150, 105)
                        self.set_text_color(*color_ipb)
                        self.cell(col_widths[3], 6, val_str, 1, 0, "R", True)

                        # Bol Turbinado (Meta >= 31%)
                        val_str = self._format_val(bol_turb, "pct")
                        color_bt = (220, 38, 38) if (pd.notna(bol_turb) and float(bol_turb) < 0.31) else (5, 150, 105)
                        self.set_text_color(*color_bt)
                        self.cell(col_widths[4], 6, val_str, 1, 0, "R", True)

                        # Resgate Fidelidade (Meta >= 52%)
                        val_str = self._format_val(resg_fid, "pct")
                        color_rf = (220, 38, 38) if (pd.notna(resg_fid) and float(resg_fid) < 0.52) else (5, 150, 105)
                        self.set_text_color(*color_rf)
                        self.cell(col_widths[5], 6, val_str, 1, 0, "R", True)

                        self.ln()
                else:
                    self.set_font(PDF_CONFIG["font_family"], "I", 8)
                    self.set_text_color(100, 116, 139)
                    self.cell(0, 8, "Nenhuma consultora registrada para esta unidade.", 0, 1, "L")
            else:
                self.set_font(PDF_CONFIG["font_family"], "I", 8)
                self.set_text_color(100, 116, 139)
                self.cell(0, 8, "Dados de consultoras não disponíveis.", 0, 1, "L")

    # 4. PÁGINA DE RANKINGS POR INDICADOR (TOP 3 E OPORTUNIDADES)
    def ranking_page(self, df: pd.DataFrame):
        self.add_page()
        self._section_title("Rankings por Indicador - Top 3 e Oportunidades")

        metrics = [
            ("TME Loja Digital (Menor é Melhor)", "tme_ajustado_segundos", "tme_ajustado", True),
            ("NPS Geral (Satisfação do Consumidor)", "nps", "nps", False),
            ("Conversão Digital / Ação de Fluxo", "conversao_acao_fluxo", "conversao_acao_fluxo", False),
            ("Penetração de Desafios Fidelidade", "penetracao_desafio_fidelidade", "penetracao_desafio_fidelidade", False),
        ]

        positions = [(15, self.get_y() + 2), (150, self.get_y() + 2),
                     (15, self.get_y() + 58), (150, self.get_y() + 58)]

        for idx, (title, sort_col, disp_col, ascending) in enumerate(metrics):
            x_pos, y_pos = positions[idx]

            df_valid = df.dropna(subset=[sort_col])
            if df_valid.empty:
                continue

            df_sorted = df_valid.sort_values(sort_col, ascending=ascending)
            top3 = df_sorted.head(3)
            bottom3 = df_sorted.tail(3)

            self.set_fill_color(248, 250, 252)
            self.set_draw_color(226, 232, 240)
            self.rect(x_pos, y_pos, 126, 50, "DF")

            self.set_fill_color(0, 66, 37)
            self.rect(x_pos, y_pos, 126, 6, "F")
            self.set_font(PDF_CONFIG["font_family"], "B", 8)
            self.set_text_color(255, 255, 255)
            self.set_xy(x_pos + 4, y_pos + 1)
            self.cell(118, 5, title, 0, 1, "L")

            # Top 3
            self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
            self.set_text_color(5, 150, 105)
            self.set_xy(x_pos + 4, y_pos + 8)
            self.cell(56, 4, "TOP 3 DESTAQUES", 0, 1, "L")

            for rank, (_, r) in enumerate(top3.iterrows()):
                self.set_xy(x_pos + 4, y_pos + 13 + rank * 5.5)
                self.set_font(PDF_CONFIG["font_family"], "", 7.5)
                self.set_text_color(30, 41, 59)
                medal = f"{rank+1}º"
                val = self._format_ranking_val(r[disp_col], disp_col)
                self.cell(6, 5, medal, 0, 0, "C")
                self.cell(26, 5, r["sigla"][:14], 0, 0, "L")
                self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                self.set_text_color(5, 150, 105)
                self.cell(24, 5, val, 0, 0, "R")

            # Bottom 3
            self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
            self.set_text_color(220, 38, 38)
            self.set_xy(x_pos + 66, y_pos + 8)
            self.cell(56, 4, "OPORTUNIDADES DE MELHORIA", 0, 1, "L")

            for rank, (_, r) in enumerate(bottom3.iloc[::-1].iterrows()):
                self.set_xy(x_pos + 66, y_pos + 13 + rank * 5.5)
                self.set_font(PDF_CONFIG["font_family"], "", 7.5)
                self.set_text_color(30, 41, 59)
                val = self._format_ranking_val(r[disp_col], disp_col)
                self.cell(6, 5, "!", 0, 0, "C")
                self.cell(26, 5, r["sigla"][:14], 0, 0, "L")
                self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                self.set_text_color(220, 38, 38)
                self.cell(24, 5, val, 0, 0, "R")

    def _format_ranking_val(self, val, col_name):
        if pd.isna(val): return "-"
        if col_name == "tme_ajustado": return str(val)
        if col_name == "nps": return f"{val:.2f}%".replace('.', ',')
        if "conversao" in col_name or "penetracao" in col_name: return f"{val*100:.2f}%".replace('.', ',')
        return f"{val:.2f}".replace('.', ',')

    # 5. NOVA SEÇÃO: TOP LOJAS & PÓDIO DA REDE
    def top_stores_page(self, df: pd.DataFrame):
        self.add_page()
        self._section_title("Pódio da Rede - Classificação Geral das Lojas")

        df_sorted = df.sort_values(by=["score_global", "meta_pef_realizado"], ascending=[False, False]).copy()

        # PÓDIO 3 DESTAQUES (Cards Horizontais)
        self._section_subtitle("Pódio de Excelência Operacional (IAF 2026)")
        podium_configs = [
            ("1º LUGAR - CAMPEÃ", (254, 249, 195), (245, 158, 11), (146, 64, 14)),
            ("2º LUGAR - VICE-CAMPEÃ", (241, 245, 249), (148, 163, 184), (51, 65, 85)),
            ("3º LUGAR - 3ª COLOCADA", (255, 247, 237), (249, 115, 22), (154, 52, 18)),
        ]

        card_w = 84
        card_h = 36
        y_pos = self.get_y() + 2

        for i in range(min(3, len(df_sorted))):
            r = df_sorted.iloc[i]
            x_pos = PDF_CONFIG["margin_left"] + i * (card_w + 9)
            tag_title, bg_c, border_c, text_c = podium_configs[i]

            self.set_fill_color(*bg_c)
            self.set_draw_color(*border_c)
            self.rect(x_pos, y_pos, card_w, card_h, "DF")

            self.set_font(PDF_CONFIG["font_family"], "B", 8)
            self.set_text_color(*text_c)
            self.set_xy(x_pos, y_pos + 3)
            self.cell(card_w, 5, tag_title, 0, 1, "C")

            self.set_font(PDF_CONFIG["font_family"], "B", 11)
            self.set_text_color(15, 23, 42)
            self.set_xy(x_pos, y_pos + 9)
            self.cell(card_w, 6, f"{r['nome_loja']} ({r['sigla']})", 0, 1, "C")

            self.set_font(PDF_CONFIG["font_family"], "", 8)
            self.set_text_color(71, 85, 105)
            self.set_xy(x_pos, y_pos + 16)
            self.cell(card_w, 5, f"Cidade: {r['cidade']}", 0, 1, "C")

            score = self._safe_int(r.get('score_global'), 0)
            pef_val = f"{r.get('meta_pef_realizado', 0)*100:.2f}%".replace('.', ',')
            self.set_font(PDF_CONFIG["font_family"], "B", 10)
            self.set_text_color(0, 66, 37)
            self.set_xy(x_pos, y_pos + 23)
            self.cell(card_w, 6, f"Score: {score}/12 Metas  |  PEF: {pef_val}", 0, 1, "C")

        # TABELA CLASSIFICAÇÃO COMPLETA DAS 9 LOJAS
        self.set_y(y_pos + card_h + 8)
        self._section_subtitle("Classificação Geral da Rede (Ranking de Estímulo à Melhoria Contínua)")

        headers = ["Posição", "Loja / Unidade", "Cidade", "Score IAF", "Meta PEF (%)", "NPS (%)", "TME Digital", "Receita GMV (R$)"]
        rows = []
        for rank, (_, r) in enumerate(df_sorted.iterrows()):
            score = self._safe_int(r.get('score_global'), 0)
            rows.append([
                f"{rank+1}º Lugar",
                f"{r['nome_loja']} ({r['pdv']})",
                r.get("cidade", "-"),
                f"{score} / 12 Metas",
                self._format_val(r.get("meta_pef_realizado"), "pct"),
                f"{r.get('nps', 0):.2f}%".replace('.', ',') if pd.notna(r.get("nps")) else "-",
                str(r.get("tme_ajustado", "-")),
                self._format_val(r.get("receita"), "money"),
            ])
        self._draw_table(headers, rows, [24, 48, 36, 28, 28, 24, 28, 38])

    # 6. NOVA SEÇÃO: TABELA COMPARATIVA VISUAL DE TODAS AS LOJAS
    def comparative_matrix_page(self, df: pd.DataFrame):
        self.add_page()
        self._section_title("Matriz Comparativa Visual de Resultados (Scorecard Panorâmico)")
        self._section_subtitle("Comparativo de Desempenho dos 9 PDVs nas 12 Metas Oficiais IAF 2026")

        df_sorted = df.sort_values(by="score_global", ascending=False).copy()

        headers = ["Loja / PDV", "Score", "PEF (>=100%)", "NPS (>=90,90%)", "TME (<=07:00)", "CPF (>=115%)", "2min (<=30%)", "Fid (>=20%)", "Skin (>=2,10%)", "IPB (>=2,50)", "BT (>=31%)", "BP (>=33%)", "Resg (>=52%)"]
        col_widths = [40, 18, 22, 20, 20, 20, 18, 18, 18, 18, 18, 18, 18]

        row_h = 7

        # Header
        self.set_font(PDF_CONFIG["font_family"], "B", 7)
        self.set_fill_color(0, 66, 37)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)

        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, 1, 0, "C", True)
        self.ln()

        # Linhas de Dados com Cores Dinâmicas
        self.set_font(PDF_CONFIG["font_family"], "", 7)

        for r_idx, (_, r) in enumerate(df_sorted.iterrows()):
            bg_color = (248, 250, 252) if r_idx % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg_color)

            # 1. Loja
            self.set_text_color(30, 41, 59)
            self.set_font(PDF_CONFIG["font_family"], "B", 7)
            self.cell(col_widths[0], row_h, f"{r['sigla']} ({r['pdv']})", 1, 0, "L", True)

            # 2. Score
            score = self._safe_int(r.get("score_global"), 0)
            self.set_text_color(0, 66, 37)
            self.cell(col_widths[1], row_h, f"{score}/12", 1, 0, "C", True)

            # Indicadores com formatação condicional de cor
            self.set_font(PDF_CONFIG["font_family"], "B", 7)

            # PEF
            pef = r.get("meta_pef_realizado")
            is_ok = pd.notna(pef) and pef >= 1.00
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[2], row_h, self._format_val(pef, "pct"), 1, 0, "C", True)

            # NPS
            nps = r.get("nps")
            is_ok = pd.notna(nps) and nps >= 90.9
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[3], row_h, f"{nps:.2f}%".replace('.', ',') if pd.notna(nps) else "-", 1, 0, "C", True)

            # TME
            tme_s = r.get("tme_ajustado_segundos")
            is_ok = pd.notna(tme_s) and tme_s <= 420
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[4], row_h, str(r.get("tme_ajustado", "-")), 1, 0, "C", True)

            # CPF
            cpf = r.get("id_cliente_cpf")
            is_ok = pd.notna(cpf) and cpf >= 1.15
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[5], row_h, self._format_val(cpf, "pct"), 1, 0, "C", True)

            # 2min
            b2m = r.get("id_cliente_2min")
            is_ok = pd.notna(b2m) and b2m <= 0.30
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[6], row_h, self._format_val(b2m, "pct"), 1, 0, "C", True)

            # Fidelidade
            fid = r.get("penetracao_desafio_fidelidade")
            is_ok = pd.notna(fid) and fid >= 0.20
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[7], row_h, self._format_val(fid, "pct"), 1, 0, "C", True)

            # Skin
            skin = r.get("cuidados_faciais")
            is_ok = pd.notna(skin) and skin >= 0.021
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[8], row_h, self._format_val(skin, "pct"), 1, 0, "C", True)

            # IPB
            ipb = r.get("itens_boleto")
            is_ok = pd.notna(ipb) and ipb >= 2.50
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[9], row_h, self._format_val(ipb, "float2"), 1, 0, "C", True)

            # BT
            bt = r.get("boletos_turbinados")
            is_ok = pd.notna(bt) and bt >= 0.31
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[10], row_h, self._format_val(bt, "pct"), 1, 0, "C", True)

            # BP
            bp = r.get("boletos_promocionais")
            is_ok = pd.notna(bp) and bp >= 0.33
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[11], row_h, self._format_val(bp, "pct"), 1, 0, "C", True)

            # Resgate
            resg = r.get("resgate_fidelidade")
            is_ok = pd.notna(resg) and resg >= 0.52
            self.set_text_color(*( (5, 150, 105) if is_ok else (220, 38, 38) ))
            self.cell(col_widths[12], row_h, self._format_val(resg, "pct"), 1, 0, "C", True)

            self.ln()

        # Legenda explicativa no rodapé da matriz
        self.set_y(self.get_y() + 8)
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.rect(PDF_CONFIG["margin_left"], self.get_y(), self.w - 2 * PDF_CONFIG["margin_left"], 14, "DF")

        self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
        self.set_text_color(5, 150, 105)
        self.set_xy(PDF_CONFIG["margin_left"] + 4, self.get_y() + 2.5)
        self.cell(100, 4, "VERDE: Indicador atingiu ou superou a meta oficial IAF 2026.", 0, 0, "L")

        self.set_text_color(220, 38, 38)
        self.cell(150, 4, "VERMELHO: Indicador abaixo da meta oficial - Oportunidade prioritária de ação.", 0, 1, "L")

        self.set_font(PDF_CONFIG["font_family"], "I", 7)
        self.set_text_color(100, 116, 139)
        self.set_xy(PDF_CONFIG["margin_left"] + 4, self.get_y() + 1)
        self.cell(250, 4, "Utilize esta matriz panorâmica para traçar alinhamentos táticos com as lideranças de loja e planos de desenvolvimento.", 0, 0, "L")

    # 7. TABELA FORMATADA AUXILIAR
    def _draw_table(self, headers: list, rows: list, col_widths: Optional[list] = None):
        if col_widths is None:
            total_w = self.w - PDF_CONFIG["margin_left"] - PDF_CONFIG["margin_right"]
            col_widths = [total_w / len(headers)] * len(headers)

        row_h = 6.5

        self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
        self.set_fill_color(0, 66, 37)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)

        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, 1, 0, "C", True)
        self.ln()

        self.set_font(PDF_CONFIG["font_family"], "", 7.5)
        self.set_text_color(30, 41, 59)

        for row_idx, row_data in enumerate(rows):
            if self.get_y() + row_h > self.h - 14:
                self.add_page()
                self.set_font(PDF_CONFIG["font_family"], "B", 7.5)
                self.set_fill_color(0, 66, 37)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], row_h, h, 1, 0, "C", True)
                self.ln()
                self.set_font(PDF_CONFIG["font_family"], "", 7.5)
                self.set_text_color(30, 41, 59)

            bg_color = (248, 250, 252) if row_idx % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg_color)

            for i, val in enumerate(row_data):
                align = "L" if i in [0, 1] else "R"
                self.cell(col_widths[i], row_h, str(val), 1, 0, align, True)
            self.ln()

    # GERAÇÃO COMPLETA
    def generate(self, df: pd.DataFrame, cp_summary: dict, data_raw=None) -> bytes:
        self.alias_nb_pages()
        self.cover_page()
        self.kpi_page(cp_summary, df)
        self.store_pages(df, data_raw)
        self.ranking_page(df)
        self.top_stores_page(df)
        self.comparative_matrix_page(df)
        return bytes(self.output())


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def generate_pdf_report(df: pd.DataFrame, cp_summary: dict, data_raw=None) -> bytes:
    """
    Gera relatório PDF profissional paginado no formato moderno e retorna como bytes.
    """
    try:
        report = RelatorioPDF(
            titulo="Acompanhamento de Indicadores",
            periodo=cp_summary.get("periodo", "Mês Atual"),
            cp_nome=APP_CONFIG["cp_nome"],
        )
        return report.generate(df, cp_summary, data_raw)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise
