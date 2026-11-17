"""
Fase 3 - Analise analitica reprodutivel.
Responde as perguntas de pesquisa a partir do schema estrela da Fase 2.
Salva tabelas de resultado em saidas/ e um findings.json com os numeros-chave.

Nenhum numero e inventado: tudo sai dos CSVs tratados por agregacao.
Testes estatisticos usam scipy. Taxas por 100 mil entram quando a populacao
do IBGE for integrada (modulo taxas.py).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

import carregar

SAIDAS = Path(__file__).resolve().parent.parent / "saidas"
SAIDAS.mkdir(exist_ok=True)

d = carregar.dimensoes()
vit = carregar.fato_sinesp(d)      # SINESP - vitimas registradas
obi = carregar.fato_sim(d)         # SIM - obitos de mulheres por agressao

# recortes reutilizados
fem = vit[vit.evento == "Feminicídio"]                      # feminicidio (evento)
vlm = vit[(vit.sexo_cod == "F") & (vit.grupo == "Letal")]   # vitimas letais mulheres (SINESP)
obf = obi[obi.sexo_cod == "F"]                              # obitos mulheres por agressao (SIM)

achados = {}


def salvar(df, nome, index=True):
    df.to_csv(SAIDAS / f"{nome}.csv", index=index)
    return df


# =====================================================================
# 1. SERIE ANUAL - as tres leituras do fenomeno
# =====================================================================
serie = pd.DataFrame({
    "feminicidios_sinesp": fem.groupby("ano").qt_vitimas.sum(),
    "vitimas_letais_mulheres_sinesp": vlm.groupby("ano").qt_vitimas.sum(),
    "obitos_agressao_mulheres_sim": obf.groupby("ano").qt_obitos.sum(),
}).astype(int)
serie["razao_sim_sobre_feminicidio"] = (
    serie.obitos_agressao_mulheres_sim / serie.feminicidios_sinesp).round(2)
salvar(serie, "01_serie_anual")

# tendencia (regressao linear no ano) para cada serie
anos = serie.index.values.astype(float)
tendencias = {}
for col in ["feminicidios_sinesp", "vitimas_letais_mulheres_sinesp",
            "obitos_agressao_mulheres_sim"]:
    lr = stats.linregress(anos, serie[col].values.astype(float))
    tendencias[col] = {
        "inclinacao_por_ano": round(lr.slope, 1),
        "variacao_pct_2019_2024": round(
            100 * (serie[col].iloc[-1] - serie[col].iloc[0]) / serie[col].iloc[0], 1),
        "r2": round(lr.rvalue ** 2, 3),
        "p_valor": round(lr.pvalue, 4),
    }
achados["tendencia_anual"] = tendencias
achados["serie_anual"] = serie.reset_index().to_dict(orient="records")

# =====================================================================
# 2. INTERSECCIONALIDADE - participacao de mulheres negras (SIM)
# =====================================================================
pct_negras_ano = obf.groupby("ano").apply(
    lambda x: 100 * x[x.negra].qt_obitos.sum() / x.qt_obitos.sum(),
    include_groups=False).round(1)
achados["pct_negras_ano"] = pct_negras_ano.to_dict()

# por UF (acumulado 2019-2024) - so UFs com volume minimo
por_uf = obf.groupby("sigla").agg(
    obitos=("qt_obitos", "sum"),
    obitos_negras=("qt_obitos", lambda s: obf.loc[s.index][obf.loc[s.index].negra].qt_obitos.sum()),
)
por_uf["pct_negras"] = (100 * por_uf.obitos_negras / por_uf.obitos).round(1)
por_uf = por_uf.merge(d["uf"][["sigla", "regiao"]], on="sigla").set_index("sigla")
por_uf = por_uf.sort_values("pct_negras", ascending=False)
salvar(por_uf, "02_pct_negras_por_uf")
achados["pct_negras_uf_top"] = por_uf.head(5).pct_negras.to_dict()
achados["pct_negras_uf_bottom"] = por_uf.tail(5).pct_negras.to_dict()

# tabela interseccional raca x faixa (SIM, mulheres, total do periodo)
inter = pd.pivot_table(obf, values="qt_obitos", index="faixa", columns="raca",
                       aggfunc="sum", fill_value=0,
                       observed=True).astype(int)
ordem_faixa = (d["faixa"].sort_values("idade_min").faixa.tolist())
inter = inter.reindex([f for f in ordem_faixa if f in inter.index])
salvar(inter, "03_interseccional_raca_faixa")

# =====================================================================
# 3. MEIO DE AGRESSAO (SIM, mulheres)
# =====================================================================
meio_tot = obf.groupby("meio").qt_obitos.sum().sort_values(ascending=False)
meio_pct = (100 * meio_tot / meio_tot.sum()).round(1)
meio_df = pd.DataFrame({"obitos": meio_tot.astype(int), "pct": meio_pct})
salvar(meio_df, "04_meio_agressao")
achados["meio_agressao_pct"] = meio_pct.to_dict()

# meio x negra (mulheres negras vs nao-negras)
meio_raca = obf.assign(grupo_raca=np.where(obf.negra, "negras", "nao_negras")) \
    .groupby(["meio", "grupo_raca"]).qt_obitos.sum().unstack(fill_value=0).astype(int)
salvar(meio_raca, "05_meio_x_raca")

# =====================================================================
# 4. FAIXA ETARIA (SIM, mulheres)
# =====================================================================
faixa_tot = obf.groupby("faixa").qt_obitos.sum()
faixa_tot = faixa_tot.reindex([f for f in ordem_faixa if f in faixa_tot.index])
faixa_df = pd.DataFrame({
    "obitos": faixa_tot.astype(int),
    "pct": (100 * faixa_tot / faixa_tot.sum()).round(1)})
salvar(faixa_df, "06_faixa_etaria")
achados["faixa_etaria_pct"] = faixa_df.pct.to_dict()
# faixa modal
achados["faixa_modal"] = faixa_df.obitos.idxmax()

# =====================================================================
# 5. SAZONALIDADE - mes do ano agregado (2019-2024)
# =====================================================================
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
sazo = pd.DataFrame({
    "feminicidios_sinesp": fem.groupby("mes").qt_vitimas.sum(),
    "obitos_agressao_sim": obf.groupby("mes").qt_obitos.sum(),
})
sazo.index = [MESES[m - 1] for m in sazo.index]
salvar(sazo, "07_sazonalidade")
# indice de sazonalidade (mes / media mensal) para feminicidios
media_mes = fem.groupby("mes").qt_vitimas.sum().mean()
achados["mes_pico_feminicidio"] = MESES[int(fem.groupby("mes").qt_vitimas.sum().idxmax()) - 1]
achados["mes_vale_feminicidio"] = MESES[int(fem.groupby("mes").qt_vitimas.sum().idxmin()) - 1]

# =====================================================================
# 6. RANKING POR UF (2024 e acumulado)
# =====================================================================
rank_uf = pd.DataFrame({
    "feminicidios_2024": fem[fem.ano == 2024].groupby("sigla").qt_vitimas.sum(),
    "feminicidios_total": fem.groupby("sigla").qt_vitimas.sum(),
    "obitos_sim_2024": obf[obf.ano == 2024].groupby("sigla").qt_obitos.sum(),
    "obitos_sim_total": obf.groupby("sigla").qt_obitos.sum(),
}).fillna(0).astype(int)
rank_uf = rank_uf.merge(por_uf[["pct_negras", "regiao"]], left_index=True, right_index=True)
rank_uf = rank_uf.sort_values("feminicidios_total", ascending=False)
salvar(rank_uf, "08_ranking_uf")
achados["top5_uf_feminicidio_total"] = rank_uf.head(5).feminicidios_total.to_dict()

# =====================================================================
# 7. DIVERGENCIA SINESP x SIM (subnotificacao do feminicidio)
# =====================================================================
# Por UF-ano: obitos de mulheres por agressao (SIM) vs feminicidios (SINESP).
# Nem todo homicidio de mulher e feminicidio, mas a razao mostra quanto o
# registro de "feminicidio" captura do universo de mortes violentas de mulheres.
cmp = pd.DataFrame({
    "feminicidios_sinesp": fem.groupby(["ano", "sigla"]).qt_vitimas.sum(),
    "obitos_agressao_sim": obf.groupby(["ano", "sigla"]).qt_obitos.sum(),
}).dropna()
cmp["pct_feminicidio_sobre_obitos"] = (
    100 * cmp.feminicidios_sinesp / cmp.obitos_agressao_sim).round(1)
salvar(cmp.reset_index(), "09_divergencia_sinesp_sim", index=False)

# correlacao espacial (UF, 2024): feminicidios SINESP vs obitos SIM
c24 = cmp.loc[2024]
r, p = stats.pearsonr(c24.feminicidios_sinesp, c24.obitos_agressao_sim)
achados["correlacao_uf_2024_sinesp_sim"] = {
    "pearson_r": round(r, 3), "p_valor": round(p, 6), "n_uf": int(len(c24))}

# razao nacional por ano ja esta na serie
achados["pct_feminicidio_sobre_obitos_nacional"] = (
    100 * serie.feminicidios_sinesp / serie.obitos_agressao_mulheres_sim).round(1).to_dict()

# =====================================================================
# 8. RANKING MUNICIPIOS (acumulado) - feminicidios
# =====================================================================
rank_mun = (fem.groupby(["mun_nome", "sigla"]).qt_vitimas.sum()
            .sort_values(ascending=False).head(20).reset_index())
salvar(rank_mun, "10_ranking_municipios", index=False)

# =====================================================================
# 9. TESTE: distribuicao racial dos obitos difere por regiao? (qui-quadrado)
# =====================================================================
tab = pd.crosstab(obf.regiao, obf.negra,
                  values=obf.qt_obitos, aggfunc="sum").fillna(0)
chi2, pchi, dof, _ = stats.chi2_contingency(tab.values)
achados["qui2_raca_por_regiao"] = {
    "chi2": round(chi2, 1), "p_valor": float(f"{pchi:.2e}"), "dof": int(dof)}

# =====================================================================
# salvar findings
# =====================================================================
def _py(o):
    if isinstance(o, dict):
        return {str(k): _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o

with open(SAIDAS / "findings.json", "w", encoding="utf-8") as f:
    json.dump(_py(achados), f, ensure_ascii=False, indent=2, default=str)

# ---- impressao resumida ----
print("=" * 64)
print("SERIE ANUAL")
print(serie.to_string())
print("\nTENDENCIA (regressao linear no ano):")
for k, v in tendencias.items():
    print(f"  {k}: +{v['inclinacao_por_ano']}/ano | {v['variacao_pct_2019_2024']:+}% "
          f"2019-24 | R2={v['r2']} | p={v['p_valor']}")
print("\n% MULHERES NEGRAS (SIM) por ano:", pct_negras_ano.to_dict())
print("\nTOP 5 UF % negras:", por_uf.head(5).pct_negras.to_dict())
print("BOTTOM 5 UF % negras:", por_uf.tail(5).pct_negras.to_dict())
print("\nMEIO DE AGRESSAO (%):", meio_pct.to_dict())
print("\nFAIXA ETARIA (%):", faixa_df.pct.to_dict(), "| modal:", achados["faixa_modal"])
print("\nSAZONALIDADE feminicidio - pico:", achados["mes_pico_feminicidio"],
      "| vale:", achados["mes_vale_feminicidio"])
print("\n% FEMINICIDIO sobre obitos SIM (nacional/ano):",
      achados["pct_feminicidio_sobre_obitos_nacional"])
print("\nCORRELACAO UF 2024 (SINESP x SIM): r=",
      achados["correlacao_uf_2024_sinesp_sim"])
print("\nQUI2 raca x regiao:", achados["qui2_raca_por_regiao"])
print("\nTOP 20 municipios (feminicidio):")
print(rank_mun.to_string(index=False))
print("\n=> saidas em:", SAIDAS)
