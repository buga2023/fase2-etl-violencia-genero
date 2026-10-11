# Verificação do banco (sql/03_verificacao.sql)

Executado em 10/10/2026 23:37.

Servidor: `PostgreSQL 18.6 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 15.3.1 20260722 (Red Hat 15.3.1-1), 64-bit`

## 1. Registros por tabela

| tabela | count |
|---|---|
| dim_tempo | 72 |
| dim_uf | 27 |
| dim_municipio | 5598 |
| dim_sexo | 3 |
| dim_raca_cor | 6 |
| dim_faixa_etaria | 9 |
| dim_evento | 8 |
| dim_meio_agressao | 6 |
| fato_vitimas_sinesp | 233988 |
| fato_obitos_agressao_sim | 22005 |
| meta_carga | 13 |

## 2. Espaço ocupado pelo schema vde

| tamanho_schema_vde |
|---|
| 25 MB |

## 3. Campos e tipos

| table_name | column_name | data_type | is_nullable |
|---|---|---|---|
| dim_evento | id_evento | smallint | NO |
| dim_evento | nome | character varying(80) | NO |
| dim_evento | grupo | character varying(20) | NO |
| dim_evento | violencia_genero | boolean | NO |
| dim_faixa_etaria | id_faixa | smallint | NO |
| dim_faixa_etaria | descricao | character varying(15) | NO |
| dim_faixa_etaria | idade_min | smallint | YES |
| dim_faixa_etaria | idade_max | smallint | YES |
| dim_meio_agressao | id_meio | smallint | NO |
| dim_meio_agressao | descricao | character varying(40) | NO |
| dim_meio_agressao | cids | character varying(40) | NO |
| dim_municipio | id_municipio | integer | NO |
| dim_municipio | cod_ibge | integer | YES |
| dim_municipio | nome | character varying(80) | NO |
| dim_municipio | nome_normalizado | character varying(80) | NO |
| dim_municipio | cod_uf | smallint | NO |
| dim_raca_cor | id_raca_cor | smallint | NO |
| dim_raca_cor | descricao | character varying(15) | NO |
| dim_raca_cor | negra | boolean | NO |
| dim_sexo | id_sexo | smallint | NO |
| dim_sexo | codigo | character(1) | NO |
| dim_sexo | descricao | character varying(15) | NO |
| dim_tempo | id_tempo | integer | NO |
| dim_tempo | ano | smallint | NO |
| dim_tempo | mes | smallint | NO |
| dim_tempo | trimestre | smallint | NO |
| dim_tempo | data_referencia | date | NO |
| dim_uf | cod_uf | smallint | NO |
| dim_uf | sigla | character(2) | NO |
| dim_uf | nome | character varying(30) | NO |
| dim_uf | regiao | character varying(15) | NO |
| fato_obitos_agressao_sim | id_tempo | integer | NO |
| fato_obitos_agressao_sim | id_municipio | integer | NO |
| fato_obitos_agressao_sim | id_sexo | smallint | NO |
| fato_obitos_agressao_sim | id_raca_cor | smallint | NO |
| fato_obitos_agressao_sim | id_faixa | smallint | NO |
| fato_obitos_agressao_sim | id_meio | smallint | NO |
| fato_obitos_agressao_sim | qt_obitos | integer | NO |
| fato_vitimas_sinesp | id_tempo | integer | NO |
| fato_vitimas_sinesp | id_municipio | integer | NO |
| fato_vitimas_sinesp | id_evento | smallint | NO |
| fato_vitimas_sinesp | id_sexo | smallint | NO |
| fato_vitimas_sinesp | qt_vitimas | integer | NO |
| meta_carga | id_carga | integer | NO |
| meta_carga | fonte | character varying(20) | NO |
| meta_carga | arquivo | character varying(200) | NO |
| meta_carga | sha256 | character(64) | NO |
| meta_carga | tamanho_bytes | bigint | NO |
| meta_carga | linhas_lidas | bigint | NO |
| meta_carga | linhas_apos_filtro | bigint | NO |
| meta_carga | arquivo_origem | character varying(200) | YES |
| meta_carga | sha256_origem | character(64) | YES |
| meta_carga | executado_em | timestamp with time zone | NO |

## 4. Relacionamentos (chaves estrangeiras)

| tabela | coluna | referencia | coluna_ref |
|---|---|---|---|
| dim_municipio | cod_uf | dim_uf | cod_uf |
| fato_obitos_agressao_sim | id_faixa | dim_faixa_etaria | id_faixa |
| fato_obitos_agressao_sim | id_meio | dim_meio_agressao | id_meio |
| fato_obitos_agressao_sim | id_municipio | dim_municipio | id_municipio |
| fato_obitos_agressao_sim | id_raca_cor | dim_raca_cor | id_raca_cor |
| fato_obitos_agressao_sim | id_sexo | dim_sexo | id_sexo |
| fato_obitos_agressao_sim | id_tempo | dim_tempo | id_tempo |
| fato_vitimas_sinesp | id_evento | dim_evento | id_evento |
| fato_vitimas_sinesp | id_municipio | dim_municipio | id_municipio |
| fato_vitimas_sinesp | id_sexo | dim_sexo | id_sexo |
| fato_vitimas_sinesp | id_tempo | dim_tempo | id_tempo |

## 5. Linhagem (meta_carga)

| fonte | arquivo | sha256 | arquivo_origem | sha256_origem | linhas_lidas | linhas_apos_filtro | executado_em |
|---|---|---|---|---|---|---|---|
| SINESP-VDE | BancoVDE 2019.xlsx | 01d5cefb6459 |  |  | 764700 | 406116 | 2026-10-11 02:37:26.551589+00:00 |
| SINESP-VDE | BancoVDE 2020.xlsx | 7648a93a473d |  |  | 764700 | 406116 | 2026-10-11 02:37:26.551589+00:00 |
| SINESP-VDE | BancoVDE 2021.xlsx | babdbbbc71c4 |  |  | 764732 | 406136 | 2026-10-11 02:37:26.551589+00:00 |
| SINESP-VDE | BancoVDE 2022.xlsx | f5561304e956 |  |  | 764652 | 406086 | 2026-10-11 02:37:26.551589+00:00 |
| SINESP-VDE | BancoVDE 2023.xlsx | 33baf9e4d2ad |  |  | 764772 | 406161 | 2026-10-11 02:37:26.551589+00:00 |
| SINESP-VDE | BancoVDE 2024.xlsx | 87deaea4473c |  |  | 764820 | 406191 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2019.csv | 05acd2eea502 |  |  | 1349801 | 3728 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2020.csv | 2fdd9fcc8924 |  |  | 1556824 | 3822 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2021.csv | 79cfbfff330f | Mortalidade_Geral_2021_csv.zip | 6a8fe8077cf1 | 1832649 | 3844 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2022.csv | e0c5c0bc97d1 | Mortalidade_Geral_2022_csv.zip | 10b37a98b9c2 | 1544266 | 3788 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2023.csv | 28db720ab8fd | Mortalidade_Geral_2023_csv.zip | 9a14ef4355b7 | 1465610 | 3887 | 2026-10-11 02:37:26.551589+00:00 |
| SIM | Mortalidade_Geral_2024.csv | be397f348a6a | DO24OPEN_csv.zip | 13db250c9090 | 1532015 | 3622 | 2026-10-11 02:37:26.551589+00:00 |
| IBGE | municipios.json | 77bf68d9f5b1 |  |  | 5571 | 5571 | 2026-10-11 02:37:26.551589+00:00 |

## 6. Amostra de vw_comparativo_uf_ano

| ano | uf | regiao | feminicidios_sinesp | feminicidios_mulheres_sinesp | vitimas_letais_mulheres_sinesp | obitos_agressao_mulheres_sim | obitos_mulheres_negras_sim | pct_mulheres_negras_sim |
|---|---|---|---|---|---|---|---|---|
| 2024 | BA | Nordeste | 110 | 110 | 403 | 405 | 356 | 87.9 |
| 2024 | SP | Sudeste | 253 | 251 | 447 | 348 | 140 | 40.2 |
| 2024 | PE | Nordeste | 76 | 76 | 264 | 273 | 221 | 81.0 |
| 2024 | CE | Nordeste | 41 | 41 | 312 | 269 | 251 | 93.3 |
| 2024 | MG | Sudeste | 169 | 169 | 358 | 266 | 178 | 66.9 |
| 2024 | RJ | Sudeste | 107 | 104 | 350 | 261 | 169 | 64.8 |
| 2024 | PR | Sul | 109 | 109 | 259 | 234 | 88 | 37.6 |
| 2024 | RS | Sul | 73 | 73 | 205 | 202 | 39 | 19.3 |
| 2024 | PA | Norte | 52 | 52 | 188 | 168 | 144 | 85.7 |
| 2024 | MA | Nordeste | 69 | 69 | 156 | 154 | 131 | 85.1 |
