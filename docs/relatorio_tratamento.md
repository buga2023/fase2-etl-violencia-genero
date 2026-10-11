# Relatório de tratamento e carga

Gerado automaticamente por `run_pipeline.py` em 10/10/2026 20:49.

## 1. Versão original utilizada (data/raw/manifest.json)

| Fonte | Arquivo | Tamanho | SHA-256 (início) |
|---|---|---:|---|
| SINESP-VDE | `sinesp/BancoVDE 2019.xlsx` | 24.2 MB | `01d5cefb6459dadd` |
| SINESP-VDE | `sinesp/BancoVDE 2020.xlsx` | 24.3 MB | `7648a93a473d366f` |
| SINESP-VDE | `sinesp/BancoVDE 2021.xlsx` | 24.3 MB | `babdbbbc71c427e3` |
| SINESP-VDE | `sinesp/BancoVDE 2022.xlsx` | 24.4 MB | `f5561304e9569bc9` |
| SINESP-VDE | `sinesp/BancoVDE 2023.xlsx` | 24.4 MB | `33baf9e4d2ad1052` |
| SINESP-VDE | `sinesp/BancoVDE 2024.xlsx` | 24.4 MB | `87deaea4473cfede` |
| SIM | `sim/Mortalidade_Geral_2019.csv` | 459.9 MB | `05acd2eea5029af6` |
| SIM | `sim/Mortalidade_Geral_2020.csv` | 531.9 MB | `2fdd9fcc8924d8da` |
| SIM | `sim/Mortalidade_Geral_2021.csv` | 632.7 MB | `79cfbfff330f3ee5` |
| SIM | `sim/Mortalidade_Geral_2022.csv` | 44.5 MB | `e0c5c0bc97d1a188` |
| SIM | `sim/Mortalidade_Geral_2022_csv.zip` | 86.9 MB | `10b37a98b9c2ef56` |
| SIM | `sim/Mortalidade_Geral_2023.csv` | 42.3 MB | `28db720ab8fd71f2` |
| SIM | `sim/Mortalidade_Geral_2023_csv.zip` | 86.9 MB | `9a14ef4355b7097c` |
| SIM | `sim/Mortalidade_Geral_2024.csv` | 550.8 MB | `be397f348a6ad25c` |
| IBGE | `ibge/municipios.json` | 2.4 MB | `77bf68d9f5b12375` |

## 2. SINESP-VDE — rastro do tratamento

| Etapa | Linhas / valor |
|---|---:|
| Linhas lidas (todos os arquivos) | 4.588.376 |
| Após recorte 2019–2024 (sem data válida: 0) | 4.588.376 |
| Após filtro de 8 eventos de interesse | 2.436.806 |
| Linhas do escopo com 'agente' preenchida (coluna descartada) | 0 |
| Linhas do escopo com 'arma' preenchida (coluna descartada) | 0 |
| Linhas do escopo com 'faixa_etaria' preenchida (coluna descartada) | 0 |
| Linhas sem quebra por sexo → total atribuído a 'Não informado' | 0 |
| Linhas com soma por sexo ≠ total_vitima (mantida a quebra por sexo) | 0 |
| Duplicatas exatas removidas | 13.743 |
| Linhas descartadas por UF inválida | 0 |
| Nomes de município sem correspondência no IBGE (→ 'NÃO INFORMADO' da UF) | 0 |
| Linhas no fato_vitimas_sinesp (grão final) | 233.988 |
| Total de vítimas no fato (conferência) | 965.890 |

## 3. SIM/DataSUS — rastro do tratamento

| Etapa | Linhas / valor |
|---|---:|
| Declarações de óbito lidas | 9.281.165 |
| Após filtro CID-10 X85–Y09 + sexo feminino | 22.691 |
|   dessas, com DTOBITO inválida | 0 |
| Após recorte 2019–2024 | 22.691 |
| Código de município sem correspondência (→ 'NÃO INFORMADO' da UF) | 1 |
| Descartadas sem UF identificável | 0 |
| Linhas no fato_obitos_agressao_sim (grão final) | 22.006 |
| Total de óbitos no fato (conferência) | 22.691 |

## 4. Base armazenada (schema `vde`)

| Tabela | Registros | Tamanho |
|---|---:|---:|
| dim_uf | 27 | 40 KB |
| dim_tempo | 72 | 40 KB |
| dim_municipio | 5.598 | 1128 KB |
| dim_sexo | 3 | 40 KB |
| dim_raca_cor | 6 | 24 KB |
| dim_faixa_etaria | 9 | 40 KB |
| dim_evento | 8 | 40 KB |
| dim_meio_agressao | 6 | 40 KB |
| fato_vitimas_sinesp | 233.988 | 21392 KB |
| fato_obitos_agressao_sim | 22.006 | 2592 KB |
| meta_carga | 13 | 24 KB |

**Espaço total ocupado:** 26.01 MB de 1.024 MB do Free Tier (2.54%).

### Campos e tipos (lidos do information_schema)

| Tabela | Campo | Tipo | Nulo? |
|---|---|---|---|
| dim_evento | id_evento | smallint | NO |
| dim_evento | nome | character varying | NO |
| dim_evento | grupo | character varying | NO |
| dim_evento | violencia_genero | boolean | NO |
| dim_faixa_etaria | id_faixa | smallint | NO |
| dim_faixa_etaria | descricao | character varying | NO |
| dim_faixa_etaria | idade_min | smallint | YES |
| dim_faixa_etaria | idade_max | smallint | YES |
| dim_meio_agressao | id_meio | smallint | NO |
| dim_meio_agressao | descricao | character varying | NO |
| dim_meio_agressao | cids | character varying | NO |
| dim_municipio | id_municipio | integer | NO |
| dim_municipio | cod_ibge | integer | YES |
| dim_municipio | nome | character varying | NO |
| dim_municipio | nome_normalizado | character varying | NO |
| dim_municipio | cod_uf | smallint | NO |
| dim_raca_cor | id_raca_cor | smallint | NO |
| dim_raca_cor | descricao | character varying | NO |
| dim_raca_cor | negra | boolean | NO |
| dim_sexo | id_sexo | smallint | NO |
| dim_sexo | codigo | character | NO |
| dim_sexo | descricao | character varying | NO |
| dim_tempo | id_tempo | integer | NO |
| dim_tempo | ano | smallint | NO |
| dim_tempo | mes | smallint | NO |
| dim_tempo | trimestre | smallint | NO |
| dim_tempo | data_referencia | date | NO |
| dim_uf | cod_uf | smallint | NO |
| dim_uf | sigla | character | NO |
| dim_uf | nome | character varying | NO |
| dim_uf | regiao | character varying | NO |
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
| meta_carga | fonte | character varying | NO |
| meta_carga | arquivo | character varying | NO |
| meta_carga | sha256 | character | NO |
| meta_carga | tamanho_bytes | bigint | NO |
| meta_carga | linhas_lidas | bigint | NO |
| meta_carga | linhas_apos_filtro | bigint | NO |
| meta_carga | executado_em | timestamp with time zone | NO |
