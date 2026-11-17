# Fase 1: levantamento de parâmetros e tipagem dos dados

Disciplina: Big Data e Analytics (UCSal, 2026/2)
Tema 06: Monitoramento de Segurança Pública e Feminicídio Interseccional
Equipe: Gustavo Souza Santos e Mateus Bulhões
ODS: 5 (Igualdade de Gênero) e 18 (Igualdade Étnico-Racial)

## 1. Problema

Queremos medir a violência letal contra mulheres no Brasil cruzando gênero, raça/cor e idade. O problema é que nenhuma base pública tem tudo isso junto. O registro policial (SINESP) sabe se o crime foi feminicídio, mas não traz a raça da vítima. A declaração de óbito (SIM) traz raça, idade e o meio da agressão, mas não diz se foi feminicídio. Por isso o projeto junta as duas, usando o IBGE para ligar os municípios.

Pergunta central: quem são as mulheres mortas por agressão no Brasil entre 2019 e 2024, como morrem e onde o registro de feminicídio acompanha (ou não) o número de mortes.

## 2. Identificação das fontes

| Fonte | Órgão | Formato de origem | Como chega |
|---|---|---|---|
| SINESP-VDE (BancoVDE) | Ministério da Justiça | XLSX, um arquivo por ano | download direto no gov.br/mj |
| SIM (Declarações de Óbito) | Ministério da Saúde / OpenDataSUS | CSV com `;`, solto (2019 e 2020) ou dentro de ZIP (2021 a 2024) | download no OpenDataSUS (S3) |
| Localidades | IBGE | JSON | API REST `servicodados.ibge.gov.br` |

As três são dados abertos do governo, sem login. O SIM 2024 (`DO24OPEN`) ainda é preliminar e pode ser revisado pelo Ministério da Saúde. Os arquivos de 2022 e 2023 do SIM vêm sem cabeçalho, então o ETL vai precisar de um passo para corrigir isso sem alterar o arquivo original.

## 3. Os V's do Big Data aplicados à base

Em aula vimos os 3 V's de Doug Laney (Volume, Velocidade e Variedade). O guia do projeto pede também Veracidade e Valor, então colocamos os cinco.

- Volume: são 6 planilhas da SINESP (cerca de 24 MB e 765 mil linhas cada) e 6 arquivos anuais do SIM (de 44 MB a 633 MB, entre 1,3 e 1,8 milhão de óbitos por ano). No total dá uns 2,6 GB e perto de 14 milhões de linhas. O SIM não cabe inteiro na memória de um notebook comum.
- Velocidade: as fontes são publicadas em lote, uma vez por ano. Não tem streaming. O pipeline roda em batch e pode ser agendado (por exemplo com GitHub Actions) para pegar o ano novo quando sair.
- Variedade: planilha XLSX, CSV com separador `;`, ZIP e JSON de API. O layout também muda: nome de coluna diferente de um ano para o outro, data em formatos diferentes, SIM com e sem cabeçalho.
- Veracidade: já sabemos de alguns problemas. Raça/cor vem em branco em parte dos óbitos, a SINESP identifica o município só pelo nome (com grafias diferentes do IBGE), contagens vêm como texto com ponto de milhar e o SIM 2024 é preliminar. Tudo isso tem que ser tratado e documentado no ETL.
- Valor: a base cruzada permite responder perguntas que nenhuma fonte responde sozinha, como a proporção de mulheres negras entre as vítimas por estado e se o aumento de feminicídios é aumento de mortes ou de registro. Isso ajuda a orientar política pública (ODS 5 e 18).

## 4. Classificação dos tipos de dados

| Dado | Tipo | Por quê |
|---|---|---|
| SIM (CSV) | estruturado | tabela com colunas fixas e dicionário de dados oficial |
| SINESP (XLSX) | estruturado | tabela, mas com layout que muda entre anos |
| IBGE (JSON da API) | semi-estruturado | objetos aninhados (município → microrregião → UF), sem esquema fixo de tabela |
| Metadados dos arquivos (manifesto com hash, tamanho, data) | semi-estruturado | gerado pelo pipeline em JSON |

Não usamos dado não estruturado (texto livre, imagem). A causa da morte já vem codificada na CID-10.

## 5. Estratégia para o limite de 1 GB do Aiven

O plano gratuito do PostgreSQL no Aiven tem 1 GB. Os dados brutos têm 2,6 GB, então não dá para carregar como estão. A estratégia:

1. Recorte temporal: só 2019 a 2024.
2. Filtro na ingestão do SIM: só causa básica de agressão (CID-10 X85 a Y09) e sexo feminino. Isso deixa uns 3,8 mil óbitos por ano de 1,5 milhão.
3. Filtro de eventos na SINESP: só os indicadores de violência contra a pessoa (feminicídio, homicídio, tentativas, estupro etc.). Apreensão de droga e roubo de carga, por exemplo, ficam de fora.
4. Agregação prévia no ETL: o banco guarda contagens por mês × município × categoria, não uma linha por pessoa. Assim também não levamos dado pessoal para a nuvem.
5. Leitura em blocos (chunks): o SIM é lido em pedaços de 200 mil linhas, lendo só as colunas necessárias, e cada pedaço é filtrado e agregado antes do próximo.

Não vamos usar amostragem estatística. Como o filtro e a agregação já reduzem o volume para poucos MB, dá para trabalhar com a população inteira do recorte, o que é melhor para contar mortes.

## 6. Colunas que passam por conversão de tipo

SIM (só 6 das mais de 80 colunas são lidas):

| Coluna | Como vem | Vira | Observação |
|---|---|---|---|
| `DTOBITO` | texto DDMMAAAA, às vezes sem o zero do dia (`1032019`) | DATE | completar com zero à esquerda antes de converter |
| `SEXO` | texto `2` ou `F` | código da dimensão sexo | os dois valores significam feminino |
| `RACACOR` | texto 1 a 5, vazio | SMALLINT (1 a 5, 9 = ignorada) | criar flag `negra` = preta + parda (critério IBGE) |
| `IDADE` | código de 3 dígitos (1º dígito é a unidade: minutos, horas, dias, meses, anos) | faixa etária | menos de 1 ano vira 0 anos; 999 vira ignorada |
| `CAUSABAS` | texto CID-10 (ex.: `X954`) | meio da agressão (arma de fogo, objeto cortante etc.) | filtro X85 a Y09 por expressão regular |
| `CODMUNOCOR` | texto de 6 dígitos (sem dígito verificador) | código IBGE (INTEGER) | casar com o código IBGE de 7 dígitos dividido por 10 |

SINESP:

| Coluna | Como vem | Vira |
|---|---|---|
| data | data, texto `MM/AAAA` ou ano e mês separados | DATE (dia 01 do mês) |
| feminino, masculino, não informado, total | texto com ponto de milhar (`1.050`) | INTEGER |
| município | nome escrito à mão, com grafias diferentes do IBGE | código IBGE, via nome normalizado + tabela de apelidos |
| evento | texto com e sem acento | id da dimensão evento |

## 7. LGPD

As duas bases são microdados públicos e já saem anonimizadas: o SIM aberto não traz nome, CPF nem endereço da falecida, e a SINESP já vem agregada por município e mês. Mesmo assim, vamos agregar tudo no ETL antes da carga, então nenhuma linha no banco corresponde a uma pessoa. As credenciais do banco ficam em `.env` (fora do Git) e nos secrets da plataforma de deploy, nunca no repositório público.

## 8. Escolha do banco

Relacional (PostgreSQL no Aiven). Os dados são tabelas com chaves claras (tempo, município, sexo, raça), a análise é de contagem e cruzamento com `JOIN` e `GROUP BY`, e a integridade entre as fontes depende de chave estrangeira. Um banco não relacional como o OpenSearch faria sentido para busca em texto livre ou logs, o que não é o caso desta base. A modelagem prevista é um esquema estrela, com as dimensões tempo, município e sexo compartilhadas pelas duas fontes.

## 9. Próximos passos (Fase 2)

- Escrever o ETL em Python (pandas) seguindo as regras acima.
- Provisionar o PostgreSQL no Aiven com Terraform e carregar o modelo estrela.
- Guardar o hash SHA-256 de cada arquivo original para provar qual versão foi usada.
