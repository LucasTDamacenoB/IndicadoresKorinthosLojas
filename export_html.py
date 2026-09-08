"""
Script para processar os dados do Excel e gerar o Dashboard em arquivo único HTML.
"""
import sys
import os
import logging

from modules.data_loader import load_all_files
from modules.calculators import build_consolidated, get_cp_summary, get_consultant_data
from modules.html_generator import generate_html

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def export_dashboard():
    dados_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dados")
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Modelo.html")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dashboard_Final.html")
    
    if not os.path.exists(template_path):
        logger.error(f"Template não encontrado: {template_path}")
        return
        
    logger.info("Buscando planilhas em /Dados...")
    files = [os.path.join(dados_dir, f) for f in sorted(os.listdir(dados_dir)) if f.endswith(".xlsx")]
    
    if not files:
        logger.error("Nenhuma planilha encontrada em /Dados!")
        return
        
    logger.info(f"Processando {len(files)} arquivos...")
    data = load_all_files(files)
    
    df = build_consolidated(data)
    cp = get_cp_summary(data)
    consultant_df = get_consultant_data(data)
    
    logger.info("Gerando novo HTML do zero...")
    generate_html(df, cp, consultant_df, output_path)
    
    logger.info(f"Sucesso! Dashboard gerado em: {output_path}")

if __name__ == "__main__":
    export_dashboard()
