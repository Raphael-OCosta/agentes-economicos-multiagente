# scripts/acoes.py

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# Carregar variáveis de ambiente (.env para uso local)
# ============================================================
load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not API_KEY:
    print("❌ ERRO: Variável de ambiente ALPHA_VANTAGE_API_KEY não encontrada.")
    print("   Defina a chave no .env (para uso local) ou nos Secrets (GitHub Actions).")
    sys.exit(1)

# ============================================================
# Configuração dos ativos e caminhos
# ============================================================

# Top 10 ações da B3 por volume - você pode ajustar essa lista depois
TOP_10_ACOES = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3",
    "BBAS3", "B3SA3", "WEGE3", "RENT3", "MGLU3"
]

# Diretório raiz do projeto (assumindo que o script está em scripts/)
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ARQUIVO_SAIDA = DATA_DIR / "top_10_acoes.csv"

# ============================================================
# Função de coleta de uma ação na Alpha Vantage
# ============================================================

def buscar_dados_acao_alpha_vantage(
    ticker_b3: str,
    api_key: str,
    num_registros: int = 20,
) -> pd.DataFrame | None:
    """
    Busca dados diários de um ticker da B3 na Alpha Vantage,
    retornando apenas os últimos `num_registros` registros mais recentes.
    """
    ticker = f"{ticker_b3}.SA"
    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&outputsize=compact"
    )

    print(f"🔄 Coletando dados de {ticker_b3} na Alpha Vantage...")
    response = requests.get(url, timeout=30)

    # Tratamento de erros HTTP
    if response.status_code != 200:
        if response.status_code == 503:
            print(f"[{ticker_b3}] Servidor Alpha Vantage indisponível (503). Aguardando 30s e tentando de novo...")
            time.sleep(30)
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"[{ticker_b3}] Erro {response.status_code} após nova tentativa.")
                return None
        else:
            print(f"[{ticker_b3}] Erro HTTP {response.status_code} ao acessar Alpha Vantage.")
            return None

    data = response.json()

    # Mensagens de limite de API ou erros genéricos
    if "Note" in data or "Information" in data:
        msg = data.get("Note") or data.get("Information") or "Mensagem de limite ou erro genérico da API."
        print(f"[{ticker_b3}] Aviso da API Alpha Vantage: {msg}")
        return None

    if "Time Series (Daily)" not in data:
        print(f"[{ticker_b3}] Resposta sem chave 'Time Series (Daily)'. Resposta bruta: {data}")
        return None

    # Montar DataFrame
    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    df.columns = ["abertura", "alta", "baixa", "fechamento", "volume"]
    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index(ascending=True)

    df["ticker"] = ticker_b3

    # Selecionar apenas os últimos N registros (mais recentes)
    df = df.tail(num_registros)

    return df


# ============================================================
# Execução principal
# ============================================================

def main():
    df_total = pd.DataFrame()

    for ativo in TOP_10_ACOES:
        try:
            df = buscar_dados_acao_alpha_vantage(ativo, API_KEY, num_registros=20)

            if df is not None and not df.empty:
                df_total = pd.concat([df_total, df])
                print(f"✅ {ativo} coletado com {len(df)} linhas.")
            elif df is not None and df.empty:
                print(f"⚠️ {ativo} retornou DataFrame vazio (após filtros).")
            else:
                print(f"⚠️ Nenhum dado retornado para {ativo}.")

            # Respeitar limite da API gratuita (5 chamadas/minuto → ~12s por chamada).
            # Usando 15s para ficar folgado.
            time.sleep(15)

        except Exception as e:
            print(f"❌ Erro ao processar {ativo}: {e}")

    if not df_total.empty:
        df_total.to_csv(ARQUIVO_SAIDA, index=True, encoding="utf-8-sig")
        print(f"📁 Arquivo final salvo em: {ARQUIVO_SAIDA} ({len(df_total)} linhas).")
    else:
        print("ℹ️ Nenhum dado foi coletado. Arquivo CSV não foi gerado.")


if __name__ == "__main__":
    main()

