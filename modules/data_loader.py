"""
data_loader.py — Leitura, identificação e interpretação resiliente dos arquivos Excel
Dashboard Visão Mensal Fechada — CP Korinthos (Código 10063) | IAF 2026
"""

import os
import glob
import logging
import re
import pandas as pd
import numpy as np
from typing import Union, Dict, Optional, Any, List

import modules.config as config

logger = logging.getLogger(__name__)


def _safe_numeric(val) -> Optional[float]:
    """Converte valor para float de forma segura tratando strings com vírgula e porcentagem."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace("R$", "").replace("%", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════
# FUNÇÕES DE LEITURA SEGURA
# ═══════════════════════════════════════════════════════════════════

def _read_excel_safe(source, **kwargs) -> Optional[pd.DataFrame]:
    """Lê um Excel de forma segura, resetando seek se necessário."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_excel(source, engine="openpyxl", **kwargs)
    except Exception as e:
        logger.error(f"Erro ao ler Excel: {e}")
        return None


def _get_sheet_names(source) -> list:
    """Retorna nomes das abas de um arquivo Excel."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")
        return xls.sheet_names
    except Exception as e:
        logger.error(f"Erro ao ler abas: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# IDENTIFICAÇÃO AUTOMÁTICA DE TIPO DE ARQUIVO
# ═══════════════════════════════════════════════════════════════════

def identify_file_type(uploaded_file) -> str:
    """
    Identifica o tipo de planilha pelo conteúdo (abas, colunas e cabeçalhos).
    Retorna uma das constantes FILE_TYPE_* de config.
    """
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        filename = getattr(uploaded_file, "name", str(uploaded_file)).lower()
        sheets = _get_sheet_names(uploaded_file)

        # 1. Receita Canal Loja — tem aba 'PERFORMANCE POR PDV'
        if "PERFORMANCE POR PDV" in sheets or "receitacanalloja" in filename:
            return config.FILE_TYPE_RECEITA

        # 2. Resumo de Performance vs. Indicadores ID Cliente vs. Cuidados Faciais
        if all(s in [str(x).upper() for x in sheets] for s in ["PDV", "CONSULTOR", "CP"]):
            if "resumo" in filename or "performance_v2" in filename:
                return config.FILE_TYPE_RESUMO
            if "id_cliente" in filename or "id cliente" in filename:
                return config.FILE_TYPE_ID_CLIENTE
            if "cuidados_faciais" in filename or "cuidados faciais" in filename:
                return config.FILE_TYPE_CUIDADOS_FACIAIS

            df_test = _read_excel_safe(uploaded_file, sheet_name="PDV", nrows=4)
            if df_test is not None:
                all_text = " ".join(str(c).upper() for c in df_test.columns)
                all_text += " " + " ".join(str(v).upper() for v in df_test.values.flatten() if pd.notna(v))
                
                if "ATENDIMENTOS NO ID" in all_text or "ATENDIMENTOS COM CPF" in all_text:
                    return config.FILE_TYPE_ID_CLIENTE
                if "BOLETO TURBINADO" in all_text or "SHARE DE ALAVANCAS" in all_text or "ITENS POR BOLETO" in all_text:
                    return config.FILE_TYPE_RESUMO
                if "BOTIK" in all_text:
                    return config.FILE_TYPE_CUIDADOS_FACIAIS

        # 3. Loja Digital — tem PDV + CONSULTOR(A) e col CLIENTES ENCAMINHADOS
        if any("CONSULTOR" in str(s).upper() for s in sheets) and "PDV" in sheets:
            df_test = _read_excel_safe(uploaded_file, sheet_name="PDV", nrows=4)
            if df_test is not None:
                cols_str = " ".join(str(c).upper() for c in df_test.columns)
                if "CLIENTES ENCAMINHADOS" in cols_str or "TME" in cols_str or "lojadigital" in filename or "loja digital" in filename:
                    return config.FILE_TYPE_LOJA_DIGITAL

        # 4. Fidelidade — tem PDV + Consultor e col 'Qnt de boleto'
        if "PDV" in sheets and any("CONSULTOR" in str(s).upper() for s in sheets):
            df_test = _read_excel_safe(uploaded_file, sheet_name="PDV", nrows=4)
            if df_test is not None:
                cols_str = " ".join(str(c).lower() for c in df_test.columns)
                if "desafios" in cols_str or "fidelidade" in cols_str or "fidelidade" in filename:
                    return config.FILE_TYPE_FIDELIDADE

        # 5. Cuidados Faciais — aba PDV com BOTIK
        if "cuidados_faciais" in filename or "cuidados faciais" in filename:
            return config.FILE_TYPE_CUIDADOS_FACIAIS

        # 6-8. NPS files (Sheet0)
        if "Sheet0" in sheets or "nps" in filename or "melhores" in filename or "piores" in filename:
            df_test = _read_excel_safe(uploaded_file, sheet_name="Sheet0", header=None, nrows=15)
            if df_test is not None:
                all_text = " ".join(str(v) for v in df_test.values.flatten() if pd.notna(v))

                if "Melhores" in all_text or "melhores" in filename:
                    return config.FILE_TYPE_NPS_MELHORES
                if "Piores" in all_text or "piores" in filename:
                    return config.FILE_TYPE_NPS_PIORES
                if "NPS Loja" in all_text or df_test.shape[1] <= 3 or "nps" in filename:
                    return config.FILE_TYPE_NPS_GERAL

        return config.FILE_TYPE_UNKNOWN

    except Exception as e:
        logger.error(f"Erro ao identificar tipo de arquivo: {e}")
        return config.FILE_TYPE_UNKNOWN


# ═══════════════════════════════════════════════════════════════════
# PARSERS INDIVIDUAIS DE ARQUIVOS
# ═══════════════════════════════════════════════════════════════════

def parse_filtros_periodo(source_or_xls) -> Optional[str]:
    """Extrai dinamicamente a competência da aba FILTROS (PERÍODO ATUAL)."""
    try:
        if isinstance(source_or_xls, pd.ExcelFile):
            xls = source_or_xls
        else:
            if hasattr(source_or_xls, "seek"):
                source_or_xls.seek(0)
            xls = pd.ExcelFile(source_or_xls, engine="openpyxl")

        # 1. Procura em abas com nome FILTROS ou similares
        filtro_sheets = [s for s in xls.sheet_names if "FILTRO" in s.upper()]
        sheets_to_check = filtro_sheets if filtro_sheets else xls.sheet_names

        for s_name in sheets_to_check:
            df_f = pd.read_excel(xls, sheet_name=s_name, header=None)
            if df_f is None or df_f.empty:
                continue

            for idx, row in df_f.iterrows():
                row_vals = [str(x).strip() for x in row if pd.notna(x) and str(x).strip() != ""]
                for c_idx, val in enumerate(row_vals):
                    v_upper = val.upper()
                    # Verifica se a célula contém 'PERÍODO ATUAL' ou 'PERIODO ATUAL' e NÃO 'ANTERIOR'
                    if ("PERÍODO ATUAL" in v_upper or "PERIODO ATUAL" in v_upper) and "ANTERIOR" not in v_upper:
                        if c_idx + 1 < len(row_vals):
                            cand = row_vals[c_idx + 1]
                            if cand and cand.upper() not in ["NAN", "NONE", "-", ""]:
                                return cand

            # Se for aba FILTROS e não achou a tag exata, procura por padrão DD/MM/AAAA - DD/MM/AAAA ou até
            if "FILTRO" in s_name.upper():
                for idx, row in df_f.iterrows():
                    for val in row:
                        if pd.notna(val):
                            m = re.search(r"(\d{2}/\d{2}/\d{4}\s*(?:-|até|a)\s*\d{2}/\d{2}/\d{4})", str(val), re.IGNORECASE)
                            if m:
                                return m.group(1).strip()
    except Exception as e:
        logger.debug(f"Aba FILTROS não continha período: {e}")
    return None


def parse_resumo(source) -> Optional[Dict[str, pd.DataFrame]]:
    """Parseia Resumo de Performance V2 (chaves 'PDV', 'CONSULTOR', 'CP')."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")

        df_pdv = pd.read_excel(xls, sheet_name="PDV", header=0)
        df_pdv.columns = [str(c).strip() for c in df_pdv.columns]

        df_cp = pd.read_excel(xls, sheet_name="CP", header=0)
        df_cp.columns = [str(c).strip() for c in df_cp.columns]

        df_consultor = pd.read_excel(xls, sheet_name="CONSULTOR", header=0)
        df_consultor.columns = [str(c).strip() for c in df_consultor.columns]

        periodo = parse_filtros_periodo(xls)

        return {"PDV": df_pdv, "CONSULTOR": df_consultor, "CP": df_cp, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear Resumo Performance: {e}")
        return None


def parse_receita(source) -> Optional[Dict[str, Any]]:
    """Parseia Receita Canal Loja — aba 'PERFORMANCE POR PDV' e 'FILTROS'."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")
        df = pd.read_excel(xls, sheet_name="PERFORMANCE POR PDV", header=None)
        periodo = parse_filtros_periodo(xls)
        return {"data": df, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear Receita Canal Loja: {e}")
        return None


def parse_id_cliente(source) -> Optional[Dict[str, Any]]:
    """Parseia Indicadores ID Cliente (chaves 'CP', 'PDV', 'CONSULTOR')."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")

        df_cp = pd.read_excel(xls, sheet_name="CP", header=None) if "CP" in xls.sheet_names else None
        df_pdv = pd.read_excel(xls, sheet_name="PDV", header=None) if "PDV" in xls.sheet_names else None
        df_cons = pd.read_excel(xls, sheet_name="CONSULTOR", header=0) if "CONSULTOR" in xls.sheet_names else None

        if df_cons is not None:
            df_cons.columns = [str(c).strip() for c in df_cons.columns]

        periodo = parse_filtros_periodo(xls)

        return {"CP": df_cp, "PDV": df_pdv, "CONSULTOR": df_cons, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear ID Cliente: {e}")
        return None


def parse_fidelidade(source) -> Optional[Dict[str, pd.DataFrame]]:
    """Parseia Programa Fidelidade (chaves 'CP', 'PDV', 'CONSULTOR')."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")

        df_cp = pd.read_excel(xls, sheet_name="CP", header=0) if "CP" in xls.sheet_names else None
        df_pdv = pd.read_excel(xls, sheet_name="PDV", header=0) if "PDV" in xls.sheet_names else None
        
        cons_sheet = [s for s in xls.sheet_names if "CONSULTOR" in s.upper()]
        df_cons = pd.read_excel(xls, sheet_name=cons_sheet[0], header=0) if cons_sheet else None

        if df_cp is not None: df_cp.columns = [str(c).strip() for c in df_cp.columns]
        if df_pdv is not None: df_pdv.columns = [str(c).strip() for c in df_pdv.columns]
        if df_cons is not None: df_cons.columns = [str(c).strip() for c in df_cons.columns]

        periodo = parse_filtros_periodo(xls)

        return {"CP": df_cp, "PDV": df_pdv, "CONSULTOR": df_cons, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear Fidelidade: {e}")
        return None


def parse_loja_digital(source) -> Optional[Dict[str, pd.DataFrame]]:
    """Parseia Loja Digital (chaves 'PDV', 'CONSULTOR')."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")

        df_pdv = pd.read_excel(xls, sheet_name="PDV", header=0) if "PDV" in xls.sheet_names else None
        
        cons_sheet = [s for s in xls.sheet_names if "CONSULTOR" in s.upper()]
        df_cons = pd.read_excel(xls, sheet_name=cons_sheet[0], header=0) if cons_sheet else None

        if df_pdv is not None: df_pdv.columns = [str(c).strip() for c in df_pdv.columns]
        if df_cons is not None: df_cons.columns = [str(c).strip() for c in df_cons.columns]

        periodo = parse_filtros_periodo(xls)

        return {"PDV": df_pdv, "CONSULTOR": df_cons, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear Loja Digital: {e}")
        return None


def parse_cuidados_faciais(source) -> Optional[Dict[str, pd.DataFrame]]:
    """Parseia Cuidados Faciais (chaves 'CP', 'PDV', 'CONSULTOR')."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xls = pd.ExcelFile(source, engine="openpyxl")

        df_cp = pd.read_excel(xls, sheet_name="CP", header=None) if "CP" in xls.sheet_names else None
        df_pdv = pd.read_excel(xls, sheet_name="PDV", header=None) if "PDV" in xls.sheet_names else None
        df_cons = pd.read_excel(xls, sheet_name="CONSULTOR", header=None) if "CONSULTOR" in xls.sheet_names else None

        periodo = parse_filtros_periodo(xls)

        return {"CP": df_cp, "PDV": df_pdv, "CONSULTOR": df_cons, "_periodo": periodo}
    except Exception as e:
        logger.error(f"Erro ao parsear Cuidados Faciais: {e}")
        return None


def parse_nps_ranking(source) -> Optional[pd.DataFrame]:
    """Parseia NPS Melhores / Piores (Sheet0 com dados de lojas)."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        df = pd.read_excel(source, sheet_name="Sheet0", header=None, engine="openpyxl")
        return df
    except Exception as e:
        logger.error(f"Erro ao parsear NPS Ranking: {e}")
        return None


def parse_nps_geral(source) -> Optional[Dict[str, Any]]:
    """Parseia NPS Geral (Sheet0)."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        df = pd.read_excel(source, sheet_name="Sheet0", header=None, engine="openpyxl")
        if df is None or df.empty:
            return None

        nps_value = None
        nps_objetivo = None
        nps_variacao_str = None
        nps_variacao_num = None
        benchmark_desc = "Benchmark histórico consolidado"

        for idx, row in df.iterrows():
            c0 = str(row.iloc[0]).strip().upper() if pd.notna(row.iloc[0]) else ""
            c1 = row.iloc[1] if df.shape[1] > 1 and pd.notna(row.iloc[1]) else None
            c1_str = str(c1).strip() if c1 is not None else ""

            # 1. Filtros / Benchmark
            if "FILTRO" in c0:
                if "BENCHMARK" in c1_str.upper() or "PERÍODO" in c1_str.upper() or "PERIODO" in c1_str.upper():
                    benchmark_desc = c1_str

            # 2. Objetivo: Row com Objetivo / Meta
            if "OBJETIVO" in c0 or "META" in c0:
                v_num = _safe_numeric(c1)
                if pd.notna(v_num) and v_num > 0:
                    nps_objetivo = float(v_num)

            # 3. Referência / Variação vs. Ano Anterior
            if "REFER" in c0 or "COMPARA" in c0 or "VARIA" in c0:
                if c1_str:
                    nps_variacao_str = c1_str
                    m = re.search(r"([+-]?\s*\d+[.,]?\d*)", c1_str)
                    if m:
                        try:
                            nps_variacao_num = float(m.group(1).replace(" ", "").replace(",", "."))
                        except Exception:
                            pass

            # 4. NPS Score: Linha com NPS Loja / Serviços / E-comm
            if "NPS" in c0 and ("LOJA" in c0 or "E-COMM" in c0 or "PRATELEIRA" in c0 or "SERVI" in c0 or "MÉTRICA" in c0 or "METRICA" in c0):
                v_num = _safe_numeric(c1)
                if pd.notna(v_num) and v_num > 0:
                    nps_value = float(v_num)

        # Fallback para o valor da última linha se nps_value não foi pego
        if nps_value is None:
            for idx in reversed(range(len(df))):
                val = _safe_numeric(df.iloc[idx, 1] if df.shape[1] > 1 else None)
                if pd.notna(val) and val > 0:
                    nps_value = float(val)
                    break

        return {
            "nps_geral": nps_value,
            "nps_objetivo": nps_objetivo,
            "nps_variacao_str": nps_variacao_str,
            "nps_variacao_num": nps_variacao_num,
            "nps_variacao": nps_variacao_str,
            "benchmark_desc": benchmark_desc,
        }
    except Exception as e:
        logger.error(f"Erro ao parsear NPS Geral: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# AUTO-DISCOVERY DE ARQUIVOS LOCAIS E MULTI-MESES
# ═══════════════════════════════════════════════════════════════════

MONTH_NAMES = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "março": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}

MONTH_DISPLAY = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}


def discover_available_months(dados_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Varre o diretório Dados/ em busca de subpastas com planilhas Excel (.xlsx).
    Identifica o mês e ano de cada pasta e as ordena cronologicamente.
    
    Retorna lista de dicionários ordenados cronologicamente:
    [
        {
            "id": "7. julho",
            "path": "c:/.../Dados/7. julho",
            "label": "Julho / 2026",
            "month_num": 7,
            "year": 2026,
            "sort_key": (2026, 7),
            "file_count": 9,
        },
        ...
    ]
    """
    if dados_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_dir = os.path.join(base_dir, "Dados")
        
    months = []
    if not os.path.isdir(dados_dir):
        return months
        
    for entry in os.listdir(dados_dir):
        full_path = os.path.join(dados_dir, entry)
        if not os.path.isdir(full_path):
            continue
            
        xlsx_files = [
            f for f in glob.glob(os.path.join(full_path, "*.xlsx"))
            if not os.path.basename(f).startswith("~$")
        ]
        if not xlsx_files:
            continue
            
        entry_lower = entry.lower()
        month_num = None
        year = 2026
        
        # 1. Ano no nome da pasta
        y_match = re.search(r"20\d\d", entry)
        if y_match:
            year = int(y_match.group(0))
            
        # 2. Número inicial da pasta (ex: '7. julho', '10. outubro', '08 - agosto')
        num_match = re.match(r"^\s*(\d+)", entry)
        if num_match:
            n = int(num_match.group(1))
            if 1 <= n <= 12:
                month_num = n
                
        # 3. Nome do mês em português
        for m_name, m_val in MONTH_NAMES.items():
            if m_name in entry_lower:
                month_num = m_val
                break
                
        if month_num is None:
            month_num = 99
            label = entry
        else:
            label = f"{MONTH_DISPLAY[month_num]} / {year}"
            
        months.append({
            "id": entry,
            "path": full_path,
            "label": label,
            "month_num": month_num,
            "year": year,
            "sort_key": (year, month_num),
            "file_count": len(xlsx_files),
        })
        
    # Ordenar cronologicamente
    months.sort(key=lambda x: x["sort_key"])
    
    # Se nenhuma subpasta com arquivos foi encontrada, verificar se existem arquivos diretamente em Dados/
    if not months:
        root_files = [
            f for f in glob.glob(os.path.join(dados_dir, "*.xlsx"))
            if not os.path.basename(f).startswith("~$")
        ]
        if root_files:
            months.append({
                "id": "_root",
                "path": dados_dir,
                "label": "Dados Gerais",
                "month_num": 1,
                "year": 2026,
                "sort_key": (2026, 1),
                "file_count": len(root_files),
            })
            
    return months


def load_files_for_folder(folder_path: str) -> Dict[str, Any]:
    """Carrega todos os arquivos .xlsx válidos de uma subpasta."""
    if not os.path.isdir(folder_path):
        return {}
    xlsx_files = [
        f for f in sorted(glob.glob(os.path.join(folder_path, "*.xlsx")))
        if not os.path.basename(f).startswith("~$")
    ]
    return load_all_files(xlsx_files)


def auto_discover_local_files(subdir: str = "mes_atual") -> list:
    """
    Busca automaticamente planilhas padrão na subpasta especificada de Dados/.
    
    Prioridade:
      1. Dados/<subdir>/*.xlsx  (ex: Dados/mes_atual/, Dados/mes_anterior/)
      2. Se subdir == 'mes_atual' ou 'mes_anterior', descobre cronologicamente as pastas de Dados/
      3. Dados/*.xlsx           (fallback: compatibilidade retroativa)
      4. Raiz do projeto *.xlsx (último recurso)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dados_base = os.path.join(base_dir, "Dados")
    
    # 1. Tenta a subpasta específica (mes_atual ou mes_anterior)
    subdir_path = os.path.join(dados_base, subdir)
    found_files = []
    
    if os.path.isdir(subdir_path):
        for f in sorted(glob.glob(os.path.join(subdir_path, "*.xlsx"))):
            if not os.path.basename(f).startswith("~$"):
                found_files.append(f)
                
    # 2. Se não encontrou, tenta descobrir dinamicamente pelas pastas de meses
    if not found_files and os.path.isdir(dados_base):
        discovered = discover_available_months(dados_base)
        if discovered:
            if subdir == "mes_atual":
                latest_folder = discovered[-1]["path"]
                for f in sorted(glob.glob(os.path.join(latest_folder, "*.xlsx"))):
                    if not os.path.basename(f).startswith("~$"):
                        found_files.append(f)
            elif subdir == "mes_anterior" and len(discovered) >= 2:
                prev_folder = discovered[-2]["path"]
                for f in sorted(glob.glob(os.path.join(prev_folder, "*.xlsx"))):
                    if not os.path.basename(f).startswith("~$"):
                        found_files.append(f)

    # 3. Fallback apenas para mes_atual se a subpasta não existir ou estiver vazia
    if not found_files and subdir == "mes_atual":
        if os.path.isdir(dados_base):
            for f in sorted(glob.glob(os.path.join(dados_base, "*.xlsx"))):
                if not os.path.basename(f).startswith("~$"):
                    found_files.append(f)
        
        # 4. Último recurso: raiz do projeto
        if not found_files:
            for f in sorted(glob.glob(os.path.join(base_dir, "*.xlsx"))):
                if not os.path.basename(f).startswith("~$") and f not in found_files:
                    found_files.append(f)
            
    return found_files


def _parse_by_type(source, ftype: str):
    """Executa o parser correspondente para o tipo de arquivo identificado."""
    if ftype == config.FILE_TYPE_RESUMO:
        return parse_resumo(source)
    elif ftype == config.FILE_TYPE_RECEITA:
        return parse_receita(source)
    elif ftype == config.FILE_TYPE_ID_CLIENTE:
        return parse_id_cliente(source)
    elif ftype == config.FILE_TYPE_FIDELIDADE:
        return parse_fidelidade(source)
    elif ftype == config.FILE_TYPE_LOJA_DIGITAL:
        return parse_loja_digital(source)
    elif ftype == config.FILE_TYPE_CUIDADOS_FACIAIS:
        return parse_cuidados_faciais(source)
    elif ftype == config.FILE_TYPE_NPS_MELHORES:
        return parse_nps_ranking(source)
    elif ftype == config.FILE_TYPE_NPS_PIORES:
        return parse_nps_ranking(source)
    elif ftype == config.FILE_TYPE_NPS_GERAL:
        return parse_nps_geral(source)
    return None


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT — CARREGAMENTO DE TODOS OS ARQUIVOS COM MERGE INTELIGENTE
# ═══════════════════════════════════════════════════════════════════

def load_all_files(uploaded_files: list, base_files: Optional[list] = None) -> Dict[str, Any]:
    """
    Processa uma lista de arquivos (file-like do Streamlit ou caminhos de disco).
    Permite mesclar com arquivos locais padrão caso o usuário faça upload parcial.
    Retorna dict com chaves FILE_TYPE_* e os dados consolidados.
    """
    data: Dict[str, Any] = {}
    file_log: List[str] = []
    
    uploaded_periods: List[tuple] = []
    base_periods: List[tuple] = []

    # 1. Carrega primeiro os arquivos base locais (se fornecidos)
    if base_files:
        for f in base_files:
            fname = getattr(f, "name", str(f))
            try:
                if hasattr(f, "seek"):
                    f.seek(0)
                ftype = identify_file_type(f)
                if hasattr(f, "seek"):
                    f.seek(0)
                parsed = _parse_by_type(f, ftype)
                if parsed is not None:
                    data[ftype] = parsed
                    file_log.append(f"📁 [Base] {os.path.basename(fname)} → {ftype}")
                    if isinstance(parsed, dict) and parsed.get("_periodo"):
                        base_periods.append((ftype, parsed.get("_periodo")))
            except Exception as e:
                logger.error(f"Erro ao processar base file {fname}: {e}")

    # 2. Carrega e sobrepõe com os arquivos enviados pelo usuário (upload)
    if uploaded_files:
        for f in uploaded_files:
            fname = getattr(f, "name", str(f))
            try:
                if hasattr(f, "seek"):
                    f.seek(0)
                ftype = identify_file_type(f)
                if hasattr(f, "seek"):
                    f.seek(0)
                parsed = _parse_by_type(f, ftype)
                if parsed is not None:
                    data[ftype] = parsed
                    file_log.append(f"⬆️ [Upload] {os.path.basename(fname)} → {ftype}")
                    if isinstance(parsed, dict) and parsed.get("_periodo"):
                        uploaded_periods.append((ftype, parsed.get("_periodo")))
                else:
                    file_log.append(f"⚠️ {os.path.basename(fname)} → {ftype} (falha no parse)")
            except Exception as e:
                file_log.append(f"❌ {os.path.basename(fname)} → erro: {e}")
                logger.error(f"Erro ao processar uploaded file {fname}: {e}")

    # 3. Determinação prioritária e assertiva do período de fechamento oficial
    priority_order = [
        config.FILE_TYPE_RESUMO,
        config.FILE_TYPE_RECEITA,
        config.FILE_TYPE_ID_CLIENTE,
        config.FILE_TYPE_LOJA_DIGITAL,
        config.FILE_TYPE_CUIDADOS_FACIAIS,
        config.FILE_TYPE_FIDELIDADE,
    ]
    
    final_period = None
    
    # Se o usuário fez upload de arquivos, o período dos arquivos de upload TEM PRECEDÊNCIA TOTAL
    if uploaded_periods:
        for ptype in priority_order:
            for up_type, up_period in uploaded_periods:
                if up_type == ptype and up_period and str(up_period).strip() not in ["None", "NAN", "", "-"]:
                    final_period = str(up_period).strip()
                    break
            if final_period:
                break
        if not final_period and uploaded_periods:
            final_period = str(uploaded_periods[0][1]).strip()

    # Se não veio em uploaded files, busca nos base files
    if not final_period and base_periods:
        for ptype in priority_order:
            for b_type, b_period in base_periods:
                if b_type == ptype and b_period and str(b_period).strip() not in ["None", "NAN", "", "-"]:
                    final_period = str(b_period).strip()
                    break
            if final_period:
                break
        if not final_period and base_periods:
            final_period = str(base_periods[0][1]).strip()

    if not final_period:
        final_period = "01/07/2026 - 31/07/2026"

    data["_log"] = file_log
    data["_periodo"] = final_period
    return data
