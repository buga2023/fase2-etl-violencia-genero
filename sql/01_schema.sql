-- =====================================================================
-- Fase 2 — Modelo dimensional (esquema estrela) — PostgreSQL (Aiven)
-- Tema: Monitoramento de Segurança Pública e Feminicídio Interseccional
-- Fontes: SINESP-VDE/MJSP (ocorrências/vítimas) + SIM/DataSUS (óbitos por agressão)
--
-- Duas tabelas fato com grãos diferentes compartilhando dimensões
-- conformadas (tempo, município/UF, sexo). É isso que permite cruzar
-- as duas fontes: a SINESP traz gênero, o SIM traz raça/cor.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS vde;
SET search_path TO vde;

-- Ordem de DROP respeita as FKs (fatos antes das dimensões)
DROP VIEW  IF EXISTS vw_comparativo_uf_ano, vw_obitos_mulheres_raca_uf_ano,
                     vw_vitimas_genero_uf_ano CASCADE;
DROP TABLE IF EXISTS fato_vitimas_sinesp, fato_obitos_agressao_sim, meta_carga,
                     dim_tempo, dim_municipio, dim_uf, dim_sexo, dim_raca_cor,
                     dim_faixa_etaria, dim_evento, dim_meio_agressao CASCADE;

-- ---------------------------------------------------------------------
-- DIMENSÕES
-- ---------------------------------------------------------------------

-- Tempo no grão mensal. Chave inteligente AAAAMM: legível e ordenável.
CREATE TABLE dim_tempo (
    id_tempo        INTEGER     PRIMARY KEY,                 -- ex.: 202403
    ano             SMALLINT    NOT NULL CHECK (ano BETWEEN 2000 AND 2100),
    mes             SMALLINT    NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre       SMALLINT    NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    data_referencia DATE        NOT NULL UNIQUE                -- sempre dia 01
);

CREATE TABLE dim_uf (
    cod_uf  SMALLINT    PRIMARY KEY,                           -- código IBGE (29 = BA)
    sigla   CHAR(2)     NOT NULL UNIQUE,
    nome    VARCHAR(30) NOT NULL,
    regiao  VARCHAR(15) NOT NULL
);

-- Chave substituta porque a SINESP identifica o município pelo NOME
-- e o SIM pelo CÓDIGO de 6 dígitos. O cod_ibge (7 dígitos) é a ponte.
-- Linhas "NÃO INFORMADO" (cod_ibge NULL) recebem registros sem município.
CREATE TABLE dim_municipio (
    id_municipio      SERIAL      PRIMARY KEY,
    cod_ibge          INTEGER     UNIQUE,                      -- 7 dígitos; NULL = não informado
    nome              VARCHAR(80) NOT NULL,
    nome_normalizado  VARCHAR(80) NOT NULL,                    -- sem acento, caixa alta (chave de join por nome)
    cod_uf            SMALLINT    NOT NULL REFERENCES dim_uf (cod_uf),
    UNIQUE (cod_uf, nome_normalizado)
);

CREATE TABLE dim_sexo (
    id_sexo    SMALLINT    PRIMARY KEY,
    codigo     CHAR(1)     NOT NULL UNIQUE,                    -- F / M / I
    descricao  VARCHAR(15) NOT NULL
);

-- Domínio IBGE de raça/cor (mesma codificação do SIM) + 9 = Ignorada
CREATE TABLE dim_raca_cor (
    id_raca_cor SMALLINT    PRIMARY KEY,
    descricao   VARCHAR(15) NOT NULL,
    negra       BOOLEAN     NOT NULL                           -- preta + parda (agregado usado pelo IBGE/FBSP)
);

CREATE TABLE dim_faixa_etaria (
    id_faixa   SMALLINT    PRIMARY KEY,
    descricao  VARCHAR(15) NOT NULL UNIQUE,
    idade_min  SMALLINT,
    idade_max  SMALLINT
);

CREATE TABLE dim_evento (
    id_evento          SMALLINT     PRIMARY KEY,
    nome               VARCHAR(80)  NOT NULL UNIQUE,
    grupo              VARCHAR(20)  NOT NULL,                  -- Letal / Tentativa / Sexual
    violencia_genero   BOOLEAN      NOT NULL                   -- tipificado por gênero (feminicídio)
);

-- Agrupamento da causa básica CID-10 (X85–Y09) pelo meio da agressão
CREATE TABLE dim_meio_agressao (
    id_meio    SMALLINT    PRIMARY KEY,
    descricao  VARCHAR(40) NOT NULL UNIQUE,
    cids       VARCHAR(40) NOT NULL
);

-- ---------------------------------------------------------------------
-- FATOS
-- ---------------------------------------------------------------------

-- Grão: mês × município × evento × sexo da vítima  → quantidade de vítimas
CREATE TABLE fato_vitimas_sinesp (
    id_tempo      INTEGER  NOT NULL REFERENCES dim_tempo (id_tempo),
    id_municipio  INTEGER  NOT NULL REFERENCES dim_municipio (id_municipio),
    id_evento     SMALLINT NOT NULL REFERENCES dim_evento (id_evento),
    id_sexo       SMALLINT NOT NULL REFERENCES dim_sexo (id_sexo),
    qt_vitimas    INTEGER  NOT NULL CHECK (qt_vitimas > 0),
    PRIMARY KEY (id_tempo, id_municipio, id_evento, id_sexo)
);

-- Grão: mês × município de ocorrência × raça/cor × faixa etária × meio
--       (somente vítimas do sexo feminino)  → quantidade de óbitos
CREATE TABLE fato_obitos_agressao_sim (
    id_tempo      INTEGER  NOT NULL REFERENCES dim_tempo (id_tempo),
    id_municipio  INTEGER  NOT NULL REFERENCES dim_municipio (id_municipio),
    id_sexo       SMALLINT NOT NULL REFERENCES dim_sexo (id_sexo) CHECK (id_sexo = 1),  -- só mulheres
    id_raca_cor   SMALLINT NOT NULL REFERENCES dim_raca_cor (id_raca_cor),
    id_faixa      SMALLINT NOT NULL REFERENCES dim_faixa_etaria (id_faixa),
    id_meio       SMALLINT NOT NULL REFERENCES dim_meio_agressao (id_meio),
    qt_obitos     INTEGER  NOT NULL CHECK (qt_obitos > 0),
    PRIMARY KEY (id_tempo, id_municipio, id_sexo, id_raca_cor, id_faixa, id_meio)
);

-- Índices para os filtros mais comuns (a PK já cobre id_tempo)
CREATE INDEX ix_sinesp_municipio ON fato_vitimas_sinesp (id_municipio);
CREATE INDEX ix_sinesp_evento    ON fato_vitimas_sinesp (id_evento);
CREATE INDEX ix_sim_municipio    ON fato_obitos_agressao_sim (id_municipio);
CREATE INDEX ix_sim_raca         ON fato_obitos_agressao_sim (id_raca_cor);
CREATE INDEX ix_mun_uf           ON dim_municipio (cod_uf);

-- ---------------------------------------------------------------------
-- LINHAGEM: cada arquivo de origem carregado, com hash da versão original
-- ---------------------------------------------------------------------
CREATE TABLE meta_carga (
    id_carga            SERIAL       PRIMARY KEY,
    fonte               VARCHAR(20)  NOT NULL,                 -- SINESP-VDE / SIM / IBGE
    arquivo             VARCHAR(200) NOT NULL,
    sha256              CHAR(64)     NOT NULL,
    tamanho_bytes       BIGINT       NOT NULL,
    linhas_lidas        BIGINT       NOT NULL,
    linhas_apos_filtro  BIGINT       NOT NULL,
    arquivo_origem      VARCHAR(200),                          -- arquivo oficial quando 'arquivo' é derivado
    sha256_origem       CHAR(64),                              -- (SIM 2022/2023: ZIP sem cabeçalho → CSV padronizado)
    executado_em        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
