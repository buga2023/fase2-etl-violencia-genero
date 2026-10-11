"""CARGA — cria o esquema e carrega dimensões e fatos no PostgreSQL via COPY.

Tudo roda numa única transação: se qualquer passo falhar, o banco volta ao
estado anterior (nunca fica meio carregado).
"""
import pandas as pd
import psycopg

from . import config as cfg

ORDEM = ["dim_uf", "dim_tempo", "dim_municipio", "dim_sexo", "dim_raca_cor", "dim_faixa_etaria",
         "dim_evento", "dim_meio_agressao", "fato_vitimas_sinesp", "fato_obitos_agressao_sim"]


def _copy(cur, tabela: str, df: pd.DataFrame) -> None:
    cols = ", ".join(df.columns)
    with cur.copy(f"COPY vde.{tabela} ({cols}) FROM STDIN") as cp:
        for linha in df.itertuples(index=False, name=None):
            cp.write_row([None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in linha])


def carregar(url: str, tabelas: dict[str, pd.DataFrame], cargas: list[dict]) -> dict:
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute((cfg.DIR_SQL / "01_schema.sql").read_text(encoding="utf-8"))
        for nome in ORDEM:
            _copy(cur, nome, tabelas[nome])
        # SERIAL não avança com valores explícitos: realinha a sequência
        cur.execute("SELECT setval('vde.dim_municipio_id_municipio_seq', (SELECT MAX(id_municipio) FROM vde.dim_municipio))")
        _copy(cur, "meta_carga", pd.DataFrame(cargas)[
            ["fonte", "arquivo", "sha256", "tamanho_bytes", "linhas_lidas", "linhas_apos_filtro"]])
        cur.execute((cfg.DIR_SQL / "02_views.sql").read_text(encoding="utf-8"))
        cur.execute("ANALYZE")  # atualiza estatísticas do planejador

        contagem = {}
        for nome in ORDEM + ["meta_carga"]:
            cur.execute(f"SELECT COUNT(*) FROM vde.{nome}")
            contagem[nome] = cur.fetchone()[0]
        cur.execute("""SELECT relname, pg_total_relation_size(c.oid)
                       FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                       WHERE n.nspname = 'vde' AND c.relkind = 'r'""")
        tamanhos = dict(cur.fetchall())
        cur.execute("""SELECT table_name, column_name, data_type, is_nullable
                       FROM information_schema.columns WHERE table_schema = 'vde'
                       AND table_name NOT LIKE 'vw\\_%' ORDER BY table_name, ordinal_position""")
        colunas = cur.fetchall()
    return {"contagem": contagem, "tamanhos": tamanhos, "colunas": colunas}
