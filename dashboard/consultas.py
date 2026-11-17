"""Consultas SQL do painel. Tudo roda direto no PostgreSQL do Aiven (schema vde).

Cada função recebe os filtros escolhidos na tela e monta o WHERE com parâmetros
(%(nome)s), nunca concatenando texto do usuário no SQL.
"""
from dataclasses import dataclass, field

import pandas as pd
import psycopg


@dataclass
class Filtros:
    ano_ini: int = 2019
    ano_fim: int = 2024
    regioes: list[str] = field(default_factory=list)
    ufs: list[str] = field(default_factory=list)
    racas: list[str] = field(default_factory=list)     # só SIM
    faixas: list[str] = field(default_factory=list)    # só SIM
    meios: list[str] = field(default_factory=list)     # só SIM
    sexos: list[str] = field(default_factory=list)     # só SINESP

    def params(self) -> dict:
        return {"ano_ini": self.ano_ini, "ano_fim": self.ano_fim, "regioes": self.regioes,
                "ufs": self.ufs, "racas": self.racas, "faixas": self.faixas,
                "meios": self.meios, "sexos": self.sexos}

    @property
    def recorte_populacional(self) -> bool:
        """Raça, idade e meio filtram só o numerador; a taxa por 100 mil deixa de ser comparável."""
        return bool(self.racas or self.faixas or self.meios)


# WHERE comum: listas vazias = sem filtro
_GEO = """t.ano BETWEEN %(ano_ini)s AND %(ano_fim)s
  AND (cardinality(%(regioes)s::text[]) = 0 OR u.regiao = ANY(%(regioes)s))
  AND (cardinality(%(ufs)s::text[]) = 0 OR u.sigla = ANY(%(ufs)s))"""

_SIM_EXTRA = """
  AND (cardinality(%(racas)s::text[]) = 0 OR r.descricao = ANY(%(racas)s))
  AND (cardinality(%(faixas)s::text[]) = 0 OR fe.descricao = ANY(%(faixas)s))
  AND (cardinality(%(meios)s::text[]) = 0 OR me.descricao = ANY(%(meios)s))"""

_SIM_FROM = """FROM vde.fato_obitos_agressao_sim f
JOIN vde.dim_tempo t ON t.id_tempo = f.id_tempo
JOIN vde.dim_municipio m ON m.id_municipio = f.id_municipio
JOIN vde.dim_uf u ON u.cod_uf = m.cod_uf
JOIN vde.dim_raca_cor r ON r.id_raca_cor = f.id_raca_cor
JOIN vde.dim_faixa_etaria fe ON fe.id_faixa = f.id_faixa
JOIN vde.dim_meio_agressao me ON me.id_meio = f.id_meio"""

_SINESP_FROM = """FROM vde.fato_vitimas_sinesp f
JOIN vde.dim_tempo t ON t.id_tempo = f.id_tempo
JOIN vde.dim_municipio m ON m.id_municipio = f.id_municipio
JOIN vde.dim_uf u ON u.cod_uf = m.cod_uf
JOIN vde.dim_evento e ON e.id_evento = f.id_evento
JOIN vde.dim_sexo s ON s.id_sexo = f.id_sexo"""

_SINESP_EXTRA = """
  AND (cardinality(%(sexos)s::text[]) = 0 OR s.descricao = ANY(%(sexos)s))"""

_POP = """SELECT p.ano, SUM(p.populacao) AS populacao
FROM vde.populacao_feminina_uf p JOIN vde.dim_uf u ON u.cod_uf = p.cod_uf
WHERE p.ano BETWEEN %(ano_ini)s AND %(ano_fim)s
  AND (cardinality(%(regioes)s::text[]) = 0 OR u.regiao = ANY(%(regioes)s))
  AND (cardinality(%(ufs)s::text[]) = 0 OR u.sigla = ANY(%(ufs)s))"""

SQL_SERIE_ANUAL = f"""
WITH sim AS (
  SELECT t.ano, SUM(f.qt_obitos) AS obitos,
         SUM(f.qt_obitos) FILTER (WHERE r.negra) AS obitos_negras,
         SUM(f.qt_obitos) FILTER (WHERE me.descricao = 'Arma de fogo') AS obitos_arma
  {_SIM_FROM}
  WHERE {_GEO}{_SIM_EXTRA}
  GROUP BY t.ano
), sinesp AS (
  SELECT t.ano, SUM(f.qt_vitimas) FILTER (WHERE e.nome = 'Feminicídio') AS feminicidios,
         SUM(f.qt_vitimas) FILTER (WHERE e.nome = 'Tentativa de feminicídio') AS tentativas
  {_SINESP_FROM}
  WHERE {_GEO}{_SINESP_EXTRA}
  GROUP BY t.ano
), pop AS ({_POP} GROUP BY p.ano)
SELECT pop.ano, pop.populacao,
       COALESCE(sim.obitos, 0) AS obitos, COALESCE(sim.obitos_negras, 0) AS obitos_negras,
       COALESCE(sim.obitos_arma, 0) AS obitos_arma,
       COALESCE(sinesp.feminicidios, 0) AS feminicidios, COALESCE(sinesp.tentativas, 0) AS tentativas
FROM pop LEFT JOIN sim USING (ano) LEFT JOIN sinesp USING (ano)
ORDER BY pop.ano"""

# Ranking geográfico. nivel: regiao | uf | municipio (drill-down)
SQL_GEO = {
    "regiao": ("u.regiao", "u.regiao"),
    "uf": ("u.sigla", "u.sigla"),
    "municipio": ("m.nome || ' (' || u.sigla || ')'", "m.nome, u.sigla"),
}


def sql_ranking(nivel: str) -> str:
    rotulo, grupo = SQL_GEO[nivel]
    pop_join = ""
    pop_cols = "NULL::bigint AS populacao"
    if nivel in ("regiao", "uf"):
        chave = "u.regiao" if nivel == "regiao" else "u.sigla"
        pop_join = f"""LEFT JOIN (
            SELECT {chave} AS local, SUM(p.populacao) AS populacao
            FROM vde.populacao_feminina_uf p JOIN vde.dim_uf u ON u.cod_uf = p.cod_uf
            WHERE p.ano BETWEEN %(ano_ini)s AND %(ano_fim)s GROUP BY {chave}
        ) pop ON pop.local = base.local"""
        pop_cols = "pop.populacao"
    return f"""
WITH sim AS (
  SELECT {rotulo} AS local, SUM(f.qt_obitos) AS obitos,
         SUM(f.qt_obitos) FILTER (WHERE r.negra) AS obitos_negras
  {_SIM_FROM}
  WHERE {_GEO}{_SIM_EXTRA}
  GROUP BY {grupo}
), sinesp AS (
  SELECT {rotulo} AS local, SUM(f.qt_vitimas) FILTER (WHERE e.nome = 'Feminicídio') AS feminicidios
  {_SINESP_FROM}
  WHERE {_GEO}{_SINESP_EXTRA}
    AND m.nome <> 'NÃO INFORMADO'
  GROUP BY {grupo}
), base AS (
  SELECT COALESCE(sim.local, sinesp.local) AS local,
         COALESCE(sim.obitos, 0) AS obitos, COALESCE(sim.obitos_negras, 0) AS obitos_negras,
         COALESCE(sinesp.feminicidios, 0) AS feminicidios
  FROM sim FULL JOIN sinesp ON sim.local = sinesp.local
)
SELECT base.*, {pop_cols}
FROM base {pop_join}
WHERE base.local IS NOT NULL"""


SQL_RACA_FAIXA = f"""
SELECT fe.id_faixa, fe.descricao AS faixa,
       CASE WHEN r.negra THEN 'Negras (pretas e pardas)'
            WHEN r.descricao = 'Ignorada' THEN 'Ignorada'
            ELSE 'Não negras' END AS grupo_racial,
       SUM(f.qt_obitos) AS obitos
{_SIM_FROM}
WHERE {_GEO}{_SIM_EXTRA}
GROUP BY 1, 2, 3 ORDER BY 1"""

SQL_MEIO_RACA = f"""
SELECT me.descricao AS meio,
       CASE WHEN r.negra THEN 'Negras (pretas e pardas)' ELSE 'Não negras' END AS grupo_racial,
       SUM(f.qt_obitos) AS obitos
{_SIM_FROM}
WHERE {_GEO}{_SIM_EXTRA} AND r.descricao <> 'Ignorada'
GROUP BY 1, 2"""

SQL_MES = f"""
SELECT t.mes, SUM(f.qt_obitos) AS obitos
{_SIM_FROM}
WHERE {_GEO}{_SIM_EXTRA}
GROUP BY t.mes ORDER BY t.mes"""

SQL_OPCOES = {
    "regioes": "SELECT DISTINCT regiao FROM vde.dim_uf ORDER BY 1",
    "ufs": "SELECT sigla, regiao FROM vde.dim_uf ORDER BY sigla",
    "racas": "SELECT descricao FROM vde.dim_raca_cor ORDER BY id_raca_cor",
    "faixas": "SELECT descricao FROM vde.dim_faixa_etaria ORDER BY id_faixa",
    "meios": "SELECT descricao FROM vde.dim_meio_agressao ORDER BY id_meio",
    "sexos": "SELECT descricao FROM vde.dim_sexo ORDER BY id_sexo",
    "anos": "SELECT MIN(ano), MAX(ano) FROM vde.dim_tempo",
}


def consultar(url: str, sql: str, params: dict | None = None) -> pd.DataFrame:
    with psycopg.connect(url, connect_timeout=15) as con, con.cursor() as cur:
        cur.execute(sql, params or {})
        cols = [d.name for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    # Decimal -> float para os gráficos
    for c in df.columns:
        if df[c].dtype == object and len(df) and hasattr(df[c].iloc[0], "as_integer_ratio"):
            df[c] = df[c].astype(float)
    return df
