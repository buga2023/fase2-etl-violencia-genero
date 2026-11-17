# Feminicídio interseccional no Brasil (2019 a 2024)

Projeto da disciplina Big Data e Analytics (UCSal, Engenharia de Software, 2026/2), tema 06: Monitoramento de Segurança Pública e Feminicídio Interseccional. ODS 5 (Igualdade de Gênero) e ODS 18 (Igualdade Étnico-Racial).

Equipe: Gustavo Souza Santos e Mateus Bulhões.

**Dashboard publicado:** https://feminicidio-interseccional.streamlit.app
**Rodar o dashboard local (um comando, depois do setup):** `streamlit run dashboard/app.py`

![Painel](docs/img/painel_kpis.jpg)

## Sumário

1. [O problema](#1-o-problema)
2. [Arquitetura](#2-arquitetura)
3. [Como reproduzir (deployment guide)](#3-como-reproduzir-deployment-guide)
4. [Segurança e LGPD](#4-segurança-e-lgpd)
5. [Os V's do Big Data aplicados à base](#5-os-vs-do-big-data-aplicados-à-base)
6. [Tipos de dados](#6-tipos-de-dados)
7. [Por que banco relacional](#7-por-que-banco-relacional)
8. [Modelo e dicionário de dados](#8-modelo-e-dicionário-de-dados)
9. [Regras de negócio](#9-regras-de-negócio)
10. [Dashboard e os 4 indicadores](#10-dashboard-e-os-4-indicadores)
11. [Análise crítica: o que os dados mostram sobre ODS 5 e ODS 18](#11-análise-crítica-o-que-os-dados-mostram-sobre-ods-5-e-ods-18)
12. [Limitações](#12-limitações)
13. [Estrutura do repositório e histórico das fases](#13-estrutura-do-repositório-e-histórico-das-fases)

## 1. O problema

A pergunta do projeto é: quem são as mulheres mortas por agressão no Brasil, como morrem, onde o risco é maior e se o Estado está nomeando essas mortes como feminicídio.

Nenhuma base pública responde isso sozinha. A SINESP-VDE (Ministério da Justiça) é o registro policial: sabe se o crime foi feminicídio, mas não registra a raça da vítima. O SIM (DataSUS) é a declaração de óbito: tem raça/cor, idade e o meio da agressão, mas não diz se foi feminicídio. Por isso juntamos as duas, com o IBGE ligando os municípios e dando a população feminina para calcular taxas.

## 2. Arquitetura

```mermaid
flowchart LR
    subgraph Fontes abertas
        A[SINESP-VDE<br/>XLSX anual]
        B[SIM / DataSUS<br/>CSV e ZIP anual]
        C[IBGE<br/>API JSON + XLSX]
    end
    subgraph ETL em Python
        D[extract.py<br/>download + SHA-256]
        E[transform_*.py<br/>limpeza, tipagem,<br/>leitura em chunks]
        F[load.py<br/>COPY numa transação]
    end
    subgraph Aiven Free Tier
        G[(PostgreSQL 18<br/>schema vde<br/>modelo estrela)]
    end
    H[Streamlit Cloud<br/>dashboard/app.py]
    I[Terraform<br/>terraform/*.tf]
    J[GitHub Actions<br/>testes + checagem<br/>mensal das fontes]
    A --> D
    B --> D
    C --> D
    D --> E --> F --> G
    I -. provisiona .-> G
    G -- SQL ao vivo<br/>usuário só leitura --> H
    J -. monitora .-> A
    J -. monitora .-> B
```

| Camada | Tecnologia | Onde está |
|---|---|---|
| Infraestrutura como código | Terraform 1.5+ com o provider `aiven/aiven` | `terraform/` |
| Banco | Aiven for PostgreSQL 18, plano `free-1-1gb` (1 GB, custo zero) | provisionado pelo Terraform |
| ETL | Python 3.12, pandas (leitura em chunks), psycopg (COPY) | `etl/`, `run_pipeline.py` |
| Análise estatística | pandas, scipy, matplotlib | `analise/` |
| Dashboard | Streamlit + Plotly, consultando o banco a cada interação | `dashboard/` |
| Automação | GitHub Actions | `.github/workflows/` |

Não usamos Spark/Hadoop. Os dados brutos somam uns 2,6 GB e cabem num notebook se forem lidos em blocos (pandas com `chunksize`), então um cluster só traria custo e complexidade. Se a base crescesse para dezenas de GB (por exemplo, todos os anos do SIM desde 1996), a troca natural seria PySpark, mantendo as mesmas regras de `etl/config.py`.

## 3. Como reproduzir (deployment guide)

Pré-requisitos: Python 3.12, Terraform 1.5 ou mais novo e uma conta no Aiven.

### 3.1 Infraestrutura (Terraform)

```bash
cp .env.example .env                              # depois preencher AIVEN_API_TOKEN
cp terraform/terraform.tfvars.example terraform/terraform.tfvars   # nome do projeto Aiven
./scripts/tf.sh init
./scripts/tf.sh plan                              # mostra: 2 recursos a criar
./scripts/tf.sh apply                             # cria o PostgreSQL free e o usuário do painel (~6 min)
./scripts/tf.sh output -raw pg_service_uri        # copiar para DATABASE_URL no .env
```

O `scripts/tf.sh` só lê o token do `.env` e repassa como `TF_VAR_aiven_api_token`, para o token nunca ficar escrito em arquivo versionado. O que o Terraform cria:

| Recurso | O que é |
|---|---|
| `aiven_pg.banco` | serviço PostgreSQL `pg-feminicidio`, plano `free-1-1gb`, região `do-nyc` |
| `aiven_pg_user.painel` | usuário `painel_leitura`, usado só pelo dashboard |

### 3.2 Carga dos dados

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py                  # ETL completo: baixa ~2,6 GB, trata, carrega (~25 min)
# ou, se o banco foi recriado e os CSVs tratados já estão no repositório:
python -m scripts.carregar_processados  # carrega data/processed em ~40 s e aplica o GRANT do painel
python -m scripts.verificar_banco       # grava a evidência em docs/verificacao_banco.md
python -m pytest -q tests               # 9 testes das regras de tratamento
```

### 3.3 Dashboard

Local:

```bash
pip install -r dashboard/requirements.txt
# .streamlit/secrets.toml (fora do git) com a URI do usuário painel_leitura:
# DATABASE_URL = "postgres://painel_leitura:SENHA@HOST:PORTA/defaultdb?sslmode=require"
streamlit run dashboard/app.py
```

A senha sai de `./scripts/tf.sh output -raw painel_senha`.

Publicação no Streamlit Community Cloud: "Create app", repositório `buga2023/fase2-etl-violencia-genero`, branch `main`, arquivo `dashboard/app.py`, Python 3.12. Em "Advanced settings > Secrets" vai a mesma linha `DATABASE_URL = "..."` do usuário `painel_leitura`. O Cloud instala o `dashboard/requirements.txt` sozinho.

## 4. Segurança e LGPD

- Nenhuma senha, token ou URI está no repositório. `.env`, `terraform.tfvars`, `*.tfstate` e `.streamlit/secrets.toml` estão no `.gitignore`. No Streamlit Cloud a conexão fica em Secrets.
- O token do Aiven foi criado com validade de 30 dias e só é lido do `.env` pelo `scripts/tf.sh`.
- O dashboard usa o usuário `painel_leitura`, criado pelo Terraform, com `GRANT SELECT` no schema `vde` e nada mais (`sql/04_usuario_painel.sql`). Testamos: um `DELETE` com esse usuário falha com `InsufficientPrivilege`. Se a senha do painel vazar, ninguém consegue alterar os dados.
- As consultas do painel usam parâmetros (`%(nome)s` do psycopg), sem concatenar texto vindo da tela no SQL.
- LGPD: as duas bases são dados abertos e já saem sem identificação (o SIM aberto não tem nome, CPF nem endereço). Mesmo assim, o ETL agrega tudo por mês × município × categoria antes de carregar, então nenhuma linha do banco corresponde a uma pessoa. Também lemos só 6 das mais de 80 colunas do SIM, o mínimo para a pergunta.

## 5. Os V's do Big Data aplicados à base

Em aula vimos os 3 V's de Doug Laney. O guia do projeto pede mais dois.

| V | Na nossa base | O que fizemos |
|---|---|---|
| Volume | 6 XLSX da SINESP (~24 MB e 765 mil linhas cada) + 6 arquivos do SIM (44 a 633 MB, até 1,8 milhão de óbitos por ano). ~2,6 GB e 13,9 milhões de linhas | Leitura do SIM em blocos de 200 mil linhas, só 6 colunas, filtro (CID X85 a Y09, sexo feminino) e agregação dentro de cada bloco. O banco ficou com 256 mil linhas e uns 37 MB, menos de 4% do 1 GB do plano free |
| Velocidade | Fontes publicadas em lote, uma vez por ano. Sem streaming | Pipeline em batch. Um workflow do GitHub Actions roda todo dia 1º e confere se MJSP, DataSUS ou IBGE publicaram arquivo novo (`scripts/verificar_fontes.py`) |
| Variedade | XLSX, CSV com `;`, ZIP, JSON de API; layout que muda entre anos; SIM 2022/2023 sem cabeçalho | Normalização de nomes de coluna, validação de colunas obrigatórias e padronização do SIM sem alterar o arquivo original |
| Veracidade | Raça ignorada, município escrito à mão na SINESP, contagem como texto com ponto de milhar, SIM 2024 preliminar, Distrito Federal com linhas repetidas | 18 regras de tratamento documentadas, hash SHA-256 de cada arquivo na tabela `meta_carga`, totais conferidos antes e depois, comparação com o Anuário do FBSP e o Atlas da Violência |
| Valor | Cruzar gênero × raça × idade × território, o que nenhuma fonte faz sozinha | Taxas por 100 mil, percentual de vítimas negras por UF e o indicador de quanto das mortes vira feminicídio no registro policial |

O monitoramento já mostrou a Velocidade e a Veracidade na prática: em novembro de 2026 o script detectou que a SINESP publicou 2025 e revisou os arquivos de 2019 a 2024, e que o DataSUS republicou o SIM de 2022 e 2023. A base deste trabalho continua com as versões de outubro de 2026 (os hashes estão em `data/raw/manifest.json`), e uma nova rodada do `run_pipeline.py` atualiza tudo.

## 6. Tipos de dados

| Dado | Tipo | Por quê |
|---|---|---|
| SIM (CSV) | estruturado | colunas fixas, dicionário oficial do DataSUS |
| SINESP (XLSX) | estruturado | tabela, mas o layout muda de um ano para o outro |
| IBGE localidades (API) | semi-estruturado | JSON aninhado (município → microrregião → UF) |
| IBGE projeção da população (XLSX) | estruturado, em formato largo | uma coluna por ano, foi despivotada no ETL |
| Manifesto dos arquivos | semi-estruturado | JSON gerado pelo pipeline |

Não usamos dado não estruturado. A causa da morte já vem codificada pela CID-10.

## 7. Por que banco relacional

Escolhemos PostgreSQL (relacional) e não OpenSearch (não relacional, também disponível no Aiven):

- Os dados já são tabelas com chaves claras (tempo, município, sexo, raça), e a análise é de contagem e cruzamento com `JOIN` e `GROUP BY`. É o caso de uso do SQL.
- Juntar duas fontes depende de integridade: chave estrangeira garante que todo óbito aponta para um município e um mês que existem.
- O volume depois do ETL é pequeno (dezenas de MB), então não precisamos da escala horizontal de um NoSQL.
- OpenSearch faria sentido para busca em texto livre ou logs, o que esta base não tem.

## 8. Modelo e dicionário de dados

Esquema estrela com duas tabelas fato, porque as fontes têm grãos diferentes: a SINESP conta vítimas por evento e sexo, o SIM conta óbitos por raça, idade e meio. Tempo, município (com UF) e sexo são dimensões compartilhadas pelas duas, e é isso que permite cruzar.

```mermaid
erDiagram
    dim_uf ||--o{ dim_municipio : cod_uf
    dim_uf ||--o{ populacao_feminina_uf : cod_uf
    dim_tempo ||--o{ fato_vitimas_sinesp : id_tempo
    dim_municipio ||--o{ fato_vitimas_sinesp : id_municipio
    dim_evento ||--o{ fato_vitimas_sinesp : id_evento
    dim_sexo ||--o{ fato_vitimas_sinesp : id_sexo
    dim_tempo ||--o{ fato_obitos_agressao_sim : id_tempo
    dim_municipio ||--o{ fato_obitos_agressao_sim : id_municipio
    dim_sexo ||--o{ fato_obitos_agressao_sim : id_sexo
    dim_raca_cor ||--o{ fato_obitos_agressao_sim : id_raca_cor
    dim_faixa_etaria ||--o{ fato_obitos_agressao_sim : id_faixa
    dim_meio_agressao ||--o{ fato_obitos_agressao_sim : id_meio
```

### Dicionário de dados (schema `vde`)

| Tabela | Coluna | Tipo | Descrição |
|---|---|---|---|
| `dim_tempo` | `id_tempo` | INTEGER (PK) | ano e mês no formato AAAAMM |
| | `ano`, `mes`, `trimestre` | SMALLINT | partes da data, com CHECK de faixa |
| | `data_referencia` | DATE | sempre o dia 01 do mês |
| `dim_uf` | `cod_uf` | SMALLINT (PK) | código IBGE da UF (11 a 53) |
| | `sigla`, `nome`, `regiao` | CHAR(2), VARCHAR | identificação e região |
| `dim_municipio` | `id_municipio` | SERIAL (PK) | chave substituta |
| | `cod_ibge` | INTEGER (único) | código IBGE de 7 dígitos; NULL na linha "NÃO INFORMADO" de cada UF |
| | `nome`, `nome_normalizado` | VARCHAR | nome oficial e versão sem acento, usada para casar com a SINESP |
| | `cod_uf` | SMALLINT (FK) | UF do município |
| `dim_sexo` | `id_sexo`, `codigo`, `descricao` | SMALLINT, CHAR(1), VARCHAR | Feminino, Masculino, Não informado |
| `dim_raca_cor` | `id_raca_cor`, `descricao` | SMALLINT, VARCHAR | Branca, Preta, Amarela, Parda, Indígena, Ignorada (códigos do SIM) |
| | `negra` | BOOLEAN | verdadeiro para preta e parda (critério IBGE) |
| `dim_faixa_etaria` | `id_faixa`, `descricao`, `idade_min`, `idade_max` | SMALLINT, VARCHAR | 0-11, 12-17, 18-24, 25-29, 30-39, 40-49, 50-59, 60+, Ignorada |
| `dim_evento` | `id_evento`, `nome`, `grupo`, `violencia_genero` | SMALLINT, VARCHAR, BOOLEAN | os 8 eventos da SINESP mantidos (Letal, Tentativa, Sexual) |
| `dim_meio_agressao` | `id_meio`, `descricao`, `cids` | SMALLINT, VARCHAR | meio da agressão agrupado a partir da CID-10 |
| `fato_vitimas_sinesp` | `id_tempo`, `id_municipio`, `id_evento`, `id_sexo` | FKs (PK composta) | grão: mês × município × evento × sexo |
| | `qt_vitimas` | INTEGER > 0 | número de vítimas |
| `fato_obitos_agressao_sim` | `id_tempo`, `id_municipio`, `id_sexo`, `id_raca_cor`, `id_faixa`, `id_meio` | FKs (PK composta) | grão: mês × município × raça × faixa × meio; só mulheres (CHECK) |
| | `qt_obitos` | INTEGER > 0 | número de óbitos |
| `populacao_feminina_uf` | `cod_uf`, `ano` | FK, SMALLINT (PK composta) | grão: UF × ano |
| | `populacao` | INTEGER > 0 | mulheres residentes (IBGE, Projeção da População, revisão 2024) |
| `meta_carga` | `fonte`, `arquivo`, `sha256`, `tamanho_bytes`, `linhas_lidas`, `linhas_apos_filtro`, `arquivo_origem`, `sha256_origem`, `executado_em` | VARCHAR, CHAR(64), BIGINT, TIMESTAMPTZ | linhagem: qual arquivo oficial gerou a carga |

Visões: `vw_vitimas_genero_uf_ano`, `vw_obitos_mulheres_raca_uf_ano`, `vw_comparativo_uf_ano` (as duas fontes lado a lado por UF e ano) e `vw_taxas_uf_ano` (taxas por 100 mil).

Quantidade carregada (evidência em `docs/verificacao_banco.md`): 233.988 linhas em `fato_vitimas_sinesp` (968.489 vítimas), 22.005 em `fato_obitos_agressao_sim` (22.691 óbitos), 5.598 municípios, 162 linhas de população e 14 registros de linhagem.

## 9. Regras de negócio

Regras que transformam o dado bruto em indicador. O detalhe de cada uma, com o número de linhas afetadas, está em `docs/fase2.md` e `docs/relatorio_tratamento.md`.

| Regra | Descrição | Onde |
|---|---|---|
| R-01 Recorte | 2019 a 2024. No SIM só causa básica de agressão (CID-10 X85 a Y09) e sexo feminino (`2` ou `F`) | `etl/config.py` |
| R-02 Eventos | Da SINESP ficam 8 eventos de violência contra a pessoa; feminicídio e tentativa marcados como violência de gênero | `etl/config.py` |
| R-03 Mulher negra | Negra = preta + parda (critério IBGE e FBSP). Raça ignorada fica no total, então o percentual é conservador | `dim_raca_cor.negra` |
| R-04 Idade | O campo IDADE do SIM tem a unidade no 1º dígito. Menos de 1 ano vira 0 anos, 999 vira ignorada, depois agrupa em 9 faixas | `etl/transform_sim.py` |
| R-05 Meio | A CID de 4 caracteres vira meio da agressão (X93-X95 arma de fogo, X99 objeto cortante, etc.) | `dim_meio_agressao` |
| R-06 Município | SINESP casa com o IBGE por nome normalizado + 11 apelidos; SIM pelo código de 6 dígitos. Sem par vai para "NÃO INFORMADO" da UF, sem perder o total | `etl/transform_*.py` |
| R-07 Duplicatas | Só remove a mesma linha repetida em outro arquivo. Linhas repetidas no mesmo arquivo são do DF (uma por Região Administrativa) e são somadas | `etl/transform_sinesp.py` |
| R-08 Taxa por 100 mil | óbitos (ou feminicídios) ÷ população feminina da UF no ano × 100.000 | `vw_taxas_uf_ano` |
| R-09 Captação | feminicídios registrados na SINESP ÷ óbitos de mulheres por agressão no SIM. Mede quanto das mortes a polícia nomeia como feminicídio | dashboard, KPI 4 |
| R-10 Agregação | Nada de linha por pessoa no banco: tudo agregado por mês × município × categoria | `etl/transform_*.py` |

## 10. Dashboard e os 4 indicadores

Link: https://feminicidio-interseccional.streamlit.app (código em `dashboard/app.py` e `dashboard/consultas.py`).

O painel não tem dado embutido. Cada mudança de filtro roda SQL no PostgreSQL do Aiven com o usuário só leitura. Para a demonstração, o rodapé mostra o horário da consulta e um botão "Consultar o banco de novo" limpa o cache (que dura 2 minutos), e a seção "Ver as consultas" lista cada consulta com o tempo em milissegundos.

![Cruzamento raça × idade](docs/img/painel_interseccional.jpg)

### Os 4 indicadores (KPIs)

| # | Indicador | Cálculo | Valor (Brasil, 2019 a 2024) | Por que importa |
|---|---|---|---|---|
| 1 | Taxa de óbitos de mulheres por agressão | óbitos SIM ÷ população feminina × 100 mil | 3,51 por 100 mil | compara estados de tamanhos diferentes, igual ao Atlas da Violência |
| 2 | Vítimas negras | óbitos de pretas e pardas ÷ total de óbitos | 67,1% | é o recorte racial da ODS 18 |
| 3 | Feminicídios registrados | vítimas do evento Feminicídio na SINESP (sexo feminino) | 8.423, alta de 13% de 2019 a 2024 | é o número oficial do registro policial (ODS 5) |
| 4 | Mortes nomeadas como feminicídio | feminicídios ÷ óbitos de mulheres por agressão | 37,1% | mostra o quanto o Estado reconhece a morte como crime de gênero |

Embaixo dos cards aparece também o percentual de mortes por arma de fogo (49,1%).

### Interatividade

- Filtros cruzados na barra lateral: ano (intervalo), região, UF, raça/cor, faixa etária, meio da agressão e sexo da vítima. Todos valem para todos os gráficos ao mesmo tempo.
- Seletor de métrica: o gráfico de evolução anual e o ranking alternam entre taxa de óbitos, óbitos absolutos, taxa de feminicídio, feminicídios absolutos e % de vítimas negras.
- Drill-down: clicando numa barra do ranking o painel desce de região para estado e de estado para município (top 15), com botão para voltar.
- Cruzamentos: raça × faixa etária (barras empilhadas em %), meio da agressão × raça, sazonalidade por mês e tabela do recorte com exportação em CSV.

## 11. Análise crítica: o que os dados mostram sobre ODS 5 e ODS 18

A análise estatística completa está em `docs/relatorio_fase3/` e é reproduzida por `analise/perguntas.py`. Com as taxas da Fase 4, os achados ficaram assim:

1. O registro de feminicídio cresce, mas as mortes não. Os feminicídios na SINESP subiram 12,8% de 2019 a 2024 (regressão linear com R² = 0,94 e p = 0,002), enquanto a taxa de óbitos de mulheres por agressão no SIM ficou parada em torno de 3,5 por 100 mil. A explicação que fecha com os dados é que mais mortes passaram a ser classificadas como feminicídio, e não que mais mulheres estão morrendo. Para a ODS 5 isso é um avanço de reconhecimento, mas mostra que a violência letal em si não caiu.

2. O risco é muito desigual entre os estados. Com a taxa, a leitura muda: São Paulo tem o maior número absoluto de feminicídios, mas a menor taxa de óbitos do país (1,59 por 100 mil). Roraima tem 9,49, seis vezes mais. Norte (5,14) e Nordeste (4,85) ficam bem acima do Sudeste (2,25). Política pública que olha só para número absoluto concentra recurso onde a mulher corre menos risco.

3. Duas em cada três vítimas são negras, e isso não mudou em seis anos (66% a 68%). O percentual vai de cerca de 20% em Santa Catarina e no Rio Grande do Sul a mais de 90% em Alagoas, Amapá, Sergipe e Ceará, e o teste qui-quadrado confirma que a distribuição racial muda entre as regiões (p < 0,001). Cruzando com a idade, as mulheres negras são maioria em todas as faixas de 12 a 59 anos, então a desigualdade não é efeito da idade. É o ponto central da ODS 18: raça e território andam juntos.

4. Metade morre por arma de fogo (49,1%), e entre as mulheres negras essa fatia é ainda maior que entre as não negras. A faixa de 18 a 39 anos concentra 57% das mortes, com pico em dezembro. Isso aponta onde a prevenção tem mais retorno: controle de arma de fogo, rede de proteção para mulheres jovens e reforço no fim do ano.

5. A classificação não é igual no país. Só 37% das mortes de mulheres por agressão aparecem como feminicídio no registro policial, e esse número varia muito: o Ceará tem taxa de óbitos alta (5,90) e taxa de feminicídio baixa (0,72), enquanto Mato Grosso registra 2,59. Isso sugere subnotificação desigual. Um protocolo nacional de classificação ajudaria a medir a ODS 5 de forma comparável entre os estados.

Os números batem com quem publica sobre o tema: o Anuário do FBSP tem 1.492 feminicídios em 2024 (1.504 na revisão) e a nossa base tem 1.501; o Atlas da Violência tem 3.903 mulheres assassinadas em 2023, 68,2% negras, e a nossa base tem 3.887 e 68,1% (a diferença é que o Atlas inclui intervenção legal, CID Y35 e Y36).

## 12. Limitações

- Feminicídio (SINESP) e óbito por agressão (SIM) são conceitos próximos, não iguais. O KPI de captação é indicativo, não uma taxa exata de subnotificação.
- O SIM 2024 ainda é preliminar e tem cerca de 7% menos óbitos que 2023. O gráfico anual sinaliza isso.
- Não há população por raça nem por município na base, então as taxas são por UF e o recorte racial usa percentual, não taxa.
- 1,5% dos óbitos têm raça ignorada e ficam no total.
- Estupro e estupro de vulnerável só existem por UF na SINESP.

## 13. Estrutura do repositório e histórico das fases

```
├── terraform/            main.tf, variables.tf, outputs.tf (Aiven PostgreSQL free + usuário do painel)
├── etl/                  extração, tratamento e carga (config.py concentra as regras de recorte)
├── run_pipeline.py       ETL completo
├── sql/                  01 schema, 02 visões, 03 verificação, 04 permissões do painel
├── dashboard/            app.py e consultas.py (Streamlit) + estatico/ (painéis HTML das Fases 2 e 3)
├── analise/              perguntas de pesquisa e figuras da Fase 3
├── saidas/, figuras/     resultados da análise (tabelas, findings.json, PNG)
├── scripts/              tf.sh, carregar_processados.py, verificar_banco.py, verificar_fontes.py
├── tests/                9 testes das regras de tratamento (pytest)
├── .github/workflows/    ci.yml (testes + terraform validate) e fontes.yml (checagem mensal)
├── data/processed/       CSVs tratados (versão resultante)
├── data/raw/manifest.json  hash SHA-256 de cada arquivo original
└── docs/                 documentação de cada fase, relatórios em PDF e evidências do banco
```

| Fase | Entrega | Documento |
|---|---|---|
| 1 | Fontes, V's, tipagem, estratégia para o limite de 1 GB, LGPD | `docs/fase1.md` |
| 2 | ETL, modelo estrela, carga no Aiven | `docs/fase2.md`, `docs/relatorio/` |
| 3 | Análise estatística e recomendações | `docs/relatorio_fase3/`, `analise/` |
| 4 | Terraform, população e taxas, dashboard ao vivo, README final | este README, `docs/pitch/` |
