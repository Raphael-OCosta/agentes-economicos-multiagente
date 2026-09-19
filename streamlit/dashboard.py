# streamlit/dashboard.py

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


import plotly.express as px

# ============================================================
# Configuração da página
# ============================================================
st.set_page_config(
    layout="wide",
    page_title="Painel de Análise de Investimentos",
)

# CSS extra para deixar o fundo mais “trading room”
CUSTOM_CSS = """
<style>
    .stApp {
        background-color: #02040a;
        color: #f9fafb;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================================================
# Caminhos de arquivos (raiz do projeto + /data)
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

ARQUIVO_RELATORIO_AGENTES = DATA_DIR / "relatorio_indicacao_acoes.md"
ARQUIVO_ACOES = DATA_DIR / "top_10_acoes.csv"
ARQUIVO_INDICADORES_ECONOMICOS = DATA_DIR / "indicadores_economicos.csv"
ARQUIVO_NOTICIAS = DATA_DIR / "noticias_investimentos.csv"

# ============================================================
# Carregar variáveis de ambiente
# ============================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================
# Inicialização do modelo de chat (OpenAI nativo)
# ============================================================
chat_model = None
if not OPENAI_API_KEY:
    st.error("Variável de ambiente OPENAI_API_KEY não encontrada.")
    st.warning("O chatbot estará desabilitado até que a chave seja configurada.")
else:
    try:
        chat_model = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.4,
            api_key=OPENAI_API_KEY,
        )
    except Exception as e:
        st.error(f"Erro ao inicializar o modelo de chat: {e}")
        st.warning("As funcionalidades do chatbot estarão desabilitadas.")

# ============================================================
# Contexto do chatbot
# ============================================================
contexto_chat = """
Você é o "Analista Econômico Virtual", um assistente de IA especializado em economia e mercado financeiro brasileiro.

**Especialidade:**
- Economia brasileira, tendências de mercado, indicadores (IPCA, SELIC, PIB, câmbio),
- Análise de ações (foco em volume e notícias relevantes),
- Interpretação de notícias financeiras.

**Objetivo:**
Ajudar o usuário a entender o cenário econômico, responder perguntas sobre investimentos e finanças de forma clara, objetiva e consultiva.

**Contexto Econômico Atual (base para suas respostas):**
- Inflação (IPCA): tendência de desaceleração nos últimos meses.
- Taxa de Juros (SELIC): 10,75% ao ano.
- Mercado de Ações: PETR4, VALE3 e WEGE3 apresentam maiores volumes recentes.
- Cenário Macroeconômico e Notícias: atenção à alta do petróleo e discussões sobre risco fiscal no país.

**Diretrizes:**
1. Baseie-se principalmente nesse contexto ao responder.
2. Seja claro, direto e educativo.
3. Tenha abordagem consultiva, explicando cenários, riscos e potenciais.
4. Não dê ordens diretas de investimento (não diga “compre X”), foque em análise.
5. Lembre que o cenário é dinâmico e pode mudar.
6. Ao comentar notícias, foque nos impactos econômicos e nos ativos mencionados.
7. Adicione contexto relevante mesmo em perguntas simples.
"""

# ============================================================
# Estado da sessão para histórico do chat
# ============================================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ============================================================
# Cabeçalho
# ============================================================
st.title("📊 Painel de Análise de Investimentos")
st.markdown(
    "Visão consolidada do mercado financeiro com análises multiagente, dados de ações, "
    "indicadores econômicos e notícias filtradas."
)
st.divider()

# ============================================================
# Chatbot no topo
# ============================================================
st.header("💬 Converse com o Analista Econômico Virtual")

pergunta_cliente = st.text_input("Digite sua pergunta sobre investimentos ou economia:")

if pergunta_cliente and chat_model:
    mensagens = [SystemMessage(content=contexto_chat)]

    # Reconstruir o histórico
    for troca in st.session_state.chat_history:
        mensagens.append(HumanMessage(content=troca["pergunta"]))
        mensagens.append(AIMessage(content=troca["resposta"]))

    mensagens.append(HumanMessage(content=pergunta_cliente))

    try:
        resposta_obj = chat_model(mensagens)
        resposta = resposta_obj.content
        st.session_state.chat_history.append(
            {"pergunta": pergunta_cliente, "resposta": resposta}
        )

        st.markdown("### 🧠 Resposta do Agente:")
        st.write(resposta)
    except Exception as e:
        st.error(f"Erro ao obter resposta do agente: {e}")

elif pergunta_cliente and not chat_model:
    st.warning("O modelo de chat não está configurado. Não é possível processar a pergunta.")

# Histórico do chat
if chat_model:
    with st.expander("📜 Histórico da conversa", expanded=False):
        for i, troca in enumerate(st.session_state.chat_history):
            st.markdown(f"**Você:** {troca['pergunta']}")
            st.markdown(f"**Agente:** {troca['resposta']}")
            if i < len(st.session_state.chat_history) - 1:
                st.markdown("---")

st.divider()

# ============================================================
# Funções utilitárias de carregamento
# ============================================================
@st.cache_data
def carregar_relatorio_md(caminho: Path) -> str:
    if caminho.exists():
        try:
            return caminho.read_text(encoding="utf-8")
        except Exception as e:
            return f"Erro ao ler o relatório: {e}"
    return "Relatório não encontrado. Execute a análise dos agentes primeiro."

@st.cache_data
def carregar_csv(caminho: Path):
    if not caminho.exists():
        return f"Arquivo {caminho.name} não encontrado."
    try:
        df = pd.read_csv(caminho)
        if df.empty:
            return f"Arquivo {caminho.name} está vazio."
        return df
    except pd.errors.EmptyDataError:
        return f"Arquivo {caminho.name} não contém dados para parsear."
    except Exception as e:
        return f"Erro ao carregar {caminho.name}: {e}"

# ============================================================
# Seção: Relatório dos agentes
# ============================================================
st.header("📊 Análises Detalhadas")
st.divider()

st.subheader("🤖 Relatório da Análise dos Agentes (CrewAI)")
relatorio_agentes = carregar_relatorio_md(ARQUIVO_RELATORIO_AGENTES)

with st.expander("Clique para ver o relatório completo", expanded=False):
    st.markdown(relatorio_agentes, unsafe_allow_html=True)

st.divider()

# ============================================================
# Gráficos e dados – Ações e Indicadores
# ============================================================
col1, col2 = st.columns(2)

# ------------------------
# COLUNA 1 – AÇÕES
# ------------------------
with col1:
    st.subheader("📈 Top 10 Ações (últimos registros)")

    df_acoes = carregar_csv(ARQUIVO_ACOES)
    if isinstance(df_acoes, pd.DataFrame):
        if "ticker" not in df_acoes.columns:
            st.error(f"Coluna 'ticker' não encontrada no arquivo {ARQUIVO_ACOES.name}.")
        else:
            tickers = sorted(df_acoes["ticker"].unique())
            if not tickers:
                st.info("Nenhum ticker encontrado no arquivo de ações.")
            else:
                ticker_selecionado = st.selectbox(
                    "Selecione uma ação para ver o gráfico:",
                    tickers,
                )

                if ticker_selecionado:
                    df_ticker = df_acoes[df_acoes["ticker"] == ticker_selecionado].copy()

                    # Detectar coluna de data (pode ser 'Unnamed: 0', 'data', 'Data', 'Date')
                    date_col = None
                    for candidate in ["Unnamed: 0", "data", "Data", "Date"]:
                        if candidate in df_ticker.columns:
                            conv = pd.to_datetime(df_ticker[candidate], errors="coerce")
                            if conv.notna().any():
                                date_col = candidate
                                df_ticker["data_plot"] = conv
                                break

                    if date_col is None:
                        st.warning(
                            "Não foi possível identificar a coluna de data para o gráfico de ações. "
                            "Verifique se existe uma coluna como 'Unnamed: 0', 'data', 'Data' ou 'Date'."
                        )
                    else:
                        df_ticker = df_ticker.dropna(subset=["data_plot"])
                        df_ticker = df_ticker.sort_values("data_plot")

                        if "fechamento" in df_ticker.columns and not df_ticker.empty:
                            # === GRÁFICO NEON VERDE ===
                            fig = px.line(
                                df_ticker,
                                x="data_plot",
                                y="fechamento",
                                title=f"Preço de Fechamento — {ticker_selecionado}",
                                markers=False,
                            )

                            fig.update_traces(
                                line=dict(color="#22c55e", width=2.5)  # verde neon
                            )

                            fig.update_layout(
                                template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="#020617",
                                font=dict(color="#e5e7eb"),
                                margin=dict(l=40, r=20, t=40, b=40),
                                xaxis=dict(
                                    showgrid=False,
                                    zeroline=False,
                                    showline=False,
                                ),
                                yaxis=dict(
                                    showgrid=False,
                                    zeroline=False,
                                    showline=False,
                                ),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info(
                                f"Não há dados de fechamento válidos para plotar para {ticker_selecionado}."
                            )

                        with st.expander(f"Ver tabela de dados - {ticker_selecionado}", expanded=False):
                            st.dataframe(
                                df_acoes[df_acoes["ticker"] == ticker_selecionado],
                                height=300,
                            )
    elif isinstance(df_acoes, str):
        st.error(df_acoes)

# ------------------------
# COLUNA 2 – INDICADORES
# ------------------------
with col2:
    st.subheader("📉 Indicadores Econômicos (IPCA, SELIC, PIB, Dólar, etc.)")

    df_indicadores = carregar_csv(ARQUIVO_INDICADORES_ECONOMICOS)

    if isinstance(df_indicadores, pd.DataFrame):
        required_cols = ["data", "valor", "indicador"]
        if not all(col in df_indicadores.columns for col in required_cols):
            st.error(
                f"O arquivo {ARQUIVO_INDICADORES_ECONOMICOS.name} deve conter as colunas: "
                f"{', '.join(required_cols)}."
            )
        else:
            # Converter datas
            df_indicadores["data"] = pd.to_datetime(
                df_indicadores["data"], errors="coerce"
            )
            df_indicadores = df_indicadores.dropna(subset=["data"])

            if df_indicadores.empty:
                st.warning("Não há dados válidos de indicadores após conversão de datas.")
            else:
                indicadores_disponiveis = sorted(df_indicadores["indicador"].unique())
                if not indicadores_disponiveis:
                    st.warning("Nenhum indicador encontrado na coluna 'indicador'.")
                else:
                    indicador_selecionado = st.selectbox(
                        "Selecione o indicador para visualização:",
                        indicadores_disponiveis,
                    )

                    if indicador_selecionado:
                        df_plot = df_indicadores[
                            df_indicadores["indicador"] == indicador_selecionado
                        ].copy()

                        if df_plot.empty:
                            st.info(
                                f"Não há dados para o indicador '{indicador_selecionado}'."
                            )
                        else:
                            # Garantir valor numérico
                            if not pd.api.types.is_numeric_dtype(df_plot["valor"]):
                                df_plot["valor"] = pd.to_numeric(
                                    df_plot["valor"], errors="coerce"
                                )
                                df_plot = df_plot.dropna(subset=["valor"])

                            if df_plot.empty:
                                st.info(
                                    f"Não há valores numéricos válidos para plotar para '{indicador_selecionado}'."
                                )
                            else:
                                df_plot = df_plot.sort_values("data")

                                # === GRÁFICO NEON VERDE PARA INDICADOR ===
                                fig = px.area(
                                    df_plot,
                                    x="data",
                                    y="valor",
                                    title=f"{indicador_selecionado} — últimos registros",
                                )

                                fig.update_traces(
                                    line=dict(color="#22c55e", width=2.0),
                                    fillcolor="rgba(34,197,94,0.15)",  # verde translúcido
                                )

                                fig.update_layout(
                                    template="plotly_dark",
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="#020617",
                                    font=dict(color="#e5e7eb"),
                                    margin=dict(l=40, r=20, t=40, b=40),
                                    xaxis=dict(
                                        showgrid=False,
                                        zeroline=False,
                                        showline=False,
                                    ),
                                    yaxis=dict(
                                        showgrid=False,
                                        zeroline=False,
                                        showline=False,
                                    ),
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                with st.expander(
                                    f"Ver tabela de dados - {indicador_selecionado}",
                                    expanded=False,
                                ):
                                    st.dataframe(df_plot, height=300)
    elif isinstance(df_indicadores, str):
        st.error(df_indicadores)

st.divider()

# ============================================================
# Notícias recentes
# ============================================================
st.subheader("📰 Notícias Recentes de Investimento")

df_noticias = carregar_csv(ARQUIVO_NOTICIAS)
if isinstance(df_noticias, pd.DataFrame):
    if "titulo" in df_noticias.columns and "link" in df_noticias.columns:
        for _, row in df_noticias.head(min(10, len(df_noticias))).iterrows():
            titulo = str(row["titulo"])
            link = str(row["link"]) if "link" in row and pd.notna(row["link"]) else ""

            st.markdown(f"### {titulo}")
            if link and link.strip().lower() not in ["nan", "na", "n/a"]:
                st.markdown(f"[Ler notícia completa]({link})")
                st.caption(f"Fonte: {row.get('fonte', 'Não informado')}")
            else:
                st.caption("Link não disponível.")
            st.markdown("---")
    else:
        st.warning(
            f"Colunas 'titulo' e 'link' não encontradas em {ARQUIVO_NOTICIAS.name}. "
            "Exibindo as primeiras 10 linhas como fallback."
        )
        st.dataframe(df_noticias.head(10))
elif isinstance(df_noticias, str):
    st.error(df_noticias)

# ============================================================
# Rodapé / Sidebar
# ============================================================
st.sidebar.info(
    f"Painel atualizado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}"
)
st.sidebar.markdown("Desenvolvido para demonstração de LLMs + agentes + dados financeiros.")
