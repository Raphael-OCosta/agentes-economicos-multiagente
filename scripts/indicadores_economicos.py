# scripts/indicadores_economicos.py

import os
import sys
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# Carregar variáveis de ambiente (.env para uso local)
# (Aqui não há chave obrigatória, mas mantemos por consistência)
# ============================================================
load_dotenv()

# ============================================================
# Configurações de diretório e arquivo de saída
# ============================================================

# Diretório raiz do projeto (assumindo que este script está em scripts/)
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ARQUIVO_SAIDA = DATA_DIR / "indicadores_economicos.csv"

# ============================================================
# Mapeamento dos indicadores e seus códigos SGS (BACEN)
# ============================================================

INDICADORES_SGS = {
    "IPCA": 433,
    "SELIC": 432,
    "PIB": 4380,
    "DÓLAR": 1,
    "COMMODITIES": 22795,
    "IGP-M": 189,
}

# ============================================================
# Função para coletar indicadores no BACEN (SGS)
# ============================================================

def coletar_indicadores_bacen(
    indicadores: dict,
    n_ultimos: int = 20
) -> pd.DataFrame:
    """
    Coleta os últimos `n_ultimos` registros de cada série do SGS (BACEN)
    e retorna um DataFrame consolidado com as colunas:
    [data, valor, indicador, data_coleta].
    """
    todos_dados = []

    for nome, codigo in indicadores.items():
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
            f"/dados/ultimos/{n_ultimos}?formato=json"
        )

        print(f"🔄 Coletando indicador '{nome}' (código {codigo}) do BACEN...")
        try:
            response = requests.get(url, timeout=30)
        except Exception as e:
            print(f"❌ Erro de conexão ao buscar {nome} (código {codigo}): {e}")
            continue

        if response.status_code != 200:
            print(
                f"❌ Erro HTTP ao buscar {nome} (código {codigo}). "
                f"Status: {response.status_code}"
            )
            continue

        try:
            dados = response.json()
        except Exception as e:
            print(f"❌ Erro ao decodificar JSON para {nome}: {e}")
            continue

        if not dados:
            print(f"ℹ️ Nenhum dado retornado para {nome}.")
            continue

        df = pd.DataFrame(dados)

        # Algumas séries vêm com 'valor' em formato string com vírgula
        if "valor" not in df.columns or "data" not in df.columns:
            print(f"⚠️ Estrutura inesperada ao buscar {nome}: {df.columns.tolist()}")
            continue

        df["valor"] = (
            df["valor"]
            .astype(str)
            .str.replace(",", ".", regex=False)
        )

        # Converter para float, descartando valores que não convertem
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df.dropna(subset=["valor"], inplace=True)

        if df.empty:
            print(f"ℹ️ Após conversão, não há valores numéricos válidos para {nome}.")
            continue

        df["indicador"] = nome
        df["data_coleta"] = datetime.now().date()

        todos_dados.append(df)

    if not todos_dados:
        print("⚠️ Nenhum indicador pôde ser coletado com sucesso.")
        return pd.DataFrame(columns=["data", "valor", "indicador", "data_coleta"])

    df_final = pd.concat(todos_dados, ignore_index=True)
    df_final.rename(columns={"data": "data", "valor": "valor"}, inplace=True)

    return df_final


# ============================================================
# Execução principal
# ============================================================

def main():
    df_indicadores = coletar_indicadores_bacen(INDICADORES_SGS, n_ultimos=20)

    if df_indicadores.empty:
        print("ℹ️ Nenhum dado consolidado para salvar em CSV.")
        # Não consideramos isso um erro fatal para CI/CD, então não damos sys.exit(1)
        return

    try:
        df_indicadores.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")
        print(f"✅ Arquivo '{ARQUIVO_SAIDA}' salvo com sucesso ({len(df_indicadores)} linhas).")
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo '{ARQUIVO_SAIDA}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
