"""
Gera os dados agregados que o painel da Fase 3 consome, embutidos como JS.
Grao: SIM agregado por (ano, uf, raca, faixa, meio); SINESP por (ano, uf).
Tudo sai dos CSVs tratados da Fase 2 por agregacao - nada inventado.
Saida: dados.js  (window.DADOS = {...})
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "analise"))
import carregar  # noqa: E402

AQUI = Path(__file__).resolve().parent

d = carregar.dimensoes()
vit = carregar.fato_sinesp(d)
obi = carregar.fato_sim(d)
fem = vit[vit.evento == "Feminicídio"]
vlm = vit[(vit.sexo_cod == "F") & (vit.grupo == "Letal")]
obf = obi[obi.sexo_cod == "F"]

# ---- dimensoes de apoio ----
ufs = (d["uf"][["sigla", "uf_nome", "regiao"]]
       .sort_values("sigla").values.tolist())
ordem_faixa = d["faixa"].sort_values("idade_min").faixa.tolist()
ordem_meio = (obf.groupby("meio").qt_obitos.sum()
              .sort_values(ascending=False).index.tolist())
racas = d["raca"].sort_values("id_raca_cor")[["raca", "negra"]].values.tolist()

# ---- SIM agregado por (ano, uf, raca, faixa, meio) ----
sim = (obf.groupby(["ano", "sigla", "raca", "negra", "faixa", "meio"],
                   observed=True).qt_obitos.sum().reset_index())
sim_rows = [[int(r.ano), r.sigla, r.raca, bool(r.negra), r.faixa, r.meio,
             int(r.qt_obitos)] for r in sim.itertuples()]

# ---- SINESP agregado por (ano, uf) ----
sinesp = []
g_fem = fem.groupby(["ano", "sigla"]).qt_vitimas.sum()
g_vlm = vlm.groupby(["ano", "sigla"]).qt_vitimas.sum()
for (ano, sig) in sorted(set(g_fem.index) | set(g_vlm.index)):
    sinesp.append([int(ano), sig,
                   int(g_fem.get((ano, sig), 0)),
                   int(g_vlm.get((ano, sig), 0))])

# ---- top municipios (feminicidio, acumulado) ----
mun = (fem.groupby(["mun_nome", "sigla"]).qt_vitimas.sum()
       .sort_values(ascending=False).head(15).reset_index())
municipios = [[r.mun_nome, r.sigla, int(r.qt_vitimas)] for r in mun.itertuples()]

dados = {
    "anos": sorted(obf.ano.unique().tolist()),
    "ufs": ufs,                       # [sigla, nome, regiao]
    "regioes": sorted(d["uf"].regiao.unique().tolist()),
    "faixas": ordem_faixa,
    "meios": ordem_meio,
    "racas": racas,                   # [raca, negra]
    "sim_cols": ["ano", "uf", "raca", "negra", "faixa", "meio", "q"],
    "sim": sim_rows,
    "sinesp_cols": ["ano", "uf", "feminicidios", "vitimas_letais"],
    "sinesp": sinesp,
    "municipios": municipios,
    "fonte": "SINESP-VDE e SIM, de 2019 a 2024. Agregação própria da Fase 3.",
}

js = "window.DADOS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n"
(AQUI / "dados.js").write_text(js, encoding="utf-8")
print("dados.js:", len(js), "bytes |", len(sim_rows), "linhas SIM(UF) |",
      len(sinesp), "linhas SINESP(UF)")
