-- Visões analíticas prontas para a Fase 3 (dashboards / KPIs)
SET search_path TO vde;

-- Vítimas por gênero, UF, ano e evento (SINESP)
CREATE OR REPLACE VIEW vw_vitimas_genero_uf_ano AS
SELECT t.ano, u.sigla AS uf, u.regiao, e.nome AS evento, s.descricao AS sexo,
       SUM(f.qt_vitimas) AS vitimas
FROM fato_vitimas_sinesp f
JOIN dim_tempo     t ON t.id_tempo     = f.id_tempo
JOIN dim_municipio m ON m.id_municipio = f.id_municipio
JOIN dim_uf        u ON u.cod_uf       = m.cod_uf
JOIN dim_evento    e ON e.id_evento    = f.id_evento
JOIN dim_sexo      s ON s.id_sexo      = f.id_sexo
GROUP BY t.ano, u.sigla, u.regiao, e.nome, s.descricao;

-- Óbitos de mulheres por agressão por raça/cor, UF e ano (SIM)
CREATE OR REPLACE VIEW vw_obitos_mulheres_raca_uf_ano AS
SELECT t.ano, u.sigla AS uf, u.regiao, r.descricao AS raca_cor, r.negra,
       SUM(f.qt_obitos) AS obitos
FROM fato_obitos_agressao_sim f
JOIN dim_tempo     t ON t.id_tempo     = f.id_tempo
JOIN dim_municipio m ON m.id_municipio = f.id_municipio
JOIN dim_uf        u ON u.cod_uf       = m.cod_uf
JOIN dim_raca_cor  r ON r.id_raca_cor  = f.id_raca_cor
GROUP BY t.ano, u.sigla, u.regiao, r.descricao, r.negra;

-- Ponte interseccional: as duas fontes lado a lado no grão UF × ano
CREATE OR REPLACE VIEW vw_comparativo_uf_ano AS
WITH sinesp AS (
    SELECT t.ano, m.cod_uf,
           SUM(f.qt_vitimas) FILTER (WHERE e.violencia_genero AND e.grupo = 'Letal') AS feminicidios,
           SUM(f.qt_vitimas) FILTER (WHERE e.violencia_genero AND e.grupo = 'Letal' AND s.codigo = 'F') AS feminicidios_f,
           SUM(f.qt_vitimas) FILTER (WHERE e.grupo = 'Letal' AND s.codigo = 'F')     AS vitimas_letais_mulheres
    FROM fato_vitimas_sinesp f
    JOIN dim_tempo t     ON t.id_tempo = f.id_tempo
    JOIN dim_municipio m ON m.id_municipio = f.id_municipio
    JOIN dim_evento e    ON e.id_evento = f.id_evento
    JOIN dim_sexo s      ON s.id_sexo = f.id_sexo
    GROUP BY t.ano, m.cod_uf
), sim AS (
    SELECT t.ano, m.cod_uf,
           SUM(f.qt_obitos)                         AS obitos_agressao_mulheres,
           SUM(f.qt_obitos) FILTER (WHERE r.negra)  AS obitos_mulheres_negras
    FROM fato_obitos_agressao_sim f
    JOIN dim_tempo t     ON t.id_tempo = f.id_tempo
    JOIN dim_municipio m ON m.id_municipio = f.id_municipio
    JOIN dim_raca_cor r  ON r.id_raca_cor = f.id_raca_cor
    GROUP BY t.ano, m.cod_uf
)
SELECT COALESCE(a.ano, b.ano) AS ano, u.sigla AS uf, u.regiao,
       COALESCE(a.feminicidios, 0)              AS feminicidios_sinesp,          -- todas as vítimas registradas
       COALESCE(a.feminicidios_f, 0)            AS feminicidios_mulheres_sinesp, -- só sexo feminino (comparável ao SIM)
       COALESCE(a.vitimas_letais_mulheres, 0)   AS vitimas_letais_mulheres_sinesp,
       COALESCE(b.obitos_agressao_mulheres, 0)  AS obitos_agressao_mulheres_sim,
       COALESCE(b.obitos_mulheres_negras, 0)    AS obitos_mulheres_negras_sim,
       ROUND(100.0 * b.obitos_mulheres_negras / NULLIF(b.obitos_agressao_mulheres, 0), 1)
                                                AS pct_mulheres_negras_sim
FROM sinesp a
FULL JOIN sim b ON a.ano = b.ano AND a.cod_uf = b.cod_uf
JOIN dim_uf u ON u.cod_uf = COALESCE(a.cod_uf, b.cod_uf);
