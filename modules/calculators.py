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
    Se houver dados consolidados pré-calculados em _consultant_data_override, utiliza-os diretamente.
    """
    if data and "_consultant_data_override" in data and tab_type in data["_consultant_data_override"]:
        return data["_consultant_data_override"][tab_type].copy()

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


# ═══════════════════════════════════════════════════════════════════
# COMPARATIVO MÊS ATUAL vs MÊS ANTERIOR (DELTAS)
# ═══════════════════════════════════════════════════════════════════

# Métricas onde MENOR é MELHOR (delta negativo = melhoria)
_INVERTED_METRICS = {"tme_medio", "id_cliente_2min"}

# Mapeamento de chaves do cp_summary para nomes legíveis
_CP_DELTA_KEYS = [
    "nps_geral", "tme_medio", "conversao_digital",
    "id_cliente_cpf", "id_cliente_2min", "desafio_fidelidade",
    "skin_share", "receita_total_gmv", "meta_pef_atingimento",
    "ticket_medio", "itens_boleto", "boleto_turbinado",
    "boleto_promocional", "resgate_fidelidade", "conversao_fluxo",
]

# Colunas do DataFrame consolidado para comparação por PDV
_PDV_DELTA_COLS = [
    "nps", "receita", "meta_pef_realizado", "tme_ajustado_segundos",
    "conversao_digital", "id_cliente_cpf", "id_cliente_2min",
    "penetracao_desafio_fidelidade", "cuidados_faciais",
    "itens_boleto", "boletos_turbinados", "boletos_promocionais",
    "resgate_fidelidade", "conversao_acao_fluxo", "score_global",
]

# Colunas de PDV onde menor é melhor
_PDV_INVERTED = {"tme_ajustado_segundos", "id_cliente_2min"}


def _safe_delta(atual, anterior):
    """Calcula diferença numérica segura entre dois valores."""
    if pd.isna(atual) or pd.isna(anterior) or atual is None or anterior is None:
        return np.nan
    try:
        return float(atual) - float(anterior)
    except (ValueError, TypeError):
        return np.nan


def compute_deltas(
    df_atual: pd.DataFrame,
    df_anterior: Optional[pd.DataFrame],
    cp_atual: dict,
    cp_anterior: Optional[dict],
) -> tuple:
    """
    Calcula as variações (deltas) entre mês atual e mês anterior.
    
    Retorna:
        deltas_cp: dict com chave = nome do KPI, valor = float (diferença)
        deltas_pdv: DataFrame indexado por PDV com colunas delta_<metrica>
    """
    # --- 1. Deltas CP (nível franquia) ---
    deltas_cp = {}
    if cp_anterior:
        for key in _CP_DELTA_KEYS:
            v_atual = cp_atual.get(key)
            v_ant = cp_anterior.get(key)
            
            # TME é string (HH:MM:SS) — converter para segundos antes de comparar
            if key == "tme_medio":
                v_atual = _time_str_to_seconds(v_atual) if v_atual else 0
                v_ant = _time_str_to_seconds(v_ant) if v_ant else 0
            
            delta = _safe_delta(v_atual, v_ant)
            if pd.notna(delta):
                deltas_cp[key] = delta

    # --- 2. Deltas PDV (nível loja) ---
    deltas_pdv = pd.DataFrame()
    if df_anterior is not None and not df_anterior.empty and not df_atual.empty:
        # Merge pelo código do PDV
        df_ant_idx = df_anterior.set_index("pdv") if "pdv" in df_anterior.columns else df_anterior
        df_atu_idx = df_atual.set_index("pdv") if "pdv" in df_atual.columns else df_atual
        
        delta_rows = {}
        for pdv in df_atu_idx.index:
            if pdv not in df_ant_idx.index:
                continue
            row_deltas = {}
            for col in _PDV_DELTA_COLS:
                if col in df_atu_idx.columns and col in df_ant_idx.columns:
                    row_deltas[f"delta_{col}"] = _safe_delta(
                        df_atu_idx.loc[pdv, col],
                        df_ant_idx.loc[pdv, col]
                    )
            delta_rows[pdv] = row_deltas
        
        if delta_rows:
            deltas_pdv = pd.DataFrame.from_dict(delta_rows, orient="index")
            deltas_pdv.index.name = "pdv"
            deltas_pdv.reset_index(inplace=True)

    return deltas_cp, deltas_pdv


def is_inverted_metric(key: str) -> bool:
    """Retorna True se a métrica é invertida (menor = melhor)."""
    return key in _INVERTED_METRICS or key in _PDV_INVERTED


def format_delta(delta_val, fmt_type="pct", inverted=False, as_html=True):
    """
    Formata um delta para exibição com seta colorida.
    
    Args:
        delta_val: valor numérico da diferença
        fmt_type: "pct" (percentual), "pts" (pontos), "time" (segundos), "brl" (reais), "dec" (decimal), "int" (inteiro)
        inverted: True se menor é melhor (ex: TME)
        as_html: Se True, retorna <span> estilizado com cor; se False, retorna apenas texto com seta
    
    Returns:
        String formatada (HTML ou texto)
    """
    if pd.isna(delta_val) or delta_val is None:
        return ""
    
    try:
        d = float(delta_val)
    except (ValueError, TypeError):
        return ""
    
    if abs(d) < 0.0001:
        return '<span style="color: #64748B; font-size: 12px;">➡️ Estável</span>' if as_html else "➡️ Estável"
    
    # Determinar se é melhoria ou piora
    is_improvement = (d < 0) if inverted else (d > 0)
    
    arrow = "🔼" if d > 0 else "🔽"
    color = "#059669" if is_improvement else "#DC2626"
    
    # Formatação do valor
    sign = "+" if d > 0 else ""
    if fmt_type == "pct":
        txt = f"{sign}{d * 100:.2f}%".replace('.', ',')
    elif fmt_type == "pts":
        txt = f"{sign}{d:.2f} pts".replace('.', ',')
    elif fmt_type == "time":
        secs = abs(int(d))
        m, s = divmod(secs, 60)
        txt = f"{sign}{'-' if d < 0 else ''}{m:02d}:{s:02d}"
    elif fmt_type == "brl":
        txt = f"{sign}R$ {abs(d):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if d < 0:
            txt = f"-R$ {abs(d):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif fmt_type == "dec":
        txt = f"{sign}{d:.2f}".replace('.', ',')
    elif fmt_type == "int":
        txt = f"{sign}{int(d):,}".replace(',', '.')
    else:
        txt = f"{sign}{d:.4f}".replace('.', ',')
    
    if as_html:
        return f'<span style="color: {color}; font-size: 12px; font-weight: 700;">{arrow} {txt}</span>'
    return f"{arrow} {txt}"


# ═══════════════════════════════════════════════════════════════════
# CONSOLIDAÇÃO MULTI-MESES (VISÃO ACUMULADA)
# ═══════════════════════════════════════════════════════════════════

def aggregate_consultants(months_data_list: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """Consolida os dados de consultoras de todos os módulos para múltiplos meses."""
    overrides = {}

    def _w_avg(s: pd.Series, w: pd.Series) -> float:
        valid = s.notna() & (w > 0)
        if valid.any():
            return float((s[valid] * w[valid]).sum() / w[valid].sum())
        return np.nan

    # 1. Resumo e Receita
    cdfs_res = [get_consultant_data_for_tab(d, "resumo") for d in months_data_list]
    cdfs_res = [c for c in cdfs_res if not c.empty]
    if cdfs_res:
        comb = pd.concat(cdfs_res, ignore_index=True)
        comb["Consultor"] = comb["Consultor"].astype(str).str.strip()
        rows = []
        for (c, pdv, loja), g in comb.groupby(["Consultor", "PDV", "Loja"]):
            tot_rec = g["Receita"].sum()
            tot_bol = g["Quantidade de Boletos"].sum()
            w = g["Quantidade de Boletos"].fillna(0)
            rows.append({
                "Consultor": c,
                "PDV": pdv,
                "Loja": loja,
                "Receita": tot_rec,
                "Vs. Período Anterior": np.nan,
                "Quantidade de Boletos": tot_bol,
                "Boleto Médio": tot_rec / tot_bol if tot_bol > 0 else np.nan,
                "Itens por Boleto": _w_avg(g["Itens por Boleto"], w),
                "Penetração Boleto Turbinado": _w_avg(g["Penetração Boleto Turbinado"], w),
                "Penetração Boleto Promocional": _w_avg(g["Penetração Boleto Promocional"], w),
                "Resgate Fidelidade": _w_avg(g["Resgate Fidelidade"], w),
            })
        df_res = pd.DataFrame(rows).sort_values("Receita", ascending=False)
        overrides["resumo"] = df_res
        overrides["receita"] = df_res.copy()

    # 2. Loja Digital
    cdfs_ld = [get_consultant_data_for_tab(d, "loja_digital") for d in months_data_list]
    cdfs_ld = [c for c in cdfs_ld if not c.empty]
    if cdfs_ld:
        comb_ld = pd.concat(cdfs_ld, ignore_index=True)
        comb_ld["CONSULTOR(A)"] = comb_ld["CONSULTOR(A)"].astype(str).str.strip()
        rows = []
        for (c, pdv, loja), g in comb_ld.groupby(["CONSULTOR(A)", "PDV", "Loja"]):
            atend = g["CLIENTES ATENDIDOS"].sum()
            conv = g["CLIENTES CONVERTIDOS"].sum()
            rec = g["RECEITA (R$)"].sum() if "RECEITA (R$)" in g.columns else np.nan
            bm = rec / conv if (pd.notna(rec) and conv > 0) else np.nan
            tme_secs = [_time_str_to_seconds(t) for t in g["TME AJUSTADO"]]
            w_tme = g["CLIENTES ATENDIDOS"].fillna(0)
            avg_tme_sec = _w_avg(pd.Series(tme_secs), w_tme)
            tme_str = _seconds_to_time_str(int(round(avg_tme_sec))) if pd.notna(avg_tme_sec) else "00:00"
            rows.append({
                "CONSULTOR(A)": c,
                "PDV": pdv,
                "Loja": loja,
                "CLIENTES ATENDIDOS": atend,
                "TME AJUSTADO": tme_str,
                "CLIENTES CONVERTIDOS": conv,
                "% CONVERSÃO": conv / atend if atend > 0 else np.nan,
                "RECEITA (R$)": rec,
                "BOLETO MEDIO (R$)": bm,
            })
        overrides["loja_digital"] = pd.DataFrame(rows).sort_values("CLIENTES ATENDIDOS", ascending=False)

    # 3. ID Cliente
    cdfs_id = [get_consultant_data_for_tab(d, "id_cliente") for d in months_data_list]
    cdfs_id = [c for c in cdfs_id if not c.empty]
    if cdfs_id:
        comb_id = pd.concat(cdfs_id, ignore_index=True)
        comb_id["CONSULTOR"] = comb_id["CONSULTOR"].astype(str).str.strip()
        rows = []
        for (pdv, c, loja), g in comb_id.groupby(["PDV", "CONSULTOR", "Loja"]):
            atend_id = g["ATENDIMENTOS NO ID CLIENTE"].sum()
            atend_cpf = g["ATENDIMENTOS COM CPF (COM E SEM COMPRA)"].sum()
            atend_ind = g["ATENDIMENTOS USO INDEVIDO"].sum()
            tot_bol = g["TOTAL BOLETOS"].sum()
            bol_id = g["BOLETOS ID"].sum()
            bol_ind = g["BOLETOS ID CLIENTE USO INDEVIDO"].sum()
            bol_2m = g["BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN"].sum()
            w_bol = g["TOTAL BOLETOS"].fillna(0)
            tma_secs = [_time_str_to_seconds(t) for t in g["TEMPO MÉDIO DE ATENDIMENTO (TMA CPF)"]]
            w_atend = g["ATENDIMENTOS NO ID CLIENTE"].fillna(0)
            avg_tma_sec = _w_avg(pd.Series(tma_secs), w_atend)
            tma_str = _seconds_to_time_str(int(round(avg_tma_sec))) if pd.notna(avg_tma_sec) else "00:00"
            rows.append({
                "PDV": pdv,
                "CONSULTOR": c,
                "Loja": loja,
                "ATENDIMENTOS NO ID CLIENTE": atend_id,
                "ATENDIMENTOS COM CPF (COM E SEM COMPRA)": atend_cpf,
                "ATENDIMENTOS USO INDEVIDO": atend_ind,
                "% Atendimentos com CPF (IAF 2026)": atend_cpf / atend_id if atend_id > 0 else np.nan,
                "% ATENDIMENTOS USO INDEVIDO": atend_ind / atend_id if atend_id > 0 else np.nan,
                "TEMPO MÉDIO DE ATENDIMENTO (TMA CPF)": tma_str,
                "TOTAL BOLETOS": tot_bol,
                "BOLETOS ID": bol_id,
                "BOLETOS ID CLIENTE USO INDEVIDO": bol_ind,
                "BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN": bol_2m,
                "% BOLETOS ID CLIENTE VÁLIDOS (IAF)": _w_avg(g["% BOLETOS ID CLIENTE VÁLIDOS (IAF)"], w_bol),
                "% BOLETOS ID CLIENTE USO INDEVIDO": bol_ind / tot_bol if tot_bol > 0 else np.nan,
                "% BOLETOS ID CLIENTE TMA CPF ABAIXO DE 2MIN": bol_2m / tot_bol if tot_bol > 0 else np.nan,
            })
        overrides["id_cliente"] = pd.DataFrame(rows).sort_values("TOTAL BOLETOS", ascending=False)

    # 4. Fidelidade
    cdfs_fid = [get_consultant_data_for_tab(d, "fidelidade") for d in months_data_list]
    cdfs_fid = [c for c in cdfs_fid if not c.empty]
    if cdfs_fid:
        comb_fid = pd.concat(cdfs_fid, ignore_index=True)
        comb_fid["Consultor"] = comb_fid["Consultor"].astype(str).str.strip()
        rows = []
        for c, g in comb_fid.groupby("Consultor"):
            des = g["Qnt de boleto com desafios concluídos"].sum()
            fid = g["Qnt de boletos Fidelidade"].sum()
            rows.append({
                "Consultor": c,
                "Qnt de boleto com desafios concluídos": des,
                "Qnt de boletos Fidelidade": fid,
                "% Penetração Desafio Fidelidade": des / fid if fid > 0 else np.nan,
            })
        overrides["fidelidade"] = pd.DataFrame(rows).sort_values("Qnt de boletos Fidelidade", ascending=False)

    # 5. Cuidados Faciais
    cdfs_cf = [get_consultant_data_for_tab(d, "cuidados_faciais") for d in months_data_list]
    cdfs_cf = [c for c in cdfs_cf if not c.empty]
    if cdfs_cf:
        comb_cf = pd.concat(cdfs_cf, ignore_index=True)
        comb_cf["Consultor"] = comb_cf["Consultor"].astype(str).str.strip()
        rows = []
        for (c, pdv, loja), g in comb_cf.groupby(["Consultor", "PDV", "Loja"]):
            rec_skin = g["RECEITA (R$)"].sum()
            pct_rec = g["(%) RECEITA"].mean()
            rows.append({
                "Consultor": c,
                "PDV": pdv,
                "Loja": loja,
                "RECEITA (R$)": rec_skin,
                "(%) RECEITA": pct_rec,
            })
        overrides["cuidados_faciais"] = pd.DataFrame(rows).sort_values("RECEITA (R$)", ascending=False)

    return overrides


def aggregate_months_data(
    months_data_list: List[Dict[str, Any]],
    month_labels: Optional[List[str]] = None,
) -> tuple:
    """
    Consolida múltiplos meses de dados em uma visão acumulada completa.
    
    Retorna:
        df_acum: DataFrame consolidado dos 9 PDVs com taxas recalculadas e score_global reavaliado
        cp_acum: dict de indicadores consolidados da franquia CP Korinthos
        data_acum: dict com _consultant_data_override e metadados de acumulado
    """
    if not months_data_list:
        return pd.DataFrame(), {}, {}

    if len(months_data_list) == 1:
        d = months_data_list[0]
        return build_consolidated(d), get_cp_summary(d), d

    # 1. Obter DataFrames consolidados de cada mês
    dfs = [build_consolidated(d) for d in months_data_list]
    cps = [get_cp_summary(d) for d in months_data_list]

    # 2. Construir tabela mestre acumulada para os 9 PDVs
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
    df_acum = pd.DataFrame(rows).set_index("pdv")

    # Colunas de soma direta
    sum_cols = [
        "receita", "receita_loja", "receita_cr", "meta_pef_loja", "meta_pef_total",
        "volume_boletos", "servicos_loja", "clique_retire", "receita_skin", "nps_registros",
        "boletos_desafio_qtd", "boletos_fidelidade_qtd",
        "clientes_encaminhados", "clientes_atendidos", "clientes_convertidos",
    ]

    for pdv in config.TARGET_PDVS:
        pdv_rows = [df.set_index("pdv").loc[pdv] for df in dfs if pdv in df.set_index("pdv").index]
        if not pdv_rows:
            continue

        for c in sum_cols:
            vals = [r[c] for r in pdv_rows if c in r and pd.notna(r[c])]
            df_acum.loc[pdv, c] = sum(vals) if vals else np.nan

        rec = df_acum.loc[pdv, "receita"]
        meta_tot = df_acum.loc[pdv, "meta_pef_total"]
        vol_bol = df_acum.loc[pdv, "volume_boletos"]
        cli_conv = df_acum.loc[pdv, "clientes_convertidos"]
        cli_atend = df_acum.loc[pdv, "clientes_atendidos"]
        bol_des = df_acum.loc[pdv, "boletos_desafio_qtd"]
        bol_fid = df_acum.loc[pdv, "boletos_fidelidade_qtd"]
        rec_skin = df_acum.loc[pdv, "receita_skin"]

        df_acum.loc[pdv, "gap_pef"] = meta_tot - rec if (pd.notna(meta_tot) and pd.notna(rec)) else np.nan
        df_acum.loc[pdv, "meta_pef_realizado"] = (rec / meta_tot) if (pd.notna(rec) and pd.notna(meta_tot) and meta_tot > 0) else np.nan
        df_acum.loc[pdv, "ticket_medio"] = (rec / vol_bol) if (pd.notna(rec) and pd.notna(vol_bol) and vol_bol > 0) else np.nan
        df_acum.loc[pdv, "conversao_digital"] = (cli_conv / cli_atend) if (pd.notna(cli_conv) and pd.notna(cli_atend) and cli_atend > 0) else np.nan
        df_acum.loc[pdv, "penetracao_desafio_fidelidade"] = (bol_des / bol_fid) if (pd.notna(bol_des) and pd.notna(bol_fid) and bol_fid > 0) else np.nan
        df_acum.loc[pdv, "cuidados_faciais"] = (rec_skin / rec) if (pd.notna(rec_skin) and pd.notna(rec) and rec > 0) else np.nan

        # Médias ponderadas por volume de boletos
        def _w_avg_pdv(col, w_col):
            vals = []
            weights = []
            for r in pdv_rows:
                if col in r and w_col in r and pd.notna(r[col]) and pd.notna(r[w_col]) and r[w_col] > 0:
                    vals.append(float(r[col]))
                    weights.append(float(r[w_col]))
            if weights and sum(weights) > 0:
                return sum(v * w for v, w in zip(vals, weights)) / sum(weights)
            fallback = [float(r[col]) for r in pdv_rows if col in r and pd.notna(r[col])]
            return np.mean(fallback) if fallback else np.nan

        for c in [
            "itens_boleto", "boletos_turbinados", "boletos_promocionais",
            "share_alavancas", "penetracao_mobshop", "boletos_1",
            "penetracao_fidelidade", "resgate_fidelidade", "conversao_acao_fluxo",
            "id_cliente_cpf", "id_cliente_validos", "id_cliente_2min"
        ]:
            df_acum.loc[pdv, c] = _w_avg_pdv(c, "volume_boletos")

        # Preço Médio
        ib = df_acum.loc[pdv, "itens_boleto"]
        if pd.notna(rec) and pd.notna(vol_bol) and pd.notna(ib) and (vol_bol * ib) > 0:
            df_acum.loc[pdv, "preco_medio"] = rec / (vol_bol * ib)
        else:
            df_acum.loc[pdv, "preco_medio"] = _w_avg_pdv("preco_medio", "volume_boletos")

        # NPS ponderado por registros
        df_acum.loc[pdv, "nps"] = _w_avg_pdv("nps", "nps_registros")

        # TME ponderado por atendimentos
        tme_secs = _w_avg_pdv("tme_ajustado_segundos", "clientes_atendidos")
        df_acum.loc[pdv, "tme_ajustado_segundos"] = tme_secs
        df_acum.loc[pdv, "tme_ajustado"] = _seconds_to_time_str(int(round(tme_secs))) if pd.notna(tme_secs) else "00:00"

        # Fallback cuidados faciais
        if pd.isna(df_acum.loc[pdv, "cuidados_faciais"]):
            df_acum.loc[pdv, "cuidados_faciais"] = _w_avg_pdv("cuidados_faciais", "receita")

    # Representatividade
    tot_rec = df_acum["receita"].sum()
    if tot_rec > 0:
        df_acum["representatividade"] = df_acum["receita"] / tot_rec

    # Recalcular Score Global (0 a 12)
    for idx, row in df_acum.iterrows():
        score = 0
        if pd.notna(row.get("meta_pef_realizado")) and row["meta_pef_realizado"] >= 1.00: score += 1
        if pd.notna(row.get("nps")) and row["nps"] >= 90.9: score += 1
        tme_s = row.get("tme_ajustado_segundos")
        if pd.notna(tme_s) and tme_s > 0 and tme_s <= 420: score += 1
        conv_v = row.get("conversao_digital", row.get("conversao_acao_fluxo"))
        if pd.notna(conv_v) and conv_v >= 0.10: score += 1
        cpf_v = row.get("id_cliente_cpf")
        if pd.notna(cpf_v) and cpf_v >= 1.15: score += 1
        b2m_v = row.get("id_cliente_2min")
        if pd.notna(b2m_v) and b2m_v <= 0.30: score += 1
        if pd.notna(row.get("penetracao_desafio_fidelidade")) and row["penetracao_desafio_fidelidade"] >= 0.20: score += 1
        if pd.notna(row.get("cuidados_faciais")) and row["cuidados_faciais"] >= 0.021: score += 1
        if pd.notna(row.get("itens_boleto")) and row["itens_boleto"] >= 2.50: score += 1
        if pd.notna(row.get("boletos_turbinados")) and row["boletos_turbinados"] >= 0.31: score += 1
        if pd.notna(row.get("boletos_promocionais")) and row["boletos_promocionais"] >= 0.33: score += 1
        if pd.notna(row.get("resgate_fidelidade")) and row["resgate_fidelidade"] >= 0.52: score += 1
        df_acum.loc[idx, "score_global"] = int(score)

    df_acum.reset_index(inplace=True)

    # 3. Consolidar CP Summary
    periodo_label = " + ".join(month_labels) if month_labels else f"{len(months_data_list)} Meses"
    cp_acum = {
        "periodo": f"Acumulado ({periodo_label})",
        "receita_total_gmv": df_acum["receita"].sum(),
        "meta_pef_total": df_acum["meta_pef_total"].sum(),
        "receita_loja_cp": df_acum["receita_loja"].sum(),
        "meta_pef_loja_cp": df_acum["meta_pef_loja"].sum(),
        "receita_cr_cp": df_acum["receita_cr"].sum(),
        "volume_boletos": int(df_acum["volume_boletos"].sum()) if pd.notna(df_acum["volume_boletos"].sum()) else 0,
        "receita_skin_cp": df_acum["receita_skin"].sum(),
    }
    cp_acum["meta_pef_atingimento"] = (cp_acum["receita_total_gmv"] / cp_acum["meta_pef_total"]) if (pd.notna(cp_acum["meta_pef_total"]) and cp_acum["meta_pef_total"] > 0) else np.nan
    cp_acum["ticket_medio"] = (cp_acum["receita_total_gmv"] / cp_acum["volume_boletos"]) if (pd.notna(cp_acum["volume_boletos"]) and cp_acum["volume_boletos"] > 0) else np.nan
    cp_acum["skin_share"] = (cp_acum["receita_skin_cp"] / cp_acum["receita_total_gmv"]) if (pd.notna(cp_acum["receita_total_gmv"]) and cp_acum["receita_total_gmv"] > 0) else np.nan

    month_vols = [cp.get("volume_boletos", 0) or 0 for cp in cps]
    tot_month_vols = sum(month_vols)

    def _cp_w_avg(key):
        if tot_month_vols > 0:
            valid_pairs = [(cp[key], v) for cp, v in zip(cps, month_vols) if key in cp and pd.notna(cp[key]) and v > 0]
            if valid_pairs:
                return float(sum(val * w for val, w in valid_pairs) / sum(w for _, w in valid_pairs))
        vals = [cp[key] for cp in cps if key in cp and pd.notna(cp[key])]
        return float(np.mean(vals)) if vals else np.nan

    for k in [
        "itens_boleto", "share_alavancas", "boletos_1", "boleto_turbinado",
        "boleto_promocional", "penetracao_mobshop", "penetracao_fidelidade",
        "resgate_fidelidade", "conversao_fluxo", "id_cliente_cpf", "id_cliente_2min"
    ]:
        cp_acum[k] = _cp_w_avg(k)

    if pd.notna(cp_acum["receita_total_gmv"]) and pd.notna(cp_acum["volume_boletos"]) and pd.notna(cp_acum["itens_boleto"]) and (cp_acum["volume_boletos"] * cp_acum["itens_boleto"]) > 0:
        cp_acum["preco_medio"] = cp_acum["receita_total_gmv"] / (cp_acum["volume_boletos"] * cp_acum["itens_boleto"])
    else:
        cp_acum["preco_medio"] = _cp_w_avg("preco_medio")

    tot_bol_des = df_acum["boletos_desafio_qtd"].sum()
    tot_bol_fid = df_acum["boletos_fidelidade_qtd"].sum()
    if pd.notna(tot_bol_fid) and tot_bol_fid > 0:
        cp_acum["desafio_fidelidade"] = tot_bol_des / tot_bol_fid
    else:
        cp_acum["desafio_fidelidade"] = _cp_w_avg("desafio_fidelidade")

    tot_nps_reg = df_acum["nps_registros"].sum()
    if pd.notna(tot_nps_reg) and tot_nps_reg > 0:
        cp_acum["nps_geral"] = float((df_acum["nps"] * df_acum["nps_registros"]).sum() / tot_nps_reg)
    else:
        cp_acum["nps_geral"] = _cp_w_avg("nps_geral")

    cp_acum["nps_objetivo"] = 86.1
    cp_acum["nps_variacao"] = "Acumulado no Período Selecionado"
    cp_acum["nps_variacao_num"] = np.nan
    cp_acum["nps_variacao_str"] = ""
    cp_acum["benchmark_desc"] = ""

    tot_atend = df_acum["clientes_atendidos"].sum()
    if pd.notna(tot_atend) and tot_atend > 0:
        tme_cp_secs = (df_acum["tme_ajustado_segundos"] * df_acum["clientes_atendidos"]).sum() / tot_atend
        cp_acum["tme_medio"] = _seconds_to_time_str(int(round(tme_cp_secs)))
    else:
        secs_list = [_time_str_to_seconds(cp.get("tme_medio", "")) for cp in cps]
        valid_secs = [s for s in secs_list if s > 0]
        cp_acum["tme_medio"] = _seconds_to_time_str(int(round(np.mean(valid_secs)))) if valid_secs else "00:00:00"

    tot_conv = df_acum["clientes_convertidos"].sum()
    if pd.notna(tot_atend) and tot_atend > 0:
        cp_acum["conversao_digital"] = tot_conv / tot_atend
    else:
        cp_acum["conversao_digital"] = _cp_w_avg("conversao_digital")

    # 4. Consolidar Consultoras
    consultant_overrides = aggregate_consultants(months_data_list)

    # 5. Criar data_acum
    data_acum = {}
    for d in reversed(months_data_list):
        for k, v in d.items():
            if k not in data_acum:
                data_acum[k] = v

    data_acum["_is_acumulado"] = True
    data_acum["_periodo"] = f"Acumulado ({periodo_label})"
    data_acum["_periodo_anterior"] = ""
    data_acum["_meses_selecionados"] = month_labels or []
    data_acum["_deltas_cp"] = {}
    data_acum["_deltas_pdv"] = pd.DataFrame()
    data_acum["_consultant_data_override"] = consultant_overrides
    data_acum["_log"] = [f"📊 Acumulado: {len(months_data_list)} competências ({periodo_label})"]

    return df_acum, cp_acum, data_acum
