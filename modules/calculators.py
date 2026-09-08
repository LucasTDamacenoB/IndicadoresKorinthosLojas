"""
calculators.py — Consolidação de métricas, rankings e diagnósticos estratégicos (IAF 2026)
Dashboard Visão Mensal Fechada — CP Korinthos (Código 10063)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

import modules.config as config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# UTILITÁRIOS DE CONVERSÃO E FORMATAÇÃO
# ═══════════════════════════════════════════════════════════════════

def _time_str_to_seconds(t_str) -> int:
    """Converte string de tempo (HH:MM:SS ou MM:SSs) para segundos inteiros."""
    try:
        if pd.isna(t_str):
            return 0
        t_str = str(t_str).strip().rstrip("s").strip()
        parts = t_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0
    except Exception:
        return 0


def _seconds_to_time_str(seconds: int) -> str:
    """Converte segundos inteiros para formato legível MM:SS ou HH:MM:SS."""
    try:
        if seconds <= 0:
            return "00:00"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "00:00"


def _safe_numeric(value) -> float:
    """Converte valor para float numérico seguro."""
    try:
        result = pd.to_numeric(value, errors="coerce")
        return float(result) if pd.notna(result) else np.nan
    except Exception:
        return np.nan


# ═══════════════════════════════════════════════════════════════════
# CONSOLIDAÇÃO DOS 9 PDVs (TABELA MESTRE)
# ═══════════════════════════════════════════════════════════════════

def build_consolidated(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Constrói a tabela mestre contendo os 9 PDVs oficiais e todas as métricas consolidadas
    lidas dinamicamente a partir dos arquivos fornecidos.
    """
    rows = []
    for pdv_code in config.TARGET_PDVS:
        info = config.PDV_MAP[pdv_code]
        rows.append({
            "pdv": pdv_code,
            "sigla": info["sigla"],
            "nome_loja": info.get("nome", info["sigla"]),
            "label": config.get_pdv_label(pdv_code),
            "cidade": info["cidade"],
            "local": info["local"],
        })

    df = pd.DataFrame(rows)
    df.set_index("pdv", inplace=True)

    # Inicializar colunas numéricas
    cols = [
        "receita", "receita_loja", "receita_anterior", "receita_vs_meta", "receita_vs_anterior", 
        "meta_pef_realizado", "representatividade", "meta_pef_loja", "meta_pef_total", "gap_pef", "receita_cr",
        "volume_boletos", "ticket_medio", "itens_boleto", "preco_medio",
        "boletos_turbinados", "boletos_promocionais", "share_alavancas",
        "penetracao_mobshop", "boletos_1", "penetracao_fidelidade",
        "penetracao_desafio_fidelidade", "boletos_desafio_qtd", "boletos_fidelidade_qtd",
        "resgate_fidelidade", "conversao_acao_fluxo",
        "id_cliente_cpf", "id_cliente_2min", "id_cliente_validos",
        "nps", "nps_registros",
        "tme_ajustado_segundos", "clientes_encaminhados", "clientes_atendidos",
        "clientes_convertidos", "conversao_digital",
        "servicos_loja", "clique_retire", "cuidados_faciais", "receita_skin",
        "loja_digital_atendimento",
    ]
    for c in cols:
        df[c] = np.nan

    df["tme_ajustado"] = ""
    df["id_cliente_tma"] = ""

    # 1. RESUMO DE PERFORMANCE V2 (Base principal de Varejo)
    if config.FILE_TYPE_RESUMO in data and data[config.FILE_TYPE_RESUMO] is not None:
        resumo = data[config.FILE_TYPE_RESUMO]
        df_pdv = resumo.get("PDV")
        if df_pdv is not None and len(df_pdv) > 0:
            for idx in range(len(df_pdv)):
                pdv_raw = str(df_pdv.iloc[idx, 0]).strip()
                if pdv_raw.upper() in ["TODOS", "TOTAL", "NAN", "", "PDV", "TIPO DE RECEITA"]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                row = df_pdv.iloc[idx]
                df.loc[pdv, "receita"] = _safe_numeric(row.iloc[1])
                df.loc[pdv, "receita_vs_meta"] = _safe_numeric(row.iloc[2])
                df.loc[pdv, "receita_vs_anterior"] = _safe_numeric(row.iloc[3])
                df.loc[pdv, "volume_boletos"] = _safe_numeric(row.iloc[4])
                df.loc[pdv, "ticket_medio"] = _safe_numeric(row.iloc[7])
                df.loc[pdv, "itens_boleto"] = _safe_numeric(row.iloc[13])
                df.loc[pdv, "preco_medio"] = _safe_numeric(row.iloc[16])
                
                # Alavancas (se vier em percentual 0-100 ou 0-1)
                bt_val = _safe_numeric(row.iloc[19])
                df.loc[pdv, "boletos_turbinados"] = bt_val / 100.0 if (pd.notna(bt_val) and bt_val > 1.0) else bt_val
                
                bp_val = _safe_numeric(row.iloc[22])
                df.loc[pdv, "boletos_promocionais"] = bp_val / 100.0 if (pd.notna(bp_val) and bp_val > 1.0) else bp_val
                
                sh_val = _safe_numeric(row.iloc[25])
                df.loc[pdv, "share_alavancas"] = sh_val / 100.0 if (pd.notna(sh_val) and sh_val > 1.0) else sh_val
                
                mob_val = _safe_numeric(row.iloc[28])
                df.loc[pdv, "penetracao_mobshop"] = mob_val / 100.0 if (pd.notna(mob_val) and mob_val > 1.0) else mob_val
                
                b1_val = _safe_numeric(row.iloc[31])
                df.loc[pdv, "boletos_1"] = b1_val / 100.0 if (pd.notna(b1_val) and b1_val > 1.0) else b1_val
                
                fid_val = _safe_numeric(row.iloc[34])
                df.loc[pdv, "penetracao_fidelidade"] = fid_val / 100.0 if (pd.notna(fid_val) and fid_val > 1.0) else fid_val
                
                # Resgate: se vier na escala 0-100 (ex: 53.73), divide por 100
                resg_val = _safe_numeric(row.iloc[37])
                if pd.notna(resg_val):
                    df.loc[pdv, "resgate_fidelidade"] = resg_val / 100.0 if resg_val > 1.0 else resg_val
                
                flx_val = _safe_numeric(row.iloc[40])
                df.loc[pdv, "conversao_acao_fluxo"] = flx_val / 100.0 if (pd.notna(flx_val) and flx_val > 1.0) else flx_val
                
                cf_val = _safe_numeric(row.iloc[43])
                df.loc[pdv, "cuidados_faciais"] = cf_val / 100.0 if (pd.notna(cf_val) and cf_val > 1.0) else cf_val
                
                df.loc[pdv, "servicos_loja"] = _safe_numeric(row.iloc[49])
                
                # Clique e Retire
                cr_val = _safe_numeric(row.iloc[52])
                df.loc[pdv, "clique_retire"] = cr_val

                # TME do resumo (fallback)
                tme_raw = str(row.iloc[58]).strip() if len(row) > 58 and pd.notna(row.iloc[58]) else ""
                if tme_raw and tme_raw.lower() != "nan":
                    df.loc[pdv, "tme_ajustado"] = tme_raw
                    df.loc[pdv, "tme_ajustado_segundos"] = _time_str_to_seconds(tme_raw)

    # 2. RECEITA CANAL LOJA (Metas PEF, Gaps e Realizado)
    if config.FILE_TYPE_RECEITA in data and data[config.FILE_TYPE_RECEITA] is not None:
        rec_data = data[config.FILE_TYPE_RECEITA]
        df_rec = rec_data.get("data") if isinstance(rec_data, dict) else rec_data
        if df_rec is not None:
            # Pula cabeçalhos (linhas 0, 1, 2) e linha de Total CP (linha 3). Começa na linha 4.
            for idx in range(4, len(df_rec)):
                pdv_raw = str(df_rec.iloc[idx, 1]).strip()
                if not pdv_raw or pdv_raw.upper() in ["NAN", "", "NONE", "TOTAL"]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                rec_ant = _safe_numeric(df_rec.iloc[idx, 4])
                rec_loja = _safe_numeric(df_rec.iloc[idx, 5])
                meta_pef_loja = _safe_numeric(df_rec.iloc[idx, 6])
                gap_loja = _safe_numeric(df_rec.iloc[idx, 7])
                rec_cr = _safe_numeric(df_rec.iloc[idx, 11])
                rec_total = _safe_numeric(df_rec.iloc[idx, 17])
                meta_pef_total = _safe_numeric(df_rec.iloc[idx, 18])
                gap_total = _safe_numeric(df_rec.iloc[idx, 19])
                realizado_total = _safe_numeric(df_rec.iloc[idx, 21])

                if pd.notna(rec_ant): df.loc[pdv, "receita_anterior"] = rec_ant
                if pd.notna(rec_loja): df.loc[pdv, "receita_loja"] = rec_loja
                if pd.notna(meta_pef_loja): df.loc[pdv, "meta_pef_loja"] = meta_pef_loja
                if pd.notna(rec_cr): df.loc[pdv, "receita_cr"] = rec_cr
                if pd.notna(rec_total): df.loc[pdv, "receita"] = rec_total
                if pd.notna(meta_pef_total): df.loc[pdv, "meta_pef_total"] = meta_pef_total
                if pd.notna(gap_total): df.loc[pdv, "gap_pef"] = gap_total

                if pd.notna(realizado_total):
                    df.loc[pdv, "meta_pef_realizado"] = realizado_total
                elif pd.notna(meta_pef_total) and meta_pef_total > 0 and pd.notna(rec_total):
                    df.loc[pdv, "meta_pef_realizado"] = rec_total / meta_pef_total
                elif pd.notna(meta_pef_loja) and meta_pef_loja > 0 and pd.notna(rec_loja):
                    df.loc[pdv, "meta_pef_realizado"] = rec_loja / meta_pef_loja

    # 3. INDICADORES ID CLIENTE (CPF e Boletos < 2min)
    if config.FILE_TYPE_ID_CLIENTE in data and data[config.FILE_TYPE_ID_CLIENTE] is not None:
        id_data = data[config.FILE_TYPE_ID_CLIENTE]
        df_id_pdv = id_data.get("PDV") if isinstance(id_data, dict) else None
        if df_id_pdv is not None and len(df_id_pdv) > 1:
            for idx in range(1, len(df_id_pdv)):
                pdv_raw = str(df_id_pdv.iloc[idx, 0]).strip()
                if pdv_raw.upper() in ["TODOS", "TOTAL", "NAN", "", "PDV"]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                # Col 11: % ATENDIMENTOS COM CPF (IAF 2026) PERÍODO ATUAL
                cpf_pct = _safe_numeric(df_id_pdv.iloc[idx, 11])
                if pd.notna(cpf_pct):
                    df.loc[pdv, "id_cliente_cpf"] = cpf_pct

                # Col 17: TMA CPF
                tma_val = str(df_id_pdv.iloc[idx, 17]).strip()
                if tma_val and tma_val.upper() != "NAN":
                    df.loc[pdv, "id_cliente_tma"] = tma_val

                # Col 32: % BOLETOS ID CLIENTE VÁLIDOS
                val_pct = _safe_numeric(df_id_pdv.iloc[idx, 32])
                if pd.notna(val_pct):
                    df.loc[pdv, "id_cliente_validos"] = val_pct

                # Col 38: % BOLETO ID CLIENTE ABAIXO DE 2MIN PERÍODO ATUAL
                b2m_pct = _safe_numeric(df_id_pdv.iloc[idx, 38])
                if pd.notna(b2m_pct):
                    df.loc[pdv, "id_cliente_2min"] = b2m_pct

    # 4. LOJA DIGITAL (TME e Conversão)
    if config.FILE_TYPE_LOJA_DIGITAL in data and data[config.FILE_TYPE_LOJA_DIGITAL] is not None:
        ld_data = data[config.FILE_TYPE_LOJA_DIGITAL]
        df_ld = ld_data.get("PDV") if isinstance(ld_data, dict) else ld_data
        if df_ld is not None:
            for _, row in df_ld.iterrows():
                pdv_raw = str(row.iloc[0]).strip()
                if pdv_raw.upper() in ["TODOS", "TOTAL", "NAN", ""]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                df.loc[pdv, "clientes_encaminhados"] = _safe_numeric(row.iloc[1])
                df.loc[pdv, "clientes_atendidos"] = _safe_numeric(row.iloc[2])

                tme_str = str(row.iloc[3]).strip()
                if tme_str and tme_str.lower() != "nan":
                    df.loc[pdv, "tme_ajustado"] = tme_str
                    df.loc[pdv, "tme_ajustado_segundos"] = _time_str_to_seconds(tme_str)

                df.loc[pdv, "clientes_convertidos"] = _safe_numeric(row.iloc[4])
                df.loc[pdv, "conversao_digital"] = _safe_numeric(row.iloc[5])

    # 5. PROGRAMA FIDELIDADE (Penetração Desafios)
    if config.FILE_TYPE_FIDELIDADE in data and data[config.FILE_TYPE_FIDELIDADE] is not None:
        fid_data = data[config.FILE_TYPE_FIDELIDADE]
        df_fid = fid_data.get("PDV") if isinstance(fid_data, dict) else fid_data
        if df_fid is not None:
            for _, row in df_fid.iterrows():
                pdv_raw = str(row.iloc[0]).strip()
                if pdv_raw.upper() in ["TODOS", "TOTAL", "NAN", ""]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                df.loc[pdv, "boletos_desafio_qtd"] = _safe_numeric(row.iloc[1])
                df.loc[pdv, "boletos_fidelidade_qtd"] = _safe_numeric(row.iloc[2])
                df.loc[pdv, "penetracao_desafio_fidelidade"] = _safe_numeric(row.iloc[3])

    # 6. CUIDADOS FACIAIS (Share Botik + Cuidados e RECEITA DE SKIN POR PDV)
    if config.FILE_TYPE_CUIDADOS_FACIAIS in data and data[config.FILE_TYPE_CUIDADOS_FACIAIS] is not None:
        cf_data = data[config.FILE_TYPE_CUIDADOS_FACIAIS]
        df_cf = cf_data.get("PDV") if isinstance(cf_data, dict) else cf_data
        if df_cf is not None:
            for idx in range(3, len(df_cf)):
                pdv_raw = str(df_cf.iloc[idx, 0]).strip()
                if not pdv_raw or pdv_raw.upper() in ["NAN", "", "NONE", "RECEITA TOTAL", "RECEITA CUIDADOS FACIAIS + BOTIK"]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                cf_pct = _safe_numeric(df_cf.iloc[idx, 1])
                rec_skin_pdv = _safe_numeric(df_cf.iloc[idx, 2])
                
                if pd.notna(cf_pct):
                    df.loc[pdv, "cuidados_faciais"] = cf_pct
                if pd.notna(rec_skin_pdv):
                    df.loc[pdv, "receita_skin"] = rec_skin_pdv

    # 7. NPS POR LOJA (Melhores / Piores)
    for ftype in [config.FILE_TYPE_NPS_MELHORES, config.FILE_TYPE_NPS_PIORES]:
        if ftype in data and data[ftype] is not None:
            df_nps = data[ftype]
            for idx in range(4, len(df_nps)):
                if df_nps.shape[1] < 4:
                    continue
                pdv_raw = str(df_nps.iloc[idx, 1]).strip()
                if not pdv_raw or pdv_raw.upper() in ["NAN", ""]:
                    continue
                pdv = config.normalize_pdv(pdv_raw)
                if pdv not in df.index:
                    continue

                nps_val = _safe_numeric(df_nps.iloc[idx, 3])
                registros = _safe_numeric(df_nps.iloc[idx, 2])
                if pd.notna(nps_val):
                    df.loc[pdv, "nps"] = nps_val
                if pd.notna(registros):
                    df.loc[pdv, "nps_registros"] = registros

    # 8. CÁLCULO DE SHARE E REPRESENTATIVIDADE
    total_rec = df["receita"].sum()
    if total_rec > 0:
        df["representatividade"] = df["receita"] / total_rec

    # 9. SCORE GLOBAL DAS 12 METAS EMPRESARIAIS IAF 2026
    for idx, row in df.iterrows():
        score = 0
        # 1. Meta PEF >= 100%
        if pd.notna(row.get("meta_pef_realizado")) and row["meta_pef_realizado"] >= 1.00: score += 1
        # 2. NPS >= 90.9%
        if pd.notna(row.get("nps")) and row["nps"] >= 90.9: score += 1
        # 3. TME <= 00:07:00 (420 segundos)
        tme_secs = row.get("tme_ajustado_segundos")
        if pd.notna(tme_secs) and tme_secs > 0 and tme_secs <= (7 * 60): score += 1
        # 4. Conversão Digital >= 10%
        conv_val = row.get("conversao_digital", row.get("conversao_acao_fluxo"))
        if pd.notna(conv_val) and conv_val >= 0.10: score += 1
        # 5. % Atendimentos com CPF >= 115%
        cpf_val = row.get("id_cliente_cpf")
        if pd.notna(cpf_val) and cpf_val >= 1.15: score += 1
        # 6. % Boletos < 2min <= 30%
        b2m_val = row.get("id_cliente_2min")
        if pd.notna(b2m_val) and b2m_val <= 0.30: score += 1
        # 7. Penetração Desafios Fidelidade >= 20%
        if pd.notna(row.get("penetracao_desafio_fidelidade")) and row["penetracao_desafio_fidelidade"] >= 0.20: score += 1
        # 8. Skin Cuidados Faciais + Botik >= 2.1%
        if pd.notna(row.get("cuidados_faciais")) and row["cuidados_faciais"] >= 0.021: score += 1
        # 9. Itens por Boleto >= 2.50
        if pd.notna(row.get("itens_boleto")) and row["itens_boleto"] >= 2.50: score += 1
        # 10. Boleto Turbinado >= 31%
        if pd.notna(row.get("boletos_turbinados")) and row["boletos_turbinados"] >= 0.31: score += 1
        # 11. Boleto Promocional >= 33%
        if pd.notna(row.get("boletos_promocionais")) and row["boletos_promocionais"] >= 0.33: score += 1
        # 12. Resgate Fidelidade >= 52%
        if pd.notna(row.get("resgate_fidelidade")) and row["resgate_fidelidade"] >= 0.52: score += 1

        df.loc[idx, "score_global"] = int(score)

    df.reset_index(inplace=True)
    return df


# ═══════════════════════════════════════════════════════════════════
# RESUMO CP KORINTHOS (NÍVEL CONSOLIDADO DA FRANQUIA — 100% DINÂMICO)
# ═══════════════════════════════════════════════════════════════════

def get_cp_summary(data: Dict[str, Any]) -> dict:
    """
    Retorna dicionário completo com os indicadores consolidados do CP Korinthos,
    extraídos dinamicamente de todas as planilhas importadas.
    """
    summary = {
        "periodo": data.get("_periodo", "Período Atual"),
        "nps_geral": np.nan,
        "nps_objetivo": 86.1,
        "nps_variacao": "Em comparação ao Ano Anterior",
        "tme_medio": "00:00:00",
        "conversao_digital": np.nan,
        "id_cliente_cpf": np.nan,
        "id_cliente_2min": np.nan,
        "id_cliente_tma": "00:00:00",
        "desafio_fidelidade": np.nan,
        "skin_share": np.nan,
        "receita_skin_cp": np.nan,
        "receita_total_gmv": np.nan,
        "meta_pef_total": np.nan,
        "meta_pef_atingimento": np.nan,
        "receita_loja_cp": np.nan,
        "meta_pef_loja_cp": np.nan,
        "receita_cr_cp": np.nan,
        "ticket_medio": np.nan,
        "itens_boleto": np.nan,
        "preco_medio": np.nan,
        "share_alavancas": np.nan,
        "boletos_1": np.nan,
        "boleto_turbinado": np.nan,
        "boleto_promocional": np.nan,
        "penetracao_mobshop": np.nan,
        "penetracao_fidelidade": np.nan,
        "resgate_fidelidade": np.nan,
        "conversao_fluxo": np.nan,
        "volume_boletos": np.nan,
    }

    # 1. RESUMO DE PERFORMANCE V2 (Aba CP)
    if config.FILE_TYPE_RESUMO in data and data[config.FILE_TYPE_RESUMO] is not None:
        res_data = data[config.FILE_TYPE_RESUMO]
        df_cp = res_data.get("CP") if isinstance(res_data, dict) else None
        if df_cp is not None and not df_cp.empty:
            for idx in range(len(df_cp)):
                metric_name = str(df_cp.iloc[idx, 0]).strip().lower()
                val_real = _safe_numeric(df_cp.iloc[idx, 4])
                val_meta = _safe_numeric(df_cp.iloc[idx, 3])

                if "receita total" in metric_name:
                    if pd.notna(val_real): summary["receita_total_gmv"] = val_real
                    if pd.notna(val_meta): summary["meta_pef_total"] = val_meta
                    if pd.notna(val_real) and pd.notna(val_meta) and val_meta > 0:
                        summary["meta_pef_atingimento"] = val_real / val_meta
                elif "quantidade de boletos" in metric_name:
                    if pd.notna(val_real): summary["volume_boletos"] = int(val_real)
                elif "boleto m" in metric_name and "dio" in metric_name:
                    if pd.notna(val_real): summary["ticket_medio"] = val_real
                elif "itens por boleto" in metric_name:
                    if pd.notna(val_real): summary["itens_boleto"] = val_real
                elif "pre" in metric_name and "dio" in metric_name:
                    if pd.notna(val_real): summary["preco_medio"] = val_real
                elif "share de alavancas" in metric_name:
                    if pd.notna(val_real): summary["share_alavancas"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "boleto b1" in metric_name:
                    if pd.notna(val_real): summary["boletos_1"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "boleto turbinado" in metric_name:
                    if pd.notna(val_real): summary["boleto_turbinado"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "boleto promocional" in metric_name:
                    if pd.notna(val_real): summary["boleto_promocional"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "receita mobshop" in metric_name:
                    if pd.notna(val_real): summary["penetracao_mobshop"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "boletos fidelidade" in metric_name:
                    if pd.notna(val_real): summary["penetracao_fidelidade"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "resgate fidelidade" in metric_name:
                    if pd.notna(val_real): summary["resgate_fidelidade"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "de fluxo" in metric_name:
                    if pd.notna(val_real): summary["conversao_fluxo"] = val_real / 100.0 if val_real > 1.0 else val_real
                elif "cuidados faciais" in metric_name:
                    if pd.notna(val_real): summary["skin_share"] = val_real / 100.0 if val_real > 1.0 else val_real

    # 2. RECEITA CANAL LOJA (Linha 3 de Total da Rede)
    if config.FILE_TYPE_RECEITA in data and data[config.FILE_TYPE_RECEITA] is not None:
        rec_data = data[config.FILE_TYPE_RECEITA]
        df_rec = rec_data.get("data") if isinstance(rec_data, dict) else rec_data
        if df_rec is not None and len(df_rec) > 3:
            # Linha 3 = Linha de TOTAL DO CP
            rec_loja = _safe_numeric(df_rec.iloc[3, 5])
            meta_loja = _safe_numeric(df_rec.iloc[3, 6])
            rec_cr = _safe_numeric(df_rec.iloc[3, 11])
            rec_total = _safe_numeric(df_rec.iloc[3, 17])
            meta_total = _safe_numeric(df_rec.iloc[3, 18])
            pef_ating = _safe_numeric(df_rec.iloc[3, 21])

            if pd.notna(rec_loja): summary["receita_loja_cp"] = rec_loja
            if pd.notna(meta_loja): summary["meta_pef_loja_cp"] = meta_loja
            if pd.notna(rec_cr): summary["receita_cr_cp"] = rec_cr
            if pd.notna(rec_total): summary["receita_total_gmv"] = rec_total
            if pd.notna(meta_total): summary["meta_pef_total"] = meta_total
            if pd.notna(pef_ating):
                summary["meta_pef_atingimento"] = pef_ating
            elif pd.notna(rec_total) and pd.notna(meta_total) and meta_total > 0:
                summary["meta_pef_atingimento"] = rec_total / meta_total

    # 3. LOJA DIGITAL (Linha TODOS da aba PDV)
    if config.FILE_TYPE_LOJA_DIGITAL in data and data[config.FILE_TYPE_LOJA_DIGITAL] is not None:
        ld_data = data[config.FILE_TYPE_LOJA_DIGITAL]
        df_ld = ld_data.get("PDV") if isinstance(ld_data, dict) else ld_data
        if df_ld is not None and not df_ld.empty:
            for idx in range(len(df_ld)):
                tag = str(df_ld.iloc[idx, 0]).strip().upper()
                if tag in ["TODOS", "TOTAL", "GERAL"]:
                    tme_str = str(df_ld.iloc[idx, 3]).strip()
                    conv_num = _safe_numeric(df_ld.iloc[idx, 5])
                    if tme_str and tme_str.lower() != "nan":
                        summary["tme_medio"] = tme_str
                    if pd.notna(conv_num):
                        summary["conversao_digital"] = conv_num
                    break

    # 4. NPS GERAL (Arquivo NPS Geral)
    if config.FILE_TYPE_NPS_GERAL in data and data[config.FILE_TYPE_NPS_GERAL] is not None:
        nps_data = data[config.FILE_TYPE_NPS_GERAL]
        if isinstance(nps_data, dict):
            if nps_data.get("nps_geral") is not None: summary["nps_geral"] = nps_data["nps_geral"]
            if nps_data.get("nps_objetivo") is not None: summary["nps_objetivo"] = nps_data["nps_objetivo"]
            if nps_data.get("nps_variacao_num") is not None: summary["nps_variacao_num"] = nps_data["nps_variacao_num"]
            if nps_data.get("nps_variacao_str") is not None: summary["nps_variacao_str"] = nps_data["nps_variacao_str"]
            if nps_data.get("nps_variacao") is not None: summary["nps_variacao"] = nps_data["nps_variacao"]
            if nps_data.get("benchmark_desc") is not None: summary["benchmark_desc"] = nps_data["benchmark_desc"]

    # 5. ID CLIENTE (Aba CP)
    if config.FILE_TYPE_ID_CLIENTE in data and data[config.FILE_TYPE_ID_CLIENTE] is not None:
        id_data = data[config.FILE_TYPE_ID_CLIENTE]
        df_cp = id_data.get("CP") if isinstance(id_data, dict) else None
        if df_cp is not None and len(df_cp) > 0:
            for idx in range(len(df_cp)):
                k = str(df_cp.iloc[idx, 0]).strip().lower()
                v = str(df_cp.iloc[idx, 1]).strip()
                
                if "atendimentos com cpf" in k and "%" in k:
                    v_clean = v.replace("%", "").replace(",", ".").strip()
                    try: summary["id_cliente_cpf"] = float(v_clean) / 100.0
                    except: pass
                elif "abaixo de 2min" in k and "%" in k:
                    v_clean = v.replace("%", "").replace(",", ".").strip()
                    try: summary["id_cliente_2min"] = float(v_clean) / 100.0
                    except: pass
                elif "tempo m" in k and "tma" in k:
                    summary["id_cliente_tma"] = v

    # 6. PROGRAMA FIDELIDADE (Aba CP)
    if config.FILE_TYPE_FIDELIDADE in data and data[config.FILE_TYPE_FIDELIDADE] is not None:
        fid_data = data[config.FILE_TYPE_FIDELIDADE]
        df_cp = fid_data.get("CP") if isinstance(fid_data, dict) else None
        if df_cp is not None and len(df_cp) > 0:
            val = _safe_numeric(df_cp.iloc[0, 3] if df_cp.shape[1] > 3 else None)
            if pd.notna(val): summary["desafio_fidelidade"] = val

    # 7. CUIDADOS FACIAIS / SKIN (Aba CP)
    if config.FILE_TYPE_CUIDADOS_FACIAIS in data and data[config.FILE_TYPE_CUIDADOS_FACIAIS] is not None:
        cf_data = data[config.FILE_TYPE_CUIDADOS_FACIAIS]
        df_cp = cf_data.get("CP") if isinstance(cf_data, dict) else None
        if df_cp is not None and len(df_cp) > 3:
            # Linha 3: RECEITA CUIDADOS FACIAIS + BOTIK
            # Coluna 2: % RECEITA (Share Skin)
            # Coluna 4: PERÍODO ATUAL (Receita Cuidados Faciais em R$)
            share_val = _safe_numeric(df_cp.iloc[3, 2] if df_cp.shape[1] > 2 else None)
            rec_skin_val = _safe_numeric(df_cp.iloc[3, 4] if df_cp.shape[1] > 4 else None)
            if pd.notna(share_val): summary["skin_share"] = share_val
            if pd.notna(rec_skin_val): summary["receita_skin_cp"] = rec_skin_val

    return summary


# ═══════════════════════════════════════════════════════════════════
# EXTRATORES DE DADOS DE CONSULTORAS POR MÓDULO
# ═══════════════════════════════════════════════════════════════════

def get_consultant_data_for_tab(data: Dict[str, Any], tab_type: str) -> pd.DataFrame:
    """
    Retorna o DataFrame de consultoras limpo, enriquecido e padronizado para o módulo específico.
    """
    if tab_type == "id_cliente":
        if config.FILE_TYPE_ID_CLIENTE in data and data[config.FILE_TYPE_ID_CLIENTE] is not None:
            id_data = data[config.FILE_TYPE_ID_CLIENTE]
            df_c = id_data.get("CONSULTOR") if isinstance(id_data, dict) else None
            if df_c is not None and not df_c.empty:
                df_res = df_c.copy()
                df_res.columns = [str(c).strip() for c in df_res.columns]
                df_res = df_res[~df_res.iloc[:, 0].astype(str).str.upper().isin(["PDV", "TOTAL", "NAN", ""])]
                df_res["PDV"] = df_res["PDV"].astype(str).apply(config.normalize_pdv)
                df_res["Loja"] = df_res["PDV"].apply(config.get_pdv_label)
                
                for c in ["% Atendimentos com CPF (IAF 2026)", "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN", "% BOLETOS ID CLIENTE VÁLIDOS (IAF)"]:
                    if c in df_res.columns:
                        df_res[c] = pd.to_numeric(df_res[c], errors="coerce")
                return df_res

    elif tab_type == "loja_digital":
        if config.FILE_TYPE_LOJA_DIGITAL in data and data[config.FILE_TYPE_LOJA_DIGITAL] is not None:
            ld_data = data[config.FILE_TYPE_LOJA_DIGITAL]
            df_c = ld_data.get("CONSULTOR") if isinstance(ld_data, dict) else None
            if df_c is not None and not df_c.empty:
                df_res = df_c.copy()
                df_res.columns = [str(c).strip() for c in df_res.columns]
                df_res = df_res[~df_res.iloc[:, 0].astype(str).str.upper().isin(["PDV", "TOTAL", "NAN", ""])]
                df_res["PDV"] = df_res["PDV"].astype(str).apply(config.normalize_pdv)
                df_res["Loja"] = df_res["PDV"].apply(config.get_pdv_label)
                if "% CONVERSÃO" in df_res.columns:
                    df_res["% CONVERSÃO"] = pd.to_numeric(df_res["% CONVERSÃO"], errors="coerce")
                return df_res

    elif tab_type == "fidelidade":
        if config.FILE_TYPE_FIDELIDADE in data and data[config.FILE_TYPE_FIDELIDADE] is not None:
            fid_data = data[config.FILE_TYPE_FIDELIDADE]
            df_c = fid_data.get("CONSULTOR") if isinstance(fid_data, dict) else None
            if df_c is not None and not df_c.empty:
                df_res = df_c.copy()
                df_res.columns = [str(c).strip() for c in df_res.columns]
                df_res = df_res[~df_res.iloc[:, 0].astype(str).str.upper().isin(["CONSULTOR", "TOTAL", "NAN", ""])]
                if "% Penetração Desafio Fidelidade" in df_res.columns:
                    df_res["% Penetração Desafio Fidelidade"] = pd.to_numeric(df_res["% Penetração Desafio Fidelidade"], errors="coerce")
                return df_res

    elif tab_type == "cuidados_faciais":
        if config.FILE_TYPE_CUIDADOS_FACIAIS in data and data[config.FILE_TYPE_CUIDADOS_FACIAIS] is not None:
            cf_data = data[config.FILE_TYPE_CUIDADOS_FACIAIS]
            df_c = cf_data.get("CONSULTOR") if isinstance(cf_data, dict) else None
            if df_c is not None and not df_c.empty:
                if len(df_c) > 4:
                    df_clean = df_c.iloc[4:].copy()
                    df_clean = df_clean[~df_clean.iloc[:, 0].astype(str).str.upper().isin(["CONSULTOR", "TOTAL", "NAN", "", "TIPO DE RECEITA"])]
                    
                    res_dict = {
                        "Consultor": df_clean.iloc[:, 0].astype(str).str.strip(),
                        "PDV": df_clean.iloc[:, 1].astype(str).apply(config.normalize_pdv),
                        "(%) RECEITA": pd.to_numeric(df_clean.iloc[:, 2], errors="coerce"),
                        "RECEITA (R$)": pd.to_numeric(df_clean.iloc[:, 3], errors="coerce"),
                    }
                    df_res = pd.DataFrame(res_dict)
                    df_res["Loja"] = df_res["PDV"].apply(config.get_pdv_label)
                    
                    return df_res

    elif tab_type in ["resumo", "receita"]:
        if config.FILE_TYPE_RESUMO in data and data[config.FILE_TYPE_RESUMO] is not None:
            res_data = data[config.FILE_TYPE_RESUMO]
            df_c = res_data.get("CONSULTOR") if isinstance(res_data, dict) else None
            if df_c is not None and not df_c.empty:
                df_clean = df_c[~df_c.iloc[:, 0].astype(str).str.upper().isin(["CONSULTOR", "TOTAL", "NAN", "", "TIPO DE RECEITA"])].copy()
                
                res_dict = {
                    "Consultor": df_clean.iloc[:, 0].astype(str).str.strip(),
                    "PDV": df_clean.iloc[:, 1].astype(str).apply(config.normalize_pdv),
                    "Receita": pd.to_numeric(df_clean.iloc[:, 2], errors="coerce"),
                    "Vs. Período Anterior": pd.to_numeric(df_clean.iloc[:, 3], errors="coerce"),
                    "Quantidade de Boletos": pd.to_numeric(df_clean.iloc[:, 4], errors="coerce"),
                    "Boleto Médio": pd.to_numeric(df_clean.iloc[:, 6], errors="coerce") if df_clean.shape[1] > 6 else np.nan,
                    "Itens por Boleto": pd.to_numeric(df_clean.iloc[:, 10], errors="coerce") if df_clean.shape[1] > 10 else np.nan,
                    "Penetração Boleto Turbinado": pd.to_numeric(df_clean.iloc[:, 14], errors="coerce") if df_clean.shape[1] > 14 else np.nan,
                    "Penetração Boleto Promocional": pd.to_numeric(df_clean.iloc[:, 16], errors="coerce") if df_clean.shape[1] > 16 else np.nan,
                    "Resgate Fidelidade": pd.to_numeric(df_clean.iloc[:, 26], errors="coerce") if df_clean.shape[1] > 26 else np.nan,
                }
                df_res = pd.DataFrame(res_dict)
                df_res["Loja"] = df_res["PDV"].apply(config.get_pdv_label)

                for pct_col in ["Penetração Boleto Turbinado", "Penetração Boleto Promocional", "Resgate Fidelidade"]:
                    df_res[pct_col] = df_res[pct_col].apply(lambda x: x / 100.0 if (pd.notna(x) and x > 1.0) else x)

                return df_res

    return pd.DataFrame()


def get_consultant_data(data: Dict[str, Any]) -> pd.DataFrame:
    """Wrapper para compatibilidade geral."""
    return get_consultant_data_for_tab(data, "resumo")


def get_strategic_diagnostics(df):
    import pandas as pd
    diag = {"top_3": [], "bottom_3": []}
    if df is None or df.empty or "score_global" not in df.columns: return diag
    
    df_sorted = df.sort_values(by="score_global", ascending=False).dropna(subset=["score_global"])
    top3_df = df_sorted.head(3)
    bot3_df = df_sorted.tail(3)
    
    for _, row in top3_df.iterrows():
        fortalezas = []
        if row.get("nps", 0) >= 90: fortalezas.append("NPS em Zona de Excelência")
        if row.get("meta_pef_realizado", 0) >= 1.0: fortalezas.append("Atingimento Total de Metas PEF")
        if row.get("conversao_digital", 0) >= 0.10: fortalezas.append("Alta Conversão Digital")
        if not fortalezas: fortalezas.append("Desempenho Consistente e Equilibrado")
            
        diag["top_3"].append({
            "loja": row.get("label", "Desconhecida"),
            "cidade": row.get("cidade", ""),
            "score": f"{row['score_global']:.1f}".replace('.', ','),
            "fortalezas": fortalezas[:2]
        })
        
    for _, row in bot3_df.iterrows():
        gaps = []
        planos = []
        if row.get("nps", 0) < 80: 
            gaps.append("NPS Crítico")
            planos.append("Revisar script de atendimento e abordagem na loja.")
        if row.get("tme_ajustado_segundos", 0) > 420: 
            gaps.append("TME Elevado")
            planos.append("Otimizar escala de equipe nos horários de pico.")
        if row.get("meta_pef_realizado", 1.0) < 1.0: 
            gaps.append("Abaixo da Meta PEF")
            planos.append("Focar em itens de maior valor agregado (Skin/Botik).")
        if not gaps: 
            gaps.append("Sinergia de Indicadores Média")
            planos.append("Acompanhamento diário dos resultados do painel.")
            
        diag["bottom_3"].append({
            "loja": row.get("label", "Desconhecida"),
            "cidade": row.get("cidade", ""),
            "score": f"{row['score_global']:.1f}".replace('.', ','),
            "gaps": gaps[:2],
            "plano_acao": planos[:2]
        })
        
    return diag
