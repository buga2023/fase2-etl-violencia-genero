# Roteiro de apresentação (10 minutos)

Este é o script da defesa: o que falar em cada bloco, o que mostrar na tela e o que responder nas perguntas. A cola rápida com os números está no fim.

## Antes de começar (10 minutos antes)

- [ ] Abrir o painel publicado e deixar carregado. O Streamlit Cloud dorme depois de um tempo sem acesso e leva uns 30 segundos para acordar.
- [ ] Conferir no console do Aiven se o serviço `pg-feminicidio` está "Running". O plano free desliga se ficar muito tempo sem uso; se estiver desligado, clicar em Power on e esperar de 2 a 5 minutos.
- [ ] Deixar um terminal aberto na pasta do repositório, para o `./scripts/tf.sh plan` (o esperado é "No changes").
- [ ] Plano B sem internet: `streamlit run dashboard/app.py` na máquina local, que usa o mesmo banco.
- [ ] Plano B se o banco não responder: abrir os painéis estáticos em `dashboard/estatico/` (HTML com os dados embutidos, funciona offline).

## Divisão

| Tempo | Bloco | Quem |
|---|---|---|
| 0:00 a 1:40 | capa, problema e fontes | Gustavo |
| 1:40 a 3:40 | arquitetura, stack e infraestrutura | Gustavo |
| 3:40 a 5:20 | tratamento, modelo e regras | Mateus |
| 5:20 a 7:30 | KPIs e achados | Mateus |
| 7:30 a 9:00 | demo ao vivo do painel | Gustavo |
| 9:00 a 10:00 | limitações, ODS e fechamento | Mateus |

Se a apresentação for individual, corte o bloco de arquitetura para 1 minuto e faça a demo você mesmo; o resto do roteiro continua igual.

## 0:00 a 1:40 — Capa, problema e fontes (Gustavo)

**Fala de abertura**

"Bom dia. A gente vai apresentar o projeto de Big Data e Analytics sobre feminicídio interseccional no Brasil, tema 06 da disciplina. A pergunta que guiou tudo foi: quem são as mulheres mortas por agressão no país entre 2019 e 2024, como morrem, onde o risco é maior e até que ponto o Estado nomeia essas mortes como feminicídio."

**O problema**

"Nenhuma fonte pública responde isso sozinha. A SINESP-VDE, do Ministério da Justiça, é o registro policial: ela diz se o caso foi feminicídio, mas não registra a raça da vítima. O SIM, do DataSUS, é a declaração de óbito: tem raça/cor, idade e meio da agressão, mas não diz se o caso foi tratado como feminicídio. A nossa saída foi cruzar as duas fontes, usando o IBGE para ligar os municípios e fornecer a população feminina, que é o denominador das taxas."

"É isso que permite o recorte interseccional: gênero, raça, idade e território na mesma análise. O projeto dialoga com a ODS 5, de igualdade de gênero, e com a ODS 18, de igualdade étnico-racial."

**Transição**

"Para juntar essas bases, a gente montou um pipeline que vai da extração até o painel."

## 1:40 a 3:40 — Arquitetura e infraestrutura (Gustavo)

Mostrar o diagrama de arquitetura do README ou do relatório.

**Fala**

"O fluxo tem quatro partes. Primeiro a extração: o `extract.py` baixa os arquivos oficiais da SINESP, do SIM e do IBGE e grava o SHA-256 de cada um no manifesto. Depois o tratamento: os `transform_*.py` limpam, tipam e agregam os dados. A carga usa `COPY` numa transação só. E o banco é um PostgreSQL 18 no Aiven, no plano free de 1 GB, provisionado por Terraform."

"O painel é um app Streamlit publicado no Streamlit Cloud. Ele não tem dado embutido: cada filtro roda SQL no banco com um usuário que só tem SELECT. O Terraform cria esse usuário e o serviço; o GitHub Actions roda os testes a cada push e confere uma vez por mês se as fontes publicaram arquivo novo."

**Por que não Spark**

"A disciplina fala de Spark e Hadoop, e a pergunta é justa. A gente não usou porque o volume não pedia: são uns 2,6 GB brutos e 13,9 milhões de linhas. O pandas lendo em blocos de 200 mil linhas processa isso num notebook comum, com memória constante. Um cluster só traria custo e complexidade. Se a base crescesse para dezenas de GB, como pegar o SIM desde 1996, aí sim valeria trocar por PySpark, reaproveitando as regras que já estão no `etl/config.py`."

**Transição**

"Com o desenho pronto, o trabalho maior foi o tratamento."

## 3:40 a 5:20 — Tratamento, modelo e regras (Mateus)

**Fala**

"O tratamento virou 18 regras documentadas. Três exemplos mostram o tipo de problema que apareceu."

"Primeiro, o Distrito Federal. A SINESP lança uma linha por região administrativa, todas com o nome 'Brasília'. Parecia duplicata, e na primeira versão a gente removia essas linhas. Só que isso apagava cerca de 60% das vítimas do DF. A regra final remove apenas a mesma linha repetida em outro arquivo; repetição dentro do mesmo arquivo é somada."

"Segundo, a idade do SIM. O campo tem a unidade no primeiro dígito: minutos, horas, dias, meses ou anos. Se a gente lesse como número puro, um bebê de 3 meses viraria 3 anos. A regra trata unidade 0 a 3 como menos de 1 ano, e 999 como ignorada."

"Terceiro, o município. A SINESP só tem o nome escrito à mão, com grafias diferentes do IBGE. A gente normaliza o nome, aplica uma tabela de apelidos e, quando não acha par, joga para a linha 'NÃO INFORMADO' da UF, sem perder o total do estado."

**Modelo**

"O modelo é um esquema estrela com duas tabelas fato, porque as fontes têm grãos diferentes. A SINESP conta vítimas por evento e sexo; o SIM conta óbitos por raça, idade e meio. Tempo, município e sexo são dimensões compartilhadas, e é isso que permite cruzar as duas."

"Depois do tratamento, 13,9 milhões de linhas viraram 256 mil, e o schema ocupa uns 25 MB, cerca de 2,5% do 1 GB do plano free. A base tem 233.988 linhas na fato da SINESP, com 968.489 vítimas, e 22.005 linhas na fato do SIM, com 22.691 óbitos."

**Transição**

"Com a base carregada, a gente chegou nos indicadores."

## 5:20 a 7:30 — KPIs e achados (Mateus)

Mostrar os cards do painel.

**Os quatro indicadores**

"O painel abre com quatro indicadores para o Brasil inteiro, de 2019 a 2024. A taxa de óbitos de mulheres por agressão ficou em 3,51 por 100 mil. As vítimas negras são 67,1% do total. A SINESP registrou 8.423 feminicídios de mulheres, uma alta de 13% no período. E 37,1% das mortes de mulheres por agressão aparecem como feminicídio no registro policial."

"Também mostramos que 49,1% dos óbitos foram por arma de fogo."

**Achado 1: registro sobe, morte não**

"O primeiro achado é o mais importante. O registro de feminicídio cresce, mas as mortes não. Considerando todas as vítimas do evento, como faz o Anuário do FBSP, os feminicídios subiram 12,8% de 2019 a 2024. A regressão dá R² de 0,94 e p igual a 0,002. Já a taxa de óbitos por agressão ficou perto de 3,5 por 100 mil, sem tendência: p igual a 0,675. Ou seja, o que cresceu foi a classificação dos casos como feminicídio, não a violência letal. Para a ODS 5 isso é avanço no reconhecimento, mas não é redução."

**Achado 2: o risco é desigual**

"O segundo achado é territorial. São Paulo tem o maior número absoluto, mas a menor taxa do país: 1,59 por 100 mil. Roraima chega a 9,49, quase seis vezes mais. Norte e Nordeste ficam bem acima do Sudeste. Por isso o painel abre pela taxa, e não pelo número absoluto."

**Achado 3: raça e perfil**

"O terceiro achado é o recorte racial. Duas em cada três vítimas são negras, e isso não mudou em seis anos: fica entre 66% e 68%. O percentual vai de cerca de 20% em Santa Catarina e no Rio Grande do Sul a mais de 90% em Alagoas, Amapá, Sergipe e Ceará. A faixa de 18 a 39 anos concentra 57% das mortes. E a classificação varia muito: o Ceará tem taxa de óbitos alta, 5,90, e taxa de feminicídio baixa, 0,72; Mato Grosso registra 2,59. Isso sugere subnotificação desigual."

**Validação**

"Os números batem com quem publica sobre o tema. O Anuário do FBSP tem 1.492 feminicídios em 2024, 1.504 na revisão; a nossa base tem 1.501, contando todas as vítimas do evento. O Atlas da Violência tem 3.903 mulheres assassinadas em 2023, 68,2% negras; a nossa base tem 3.887 e 68,1%."

**Transição**

"Quem quiser conferir isso ao vivo, o painel está publicado. Vou mostrar."

## 7:30 a 9:00 — Demo ao vivo (Gustavo)

Roteiro de cliques, nessa ordem:

1. Abrir https://feminicidio-interseccional.streamlit.app e esperar os cards carregarem.
2. Apontar os quatro cards e ler só dois números: 3,51 por 100 mil e 67,1% de vítimas negras.
3. Mostrar que o filtro de sexo já vem em "Feminino" e que o período é 2019 a 2024.
4. No seletor de métrica, alternar entre "Taxa de óbitos" e "Feminicídios registrados" para mostrar que as curvas contam histórias diferentes.
5. Clicar numa barra do ranking de regiões, descer para estado e depois para município. Mostrar Roraima ou São Paulo, que são os extremos. Usar o botão de voltar.
6. Abrir "Ver as consultas e o tempo de cada uma" e mostrar que o painel está consultando o banco naquele momento, com o tempo em milissegundos.
7. Exportar a tabela do recorte em CSV.
8. Se sobrar tempo, rodar `./scripts/tf.sh plan` e mostrar "No changes", provando que a infraestrutura está versionada.

**Frase de fechamento da demo**

"Tudo o que vocês viram é SQL ao vivo no PostgreSQL. O app não tem CSV embutido e o usuário do painel só tem permissão de leitura."

## 9:00 a 10:00 — Limitações e fechamento (Mateus)

**Limitações**

"Três limitações importantes. Primeiro, feminicídio e óbito por agressão são conceitos próximos, mas não iguais; o KPI de captação é indicativo, não uma taxa exata de subnotificação. Segundo, o SIM de 2024 ainda é preliminar e tem cerca de 7% menos óbitos que 2023. Terceiro, não existe população por raça nem por município na base, então as taxas são por UF e o recorte racial usa percentual."

**Fechamento**

"O que fica do projeto: um pipeline reprodutível, com hash de cada arquivo original, testes automatizados e um painel que consulta o banco ao vivo. E um resultado que conversa com as duas ODS: o reconhecimento do feminicídio avançou, mas a violência letal contra mulheres não caiu, e o risco continua muito desigual entre os estados."

"Obrigado. A gente fica à disposição para as perguntas."

## Números para decorar

| Indicador | Valor |
|---|---|
| Taxa de óbitos por agressão | 3,51 por 100 mil mulheres |
| Vítimas negras | 67,1% |
| Feminicídios registrados (mulheres) | 8.423, alta de 13,0% de 2019 a 2024 |
| Mortes nomeadas como feminicídio | 37,1% |
| Arma de fogo | 49,1% dos óbitos |
| Faixa de 18 a 39 anos | 57% das mortes |
| Maior e menor taxa por UF | RR 9,49 e SP 1,59 |
| Regiões | Norte 5,14, Nordeste 4,85, Centro-Oeste 4,02, Sul 3,45, Sudeste 2,25 |
| Volume bruto | 2,6 GB e 13,9 milhões de linhas |
| Depois do ETL | 256 mil linhas e uns 25 MB no banco |
| Linhas carregadas | 233.988 na SINESP (968.489 vítimas) e 22.005 no SIM (22.691 óbitos) |
| Regras e testes | 18 regras de tratamento e 9 testes automatizados |

## Perguntas prováveis

**Por que vocês não usaram Spark ou Hadoop, se a disciplina fala deles?**
Porque o volume não pedia. São uns 2,6 GB brutos, e o pandas lendo em blocos de 200 mil linhas processa tudo num notebook comum com memória constante. Spark faz sentido quando o dado não cabe numa máquina. Se a gente pegasse o SIM desde 1996, ou microdados de outras bases grandes, a troca seria PySpark, mantendo as mesmas regras do `etl/config.py`.

**Como vocês lidaram com o limite de 1 GB do Aiven?**
Filtrando na leitura (só agressão, só mulheres, só 6 colunas) e agregando por mês, município e categoria antes de carregar. 13,9 milhões de linhas viraram 256 mil. O schema ocupa uns 25 MB, cerca de 2,5% do plano.

**O painel consulta mesmo o banco ou os dados estão no arquivo?**
Consulta o banco. Não tem nenhum CSV no app. Cada filtro roda SQL no Aiven com o usuário `painel_leitura`. Dá para ver em "Ver as consultas", com o horário e os milissegundos de cada uma. Tem um cache de 2 minutos para não sobrecarregar o plano free, e o botão "Consultar o banco de novo" limpa esse cache.

**Onde ficam as senhas?**
Em nenhum arquivo do repositório. Local, no `.env` e no `.streamlit/secrets.toml`, que estão no `.gitignore`. No Streamlit Cloud, em Secrets. O token do Aiven só é lido pelo `scripts/tf.sh`. E o painel usa um usuário que só tem SELECT: se a senha dele vazar, ninguém consegue apagar nada.

**Por que relacional e não OpenSearch?**
Os dados são tabelas com chaves, a análise é JOIN e GROUP BY, e a integridade entre as duas fontes depende de chave estrangeira. OpenSearch é bom para busca em texto livre e logs, que não temos.

**Como vocês sabem que o tratamento está certo?**
Três coisas. Os totais batem antes e depois de cada etapa (o relatório de tratamento mostra). Tem 9 testes automatizados com arquivos sintéticos que têm os defeitos reais. E o resultado bate com quem publica: 1.501 feminicídios em 2024, contra 1.504 do FBSP, e 68,1% de vítimas negras em 2023, contra 68,2% do Atlas da Violência.

**Feminicídio e óbito por agressão não são a mesma coisa. Por que comparar?**
Não são, e a gente deixa isso claro. Feminicídio é a classificação policial de um crime por razão de gênero. Óbito por agressão é toda mulher morta por violência. Por isso o KPI de captação (37%) é um indicador de quanto das mortes é reconhecido como feminicídio, não uma taxa exata de subnotificação.

**Por que o KPI de captação some quando filtro por raça?**
Porque raça, idade e meio só existem no SIM. A SINESP não registra a raça, então não dá para dividir feminicídios de mulheres negras por óbitos de mulheres negras. Em vez de mostrar uma conta errada, o painel deixa o card em branco e explica.

**Por que 2024 cai no gráfico?**
O SIM de 2024 ainda é preliminar, com uns 7% menos óbitos que 2023. O próprio gráfico avisa. Quando o DataSUS publicar a versão final, é só rodar o pipeline de novo.

**O que é o V de Velocidade no projeto de vocês?**
As fontes saem em lote, uma vez por ano, então não tem streaming. O que fizemos foi um GitHub Actions que roda todo dia 1º e confere se MJSP, DataSUS ou IBGE publicaram arquivo novo. Ele já achou o SINESP 2025 e revisões do SIM 2022 e 2023.

**Como a LGPD entra?**
As bases já são abertas e anonimizadas, mas mesmo assim lemos só as colunas necessárias e agregamos tudo, então nenhuma linha do banco é uma pessoa. E as credenciais nunca vão para o repositório público.

**Por que a taxa é por UF e não por município?**
A projeção de população do IBGE por sexo é por UF. No nível de município o painel mostra número absoluto e avisa isso.

**O que deu errado no caminho?**
O DF: a SINESP lança uma linha por região administrativa, todas como "Brasília". Parecia duplicata, e na primeira versão a gente apagava 60% das vítimas do DF. E o banco da Fase 2, criado pelo console num plano de trial, desligou quando o trial acabou. Recriamos pelo Terraform no plano free.
