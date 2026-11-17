# Pitch de 10 minutos: roteiro e defesa

Slides: https://claude.ai/artifact/BeRfLyGcVTFiRZSFX7izEf (as falas de cada slide estão nas notas do apresentador; dá para baixar em PPTX ou PDF pelo menu da página).

## Divisão sugerida

| Tempo | Slide | Quem |
|---|---|---|
| 0:00 a 1:40 | capa, problema | Gustavo |
| 1:40 a 3:40 | arquitetura, Terraform (se der tempo, rodar `./scripts/tf.sh plan` ao vivo) | Gustavo |
| 3:40 a 5:20 | tratamento, modelo e regras | Mateus |
| 5:20 a 7:30 | KPIs, achado 1, achado 2 | Mateus |
| 7:30 a 9:00 | demo ao vivo do painel | Gustavo |
| 9:00 a 10:00 | decisões técnicas, fechamento | Mateus |

## Checklist antes de apresentar

- [ ] Abrir o painel publicado uns 10 minutos antes. O Streamlit Cloud "dorme" depois de um tempo sem acesso e leva uns 30 s para acordar.
- [ ] Conferir se o serviço `pg-feminicidio` está "Running" no console do Aiven. O plano free desliga se ficar muito tempo sem uso. Se estiver desligado, clicar em Power on (2 a 5 minutos).
- [ ] Terminal aberto na pasta do repositório para o `./scripts/tf.sh plan`. O esperado é "No changes".
- [ ] Plano B sem internet do Cloud: `streamlit run dashboard/app.py` local, que usa o mesmo banco.

## Números do painel (filtro padrão Sexo = Feminino, 2019 a 2024)

São os mesmos dos cards do painel e do slide 7. Vale decorar.

| Indicador | Valor |
|---|---|
| Taxa de óbitos por agressão | 3,51 por 100 mil mulheres |
| Vítimas negras | 67,1% |
| Feminicídios registrados (vítimas mulheres) | 8.423, alta de 13,0% de 2019 a 2024 |
| Mortes nomeadas como feminicídio | 37,1% |
| Arma de fogo | 49,1% dos óbitos |
| Maior e menor taxa por UF | RR 9,49 · SP 1,59 |
| Regiões | Norte 5,14 · Nordeste 4,85 · Centro-Oeste 4,02 · Sul 3,45 · Sudeste 2,25 |

O +12,8% do slide 8 conta todas as vítimas do evento Feminicídio (critério do FBSP). O +13,0% do card conta só mulheres, porque o painel abre com o filtro Sexo = Feminino.

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
Três coisas. Os totais batem antes e depois de cada etapa (o relatório de tratamento mostra). Tem 9 testes automatizados com arquivos sintéticos que têm os defeitos reais. E o resultado bate com quem publica: 1.501 feminicídios em 2024 (todas as vítimas, mesmo critério do Anuário) contra 1.504 do FBSP, e 68,1% de vítimas negras em 2023 contra 68,2% do Atlas da Violência.

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
