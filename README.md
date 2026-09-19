# Agentes Econômicos — pipeline multiagente e verificação de lastro factual

> Três agentes de IA coletam dados macroeconômicos, cotações da B3 e notícias, e produzem um relatório de investimentos. O projeto inclui um **verificador** que testa se cada afirmação do relatório tem origem nos dados coletados — e demonstra, com evidência reproduzível, que boa parte **não tem**.

`CrewAI` · `LangChain` · `Streamlit` · `Pandas` · `Python 3.12+`

---

## ⚠️ Aviso

Este é um **projeto acadêmico**. O relatório gerado **não é recomendação de investimento**, não foi revisado por profissional certificado e, como este repositório documenta, contém afirmações sem lastro nos dados coletados. Não use para decisões financeiras.

---

## O que o pipeline faz

```
BACEN SGS ────┐
Alpha Vantage ├──→ CSVs ──→ 3 agentes CrewAI ──→ relatório .md ──→ dashboard Streamlit
Portais web ──┘                                        │
                                                  verificador
                                                  (gate de lastro)
```

| Etapa | Script | Saída |
|---|---|---|
| Indicadores macro | `scripts/indicadores_economicos.py` | IPCA, SELIC, PIB, dólar, commodities, IGP-M — 120 registros |
| Cotações | `scripts/acoes.py` | 10 tickers da B3, 200 registros |
| Notícias | `scripts/noticias.py` | 36 manchetes de 4 portais |
| Análise multiagente | `scripts/agentes_economicos.py` | relatório com recomendações |
| **Verificação** | `scripts/verificar_relatorio.py` | aprovação ou reprovação do relatório |
| Visualização | `streamlit/dashboard.py` | painel consolidado |

Os três agentes rodam em cadeia sequencial: **analista macroeconômico** → **especialista em ações** → **redator**. Cada um recebe apenas a saída do anterior.

---

## O achado: o relatório inventou a própria bibliografia

Numa execução real, o relatório gerado listou como fontes:

> *"Valor Econômico, Bloomberg, Reuters, Infomoney"* e *"Arquivos CSV internos da B3"*

O pipeline **nunca acessa** Valor, Bloomberg ou Reuters — ele raspa CNN Brasil, G1, InfoMoney e Exame. E não existe CSV da B3; os preços vêm da Alpha Vantage.

O `verificar_relatorio.py` mede isso:

```
percentuais citados       : 5
  sem lastro nos CSVs     : 2  ['1.85', '2.1']
valores em R$ citados     : 5  ['R$ 2', 'R$ 270 bilhões', 'R$ 5,20',
                                'R$ 6,5 bilhões', 'R$ 9,03 bilhões']
empresas citadas          : ['B3','Bradesco','Itaú','Petrobras','Vale','WEG']
  ausentes das fontes     : ['Bradesco', 'Itaú', 'Petrobras']
fontes citadas nao usadas : ['bloomberg','focus','ibge','reuters','valor econômico']
--------------------------------------------------------------
RESULTADO: RELATORIO NAO VERIFICAVEL
```

Três das cinco empresas que receberam recomendação (`COMPRA` / `MANTER`) **não aparecem em nenhum dos arquivos de entrada**. Valores como "R$ 9,03 bilhões em dividendos" não vieram de fonte alguma — foram produzidos da memória do modelo.

**Por que passa despercebido:** o texto é fluente, bem estruturado e cita números com precisão decimal. O apêndice de fontes, que existe justamente para dar rastreabilidade, é o trecho mais fabricado do documento.

---

## O verificador

`scripts/verificar_relatorio.py` não avalia o mérito da análise — isso nenhum teste automático faz. Ele responde a uma pergunta objetiva: **cada número e cada fonte citada tem de onde ter vindo?**

- extrai percentuais, valores em reais, nomes de empresas e fontes do relatório;
- confronta com o conteúdo dos três CSVs de entrada;
- confronta as fontes citadas com a lista de domínios que o pipeline realmente acessa;
- sai com código `1` quando encontra afirmação sem origem.

Por sair com código de erro, pode ser usado como portão em `main.py` ou em CI, impedindo publicação de relatório sem lastro.

### Limitações conhecidas do verificador

Esta é uma primeira versão, e é importante ser explícito sobre o que ela **não** garante:

- **Casamento por substring produz falso-negativo.** "Vale" bate com "vale a pena" em qualquer manchete; "WEG" e "B3" batem com os tickers `WEGE3` e `B3SA3`. O nome existe na fonte, mas não como notícia que sustente a tese.
- **Tolerância numérica de 0,05** contra um conjunto de 120+ valores torna coincidência provável.
- **Ausência de alerta não é validação.** O que a ferramenta acusa é real; o que ela deixa passar permanece não verificado.

Uma v2 exigiria correspondência por palavra inteira e checagem de contexto, não apenas presença do token.

---

## Como rodar

```bash
git clone <este-repositorio>
cd Projeto_agentes_IA_economicos

python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # preencha as chaves
```

Chaves necessárias no `.env`:

| Variável | Onde obter | Obrigatória |
|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com | sim — sem ela os agentes não rodam |
| `ALPHA_VANTAGE_API_KEY` | alphavantage.co | sim — gratuita, 25 chamadas/dia |
| `SERPER_API_KEY` | serper.dev | opcional — busca web dos agentes |

```bash
# pipeline completo
python main/main.py

# ou etapa por etapa
python scripts/indicadores_economicos.py
python scripts/acoes.py
python scripts/noticias.py
python scripts/agentes_economicos.py
python scripts/verificar_relatorio.py
streamlit run streamlit/dashboard.py
```

---

## Modos de falha silenciosa mapeados

Cada fonte externa falha sem quebrar o script. Documentar isso foi metade do trabalho:

| Fonte | Como falha em silêncio | Como detectar |
|---|---|---|
| **Alpha Vantage** | ao estourar 25 chamadas/dia, responde HTTP 200 com aviso no corpo; o script grava CSV vazio | conferir contagem de linhas após a coleta |
| **Scraping** | seletor CSS desatualizado retorna lista vazia sem erro — um portal trouxe 17 manchetes e outro apenas 2 | comparar volume por portal entre execuções |
| **CrewAI** | quando uma ferramenta falha, a mensagem de erro é entregue ao agente como se fosse o resultado da busca; ele continua escrevendo | verificar se o relatório cita conteúdo atual e com fonte |
| **LLM** | lacuna de contexto é preenchida com texto plausível — o relatório datou a si mesmo em outubro estando em setembro | injetar a data explicitamente no prompt |

**Princípio que organizou o trabalho:** script que termina sem erro não significa dado bom. Conferir contagem de linhas depois de cada coleta, antes de deixar o dado seguir.

---

## Problemas conhecidos no pipeline

- **A coleta de notícias não alimenta a análise.** Das 36 manchetes raspadas, nenhuma menciona qualquer uma das 10 empresas analisadas. A etapa consome tempo e rede sem contribuir.
- **`manager_llm` é parâmetro inerte.** Definido no `Crew`, mas só tem efeito em processo hierárquico — aqui o processo é sequencial.
- **O agendamento não persiste resultado.** O workflow em `.github/workflows/daily-main.yml` roda diariamente mas não faz commit dos artefatos gerados; a saída se perde ao fim da execução.
- **Orquestração sequencial propaga erro sem atrito.** O terceiro agente não tem como saber que o primeiro trabalhou com CSV vazio.

---

## Estrutura

```
main/
  main.py                    orquestrador local
scripts/
  indicadores_economicos.py  BACEN SGS (sem chave)
  acoes.py                   Alpha Vantage, 10 tickers B3
  noticias.py                scraping de 4 portais
  agentes_economicos.py      3 agentes CrewAI
  verificar_relatorio.py     gate de lastro factual
streamlit/
  dashboard.py               painel consolidado
data/                        CSVs e relatório gerado
.github/workflows/           execução diária agendada
```

---

## Contexto e créditos

Projeto prático da disciplina **LLM's — Engenharias Avançadas**, de autoria do **Prof. Thiago Azeredo Rodrigues**. O enunciado, a arquitetura original do pipeline e os scripts de coleta são material da disciplina.

Contribuições próprias documentadas aqui: a auditoria do relatório gerado, o verificador de lastro factual (`scripts/verificar_relatorio.py`), o mapeamento dos modos de falha silenciosa e a documentação dos problemas conhecidos.

## Licença

MIT — ver [LICENSE](LICENSE).
