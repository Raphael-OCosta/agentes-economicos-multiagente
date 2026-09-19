# scripts/agentes_economicos.py

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai_tools.tools import SerperDevTool
from langchain_openai import ChatOpenAI

# ============================================================
# Carregar variáveis de ambiente
# ============================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "ERRO: Variável de ambiente OPENAI_API_KEY não encontrada. "
        "Defina no .env (local) ou nos Secrets (GitHub Actions / Render)."
    )

# SERPER_API_KEY é usada internamente pelo SerperDevTool
if not os.getenv("SERPER_API_KEY"):
    print(
        "⚠️ Aviso: SERPER_API_KEY não encontrada. "
        "O SerperDevTool pode não funcionar corretamente sem essa chave."
    )

# ============================================================
# Diretórios e arquivos
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ARQ_TOPO_ACOES = DATA_DIR / "top_10_acoes.csv"
ARQ_NOTICIAS = DATA_DIR / "noticias_investimentos.csv"
ARQ_INDICADORES = DATA_DIR / "indicadores_economicos.csv"
ARQ_RELATORIO_SAIDA = DATA_DIR / "relatorio_indicacao_acoes.md"

# ============================================================
# Leitura dos CSVs
# ============================================================
try:
    df_top_10_acoes = pd.read_csv(ARQ_TOPO_ACOES)
    df_noticias_investimento = pd.read_csv(ARQ_NOTICIAS)
    df_indices = pd.read_csv(ARQ_INDICADORES)
except FileNotFoundError as e:
    print("❌ Erro: Arquivo CSV não encontrado.")
    print(f"   Detalhe: {e}")
    print("   Verifique se os arquivos abaixo existem em 'data/':")
    print(f"   - {ARQ_TOPO_ACOES.name}")
    print(f"   - {ARQ_NOTICIAS.name}")
    print(f"   - {ARQ_INDICADORES.name}")
    raise SystemExit(1)

# ============================================================
# Transformar DataFrames em texto de contexto
# ============================================================
contexto_top_10_acoes = df_top_10_acoes.to_markdown(index=False)
contexto_indices = df_indices.to_markdown(index=False)

# Notícias: título + link
if not df_noticias_investimento.empty and {"titulo", "link"}.issubset(df_noticias_investimento.columns):
    contexto_noticias_investimentos = "\n".join(
        [
            f"Título: {row['titulo']}\nLink: {row['link']}"
            for _, row in df_noticias_investimento.iterrows()
        ]
    )
else:
    contexto_noticias_investimentos = "Nenhuma notícia de investimento carregada do CSV."

contexto_geral_csv = f"""
=== 📈 Dados Históricos de Indicadores Econômicos ===
{contexto_indices}

=== 📰 Notícias de Investimento Recentes (do CSV) ===
{contexto_noticias_investimentos}

=== 📊 Top 10 Ações (do CSV) ===
{contexto_top_10_acoes}
"""

# ============================================================
# Configuração do LLM (OpenAI nativo)
# ============================================================
llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY,
)

# Ferramenta de busca na web (internet)
web_tool = SerperDevTool()

# ============================================================
# Definição dos agentes
# ============================================================

analista_macroeconomico = Agent(
    role="Analista Macroeconômico Sênior",
    goal=(
        "Analisar o cenário macroeconômico brasileiro, com foco nos indicadores econômicos "
        "e nas notícias de investimento, para identificar tendências e impactos potenciais "
        "no mercado de ações, especialmente nas ações listadas no arquivo 'top_10_acoes.csv'."
    ),
    backstory=(
        "Economista com vasta experiência na análise da conjuntura econômica brasileira, "
        "indicadores e seus efeitos sobre os ativos financeiros. Utiliza dados históricos "
        "e informações de mercado atualizadas para embasar suas projeções."
    ),
    verbose=True,
    allow_delegation=False,
    tools=[web_tool],  # acesso à internet via Serper
    llm=llm,
)

especialista_em_acoes = Agent(
    role="Especialista em Análise de Ações da B3",
    goal=(
        "Avaliar ações da B3, com ênfase nas 'top_10_acoes.csv' mas não se limitando a elas, "
        "com base na análise macroeconômica, dados fundamentalistas (se disponíveis) e notícias de mercado. "
        "Gerar recomendações de COMPRA, VENDA ou MANTER para ações específicas, com justificativas claras."
    ),
    backstory=(
        "Analista de investimentos (CNPI) focado no mercado de ações brasileiro, com expertise em valuation "
        "de empresas e estratégias de investimento. Busca identificar assimetrias e oportunidades, "
        "fornecendo recomendações acionáveis."
    ),
    verbose=True,
    allow_delegation=False,
    tools=[web_tool],  # também pode consultar internet, se você quiser restringir, remova aqui
    llm=llm,
)

redator_de_relatorios_de_investimento = Agent(
    role="Redator de Relatórios de Investimento",
    goal=(
        "Consolidar a análise macroeconômica e as recomendações de ações em um relatório final claro, "
        "conciso e bem estruturado para investidores, destacando as principais indicações e justificativas."
    ),
    backstory=(
        "Profissional de comunicação com foco no mercado financeiro, especializado em transformar análises "
        "técnicas complexas em relatórios de fácil compreensão para o público investidor."
    ),
    verbose=True,
    allow_delegation=False,
    tools=[],  # não precisa de internet, só organiza o que os outros produziram
    llm=llm,
)

# ============================================================
# Tarefas (Tasks)
# ============================================================

tarefa_analise_cenario = Task(
    description=(
        "1. Analise os dados dos indicadores econômicos fornecidos no 'contexto_geral_csv' para entender "
        "as tendências recentes do mercado.\n"
        "2. Revise as 'Notícias de Investimento Recentes (do CSV)' para capturar o sentimento e os eventos atuais.\n"
        "3. Use a ferramenta de busca na web (SerperDevTool) para buscar informações atualizadas (últimos 1–3 meses) sobre:\n"
        "   a) Perspectivas para IPCA, PIB, dólar, IGP-M e taxa Selic no Brasil.\n"
        "   b) Principais fatores macroeconômicos que estão afetando o mercado de ações brasileiro.\n"
        "   c) Notícias relevantes sobre a economia brasileira que possam impactar investimentos.\n"
        "4. Sintetize tudo em um panorama do cenário macroeconômico atual e suas implicações para investidores em ações.\n\n"
        f"Contexto dos CSVs:\n{contexto_geral_csv}"
    ),
    expected_output=(
        "Um relatório conciso sobre o cenário macroeconômico brasileiro, destacando:\n"
        "- Análise da trajetória recente dos indicadores coletados e suas perspectivas.\n"
        "- Principais notícias e eventos de investimento relevantes (CSV + pesquisa online).\n"
        "- Impactos esperados desse cenário no mercado de ações brasileiro."
    ),
    agent=analista_macroeconomico,
)

tarefa_indicacao_acoes = Task(
    description=(
        "1. Com base na análise do cenário macroeconômico (tarefa anterior), avalie as ações listadas "
        "no arquivo 'top_10_acoes.csv'.\n"
        "2. Para cada ação do 'top_10_acoes.csv', utilize a ferramenta de busca na web para encontrar:\n"
        "   a) Notícias recentes e específicas sobre a empresa e seu setor.\n"
        "   b) Análises e perspectivas de mercado (preço-alvo, recomendações, etc.).\n"
        "   c) Informações fundamentais relevantes, quando possível.\n"
        "3. Se julgar pertinente, pesquise também outras ações da B3 que possam representar boas "
        "oportunidades ou riscos no cenário atual.\n"
        "4. Formule recomendações de INVESTIMENTO (COMPRA, VENDA ou MANTER) para pelo menos 5 ações "
        "(priorizando as do 'top_10_acoes.csv', mas podendo incluir outras), cada uma com justificativa clara.\n\n"
        f"Contexto principal — Top 10 Ações (CSV):\n{contexto_top_10_acoes}"
    ),
    expected_output=(
        "Um relatório de indicações de ações contendo:\n"
        "- Recomendações claras de COMPRA, VENDA ou MANTER para 3 a 5 ações da Bovespa (com seus tickers).\n"
        "- Justificativa detalhada para cada recomendação, explicando fatores macro, setoriais, "
        "específicos da empresa e notícias recentes.\n"
        "Priorizar as ações do 'top_10_acoes.csv', mas incluir outras se relevantes."
    ),
    agent=especialista_em_acoes,
    context=[tarefa_analise_cenario],
)

tarefa_compilacao_relatorio_final = Task(
    description=(
        "**Sua responsabilidade é GERAR e ESCREVER o conteúdo completo do relatório de investimento final "
        "em formato markdown. Não descreva o que você faria; produza o relatório AGORA.**\n\n"
        "Você deve:\n"
        "1. Unificar a análise do cenário macroeconômico e as indicações de ações em um relatório coeso.\n"
        "2. Escrever em linguagem clara, profissional e acessível, usando markdown (títulos, subtítulos, listas, negrito).\n"
        "3. Destacar como o cenário macroeconômico fundamenta as recomendações de ações.\n"
        "4. Apresentar cada indicação com: Ticker, Recomendação (COMPRA/VENDA/MANTER) e justificativa completa.\n"
        "5. Incluir um apêndice mencionando as fontes de dados (CSV + pesquisa online).\n\n"
        "Use as análises das tarefas anteriores, disponíveis no contexto, como base principal."
    ),
    expected_output=(
        "Um relatório de investimento completo em markdown (PT-BR), contendo:\n"
        "### Sumário Executivo\n"
        "### Análise do Cenário Macroeconômico\n"
        "### Indicações de Ações Detalhadas\n"
        "### Breves Considerações sobre Riscos e Oportunidades\n"
        "### Apêndice: Fontes de Dados\n"
    ),
    agent=redator_de_relatorios_de_investimento,
    context=[tarefa_analise_cenario, tarefa_indicacao_acoes],
)

# ============================================================
# Montar a Crew e executar
# ============================================================

def main():
    crew_recomendacao_de_acoes = Crew(
        agents=[
            analista_macroeconomico,
            especialista_em_acoes,
            redator_de_relatorios_de_investimento,
        ],
        tasks=[
            tarefa_analise_cenario,
            tarefa_indicacao_acoes,
            tarefa_compilacao_relatorio_final,
        ],
        verbose=True,
        manager_llm=llm,  # o próprio modelo OpenAI coordena
    )

    print("🚀 Iniciando a análise da Crew para recomendação de ações...")
    resultado_crew = crew_recomendacao_de_acoes.kickoff()

    # Extrair texto final
    if hasattr(resultado_crew, "raw") and isinstance(resultado_crew.raw, str):
        texto_para_salvar = resultado_crew.raw
    elif hasattr(resultado_crew, "result") and isinstance(resultado_crew.result, str):
        texto_para_salvar = resultado_crew.result
    else:
        texto_para_salvar = str(resultado_crew)

    print("\n\n=== RELATÓRIO FINAL DE INVESTIMENTO (TEXTO) ===\n")
    print(texto_para_salvar)

    # Salvar relatório em markdown
    ARQ_RELATORIO_SAIDA.write_text(texto_para_salvar, encoding="utf-8")
    print(f"\n\n📁 Relatório salvo em: {ARQ_RELATORIO_SAIDA}")


if __name__ == "__main__":
    main()
