"""Gera dashboard/painel_feminicidio_interseccional.html a partir de data/processed/*.csv.

Uso: python dashboard/gerar_painel.py
O HTML final é autocontido (dados agregados embutidos, sem dependências externas).
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
P = RAIZ / "data" / "processed"
TPL = Path(__file__).with_name("template.html")
OUT = Path(__file__).with_name("painel_feminicidio_interseccional.html")


def main():
    t = pd.read_csv(P / "dim_tempo.csv")
    m = pd.read_csv(P / "dim_municipio.csv")
    u = pd.read_csv(P / "dim_uf.csv")
    e = pd.read_csv(P / "dim_evento.csv")
    s = pd.read_csv(P / "dim_sexo.csv")
    r = pd.read_csv(P / "dim_raca_cor.csv")
    fa = pd.read_csv(P / "dim_faixa_etaria.csv")
    me = pd.read_csv(P / "dim_meio_agressao.csv")
    fs = pd.read_csv(P / "fato_vitimas_sinesp.csv")
    fo = pd.read_csv(P / "fato_obitos_agressao_sim.csv")

    mu = m.merge(u, on="cod_uf")[["id_municipio", "sigla"]]
    tempo = t[["id_tempo", "ano", "mes"]]

    sinesp = (fs.merge(tempo, on="id_tempo").merge(mu, on="id_municipio")
                .groupby(["ano", "mes", "sigla", "id_evento", "id_sexo"], as_index=False)["qt_vitimas"].sum())
    sim = (fo.merge(tempo, on="id_tempo").merge(mu, on="id_municipio")
             .groupby(["ano", "mes", "sigla", "id_raca_cor", "id_faixa", "id_meio"], as_index=False)["qt_obitos"].sum())
    assert sinesp.qt_vitimas.sum() == fs.qt_vitimas.sum()
    assert sim.qt_obitos.sum() == fo.qt_obitos.sum()

    # feminicídios com vítima mulher por município e ano (tabela de detalhe)
    top = (fs[(fs.id_evento == 1) & (fs.id_sexo == 1)]
           .merge(t[["id_tempo", "ano"]], on="id_tempo")
           .merge(m[["id_municipio", "nome", "cod_uf"]], on="id_municipio")
           .merge(u[["cod_uf", "sigla"]], on="cod_uf"))
    top = top[top.nome != "NÃO INFORMADO"].groupby(["ano", "sigla", "nome"], as_index=False)["qt_vitimas"].sum()
    top = top[top.qt_vitimas > 0]

    def recs(df):
        return json.loads(df.to_json(orient="records", force_ascii=False))

    dados = {
        "uf": recs(u), "evento": recs(e), "sexo": recs(s), "raca": recs(r), "faixa": recs(fa), "meio": recs(me),
        "sinesp": sinesp.values.tolist(), "sim": sim.values.tolist(), "top_mun": top.values.tolist(),
    }
    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":"), default=int)
    html = TPL.read_text(encoding="utf-8")
    html = html.replace("__DATA_JSON__", js).replace("__DATA__", date.today().strftime("%d/%m/%Y"))
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size/1e6:.2f} MB | sinesp {len(sinesp)} linhas, sim {len(sim)} linhas, "
          f"vítimas {sinesp.qt_vitimas.sum():,} | óbitos {sim.qt_obitos.sum():,}")


if __name__ == "__main__":
    main()
