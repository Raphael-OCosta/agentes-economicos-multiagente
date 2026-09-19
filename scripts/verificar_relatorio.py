"""
Verificador de lastro factual.
Testa se as afirmacoes numericas e as fontes citadas no relatorio
existem nos arquivos de entrada. Nao julga o merito da analise --
apenas se ha origem para o que foi afirmado.
"""
import re
import sys
from pathlib import Path

import pandas as pd

RELATORIO = Path("data/relatorio_indicacao_acoes.md")
FONTES = [
    "data/indicadores_economicos.csv",
    "data/top_10_acoes.csv",
    "data/noticias_investimentos.csv",
]
# dominios que o pipeline realmente acessa
FONTES_REAIS = ["cnn", "g1", "infomoney", "exame", "banco central",
                "bacen", "alpha vantage", "b3"]


def carregar_corpus():
    texto, numeros = [], set()
    for caminho in FONTES:
        p = Path(caminho)
        if not p.exists():
            print(f"[AVISO] fonte ausente: {caminho}")
            continue
        df = pd.read_csv(p)
        texto.append(df.to_string())
        for col in df.columns:
            serie = pd.to_numeric(df[col], errors="coerce").dropna()
            numeros.update(round(float(v), 2) for v in serie)
    return " ".join(texto).lower(), numeros


def numero_existe(valor, numeros, tol=0.05):
    return any(abs(valor - v) <= tol for v in numeros)


def main():
    if not RELATORIO.exists():
        sys.exit("relatorio nao encontrado -- rode agentes_economicos.py antes")

    texto = RELATORIO.read_text(encoding="utf-8")
    corpus, numeros = carregar_corpus()

    # ---------- 1. percentuais citados ----------
    percentuais = sorted({p.replace(",", ".")
                          for p in re.findall(r"(\d+[,.]\d+)\s*%", texto)})
    sem_lastro_pct = [p for p in percentuais
                      if not numero_existe(float(p), numeros)]

    # ---------- 2. valores em reais ----------
    reais = sorted({m for m in re.findall(
        r"R\$\s*[\d.,]+\s*(?:bilh\w*|milh\w*)?", texto)})

    # ---------- 3. entidades citadas ----------
    entidades = sorted({e for e in re.findall(
        r"\b(Petrobras|Vale|Ita[uú]|Bradesco|WEG|Ambev|Magalu|Localiza|B3)\b",
        texto)})
    sem_lastro_ent = [e for e in entidades if e.lower() not in corpus]

    # ---------- 4. fontes fabricadas ----------
    trecho = texto.lower().split("fontes de dados")[-1]
    citadas = re.findall(
        r"\b(bloomberg|reuters|valor econ[oô]mico|forbes|financial times|"
        r"the economist|cnn|g1|infomoney|exame|focus|ibge)\b", trecho)
    fabricadas = sorted({c for c in set(citadas)
                         if not any(r in c for r in FONTES_REAIS)})

    # ---------- relatorio ----------
    print("=" * 62)
    print("VERIFICACAO DE LASTRO FACTUAL")
    print("=" * 62)
    print(f"percentuais citados       : {len(percentuais)}")
    print(f"  sem lastro nos CSVs     : {len(sem_lastro_pct)}  {sem_lastro_pct[:8]}")
    print(f"valores em R$ citados     : {len(reais)}  {reais[:5]}")
    print(f"  (nenhum CSV traz valor absoluto em reais por empresa)")
    print(f"empresas citadas          : {entidades}")
    print(f"  ausentes das fontes     : {sem_lastro_ent}")
    print(f"fontes citadas nao usadas : {fabricadas}")
    print("-" * 62)

    falhas = []
    if sem_lastro_pct:
        falhas.append(f"{len(sem_lastro_pct)} percentuais sem origem")
    if sem_lastro_ent:
        falhas.append(f"{len(sem_lastro_ent)} empresas sem qualquer mencao nas fontes")
    if fabricadas:
        falhas.append(f"bibliografia fabricada: {fabricadas}")

    if falhas:
        print("RESULTADO: RELATORIO NAO VERIFICAVEL")
        for f in falhas:
            print(f"  - {f}")
        sys.exit(1)

    print("RESULTADO: todas as afirmacoes tem origem rastreavel")


if __name__ == "__main__":
    main()