"""
Fase 3 - Geracao das figuras do relatorio (matplotlib), no padrao editorial
da Fase 2. Paleta de fontes validada pela skill dataviz:
  SINESP (registro policial) = azul  #1C6EA4
  SIM    (obitos/DataSUS)    = terracota #C0442F
Series unicas usam rampa sequencial de um tom; nada de arco-iris.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter

import carregar

BASE = Path(__file__).resolve().parent.parent
FIG = BASE / "figuras"
FIG.mkdir(exist_ok=True)
# As fontes Fraunces/Inter/JetBrains ficam em relatorio/fonts no repositorio.
# Se nao forem encontradas, o matplotlib cai no padrao sem quebrar.
FONTS = Path(__file__).resolve().parent.parent / "docs" / "relatorio" / "fonts"

# ---- identidade visual ----
INK = "#1C1C1C"; MUTE = "#5a4a3a"; PAPER = "#FCFAF5"; LINE = "#D9D2C4"
VINHO = "#5C1F2A"; OURO = "#9D7B3F"; VERDE = "#2C4A2D"
SINESP = "#1C6EA4"; SIM = "#C0442F"

# rampas sequenciais (um tom, claro -> escuro)
from matplotlib.colors import LinearSegmentedColormap
RAMP_VINHO = LinearSegmentedColormap.from_list("vinho", ["#EBD9DC", "#5C1F2A", "#2E0F15"])
RAMP_AZUL = LinearSegmentedColormap.from_list("azul", ["#D6E6F0", "#1C6EA4", "#0C3A5A"])

# ---- fontes ----
SERIF = SANS = MONO = None
try:
    for f in ["Fraunces.ttf", "InterTight.ttf", "JetBrainsMono.ttf"]:
        if (FONTS / f).exists():
            fm.fontManager.addfont(str(FONTS / f))
    SERIF = fm.FontProperties(fname=str(FONTS / "Fraunces.ttf")).get_name()
    SANS = fm.FontProperties(fname=str(FONTS / "InterTight.ttf")).get_name()
    MONO = fm.FontProperties(fname=str(FONTS / "JetBrainsMono.ttf")).get_name()
except Exception as e:
    print("fontes:", e)

plt.rcParams.update({
    "font.family": SANS or "DejaVu Sans",
    "figure.facecolor": PAPER, "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER, "text.color": INK,
    "axes.edgecolor": LINE, "axes.labelcolor": INK,
    "xtick.color": MUTE, "ytick.color": MUTE,
    "axes.grid": False, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200,
})


def titulo(ax, t, sub=None):
    # offsets em pontos -> espacamento constante em qualquer altura de figura
    ax.annotate(t, xy=(0, 1), xycoords="axes fraction", xytext=(0, 26),
                textcoords="offset points", fontsize=13, fontweight="bold",
                color=VINHO, fontfamily=SERIF or SANS, va="bottom", ha="left")
    if sub:
        ax.annotate(sub, xy=(0, 1), xycoords="axes fraction", xytext=(0, 8),
                    textcoords="offset points", fontsize=8.5, color=MUTE,
                    fontstyle="italic", fontfamily=SERIF or SANS,
                    va="bottom", ha="left")


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(FIG / f"{nome}.png", bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print("  ok", nome)


d = carregar.dimensoes()
vit = carregar.fato_sinesp(d)
obi = carregar.fato_sim(d)
fem = vit[vit.evento == "Feminicídio"]
vlm = vit[(vit.sexo_cod == "F") & (vit.grupo == "Letal")]
obf = obi[obi.sexo_cod == "F"]
ordem_faixa = d["faixa"].sort_values("idade_min").faixa.tolist()

# =====================================================================
# FIG 1 - serie anual (feminicidio SINESP x obitos SIM x vitimas letais)
# =====================================================================
s_fem = fem.groupby("ano").qt_vitimas.sum()
s_vlm = vlm.groupby("ano").qt_vitimas.sum()
s_sim = obf.groupby("ano").qt_obitos.sum()
anos = s_fem.index.tolist()

fig, ax = plt.subplots(figsize=(7.4, 4.0))
ax.plot(anos, s_vlm, color=SINESP, lw=1.4, ls=(0, (4, 2)), marker="o", ms=4,
        label="Vítimas letais de mulheres na SINESP")
ax.plot(anos, s_sim, color=SIM, lw=2.2, marker="o", ms=5,
        label="Óbitos de mulheres por agressão no SIM")
ax.plot(anos, s_fem, color=INK, lw=2.2, marker="o", ms=5,
        label="Feminicídios na SINESP")
for serie_, cor in [(s_vlm, SINESP), (s_sim, SIM), (s_fem, INK)]:
    ax.annotate(f"{int(serie_.iloc[-1]):,}".replace(",", "."),
                (anos[-1], serie_.iloc[-1]), xytext=(8, 0),
                textcoords="offset points", va="center", fontsize=8.5,
                color=cor, fontweight="bold")
ax.set_ylim(0, 4600)
ax.set_xticks(anos)
ax.legend(frameon=False, fontsize=8.3, loc="center left",
          bbox_to_anchor=(0.03, 0.46))
titulo(ax, "Três leituras da mesma tragédia",
       "Contagens de cada ano no Brasil, de 2019 a 2024. O registro de feminicídio sobe, mas o total de mortes não acompanha.")
salvar(fig, "fig1_serie_anual")

# =====================================================================
# FIG 2 - captacao: % feminicidio sobre obitos SIM
# =====================================================================
capt = (100 * s_fem / s_sim)
fig, ax = plt.subplots(figsize=(7.4, 3.4))
ax.plot(anos, capt, color=VINHO, lw=2.4, marker="o", ms=6)
ax.fill_between(anos, capt, 0, color=VINHO, alpha=0.06)
for x, y in zip(anos, capt):
    ax.annotate(f"{y:.1f}%", (x, y), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=8.5, color=VINHO, fontweight="bold")
ax.set_ylim(30, 45)
ax.set_xticks(anos)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
titulo(ax, "A Justiça está captando mais feminicídios",
       "Feminicídios da SINESP como fatia dos óbitos de mulheres por agressão do SIM. Subiu de 35,7% para 41,4%.")
salvar(fig, "fig2_captacao")

# =====================================================================
# FIG 3 - % mulheres negras por UF (sequencial)
# =====================================================================
puf = obf.groupby("sigla").apply(
    lambda x: pd.Series({"obitos": x.qt_obitos.sum(),
                         "pct_negras": 100 * x[x.negra].qt_obitos.sum() / x.qt_obitos.sum()}),
    include_groups=False).sort_values("pct_negras")
fig, ax = plt.subplots(figsize=(7.0, 7.2))
cores = RAMP_VINHO(0.25 + 0.75 * (puf.pct_negras - puf.pct_negras.min()) /
                   (puf.pct_negras.max() - puf.pct_negras.min()))
ax.barh(puf.index, puf.pct_negras, color=cores, height=0.74)
for i, (sig, row) in enumerate(puf.iterrows()):
    ax.text(row.pct_negras + 1, i, f"{row.pct_negras:.1f}%", va="center",
            fontsize=7.6, color=INK)
ax.axvline(67.1, color=OURO, lw=1.4, ls="--")
ax.text(67.1, len(puf) - 0.3, " média do Brasil 67,1%", fontsize=7.6,
        color=OURO, fontstyle="italic", va="top")
ax.set_xlim(0, 108)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.tick_params(axis="y", length=0, labelsize=8.5)
titulo(ax, "A cor da vítima muda de estado para estado",
       "Percentual de mulheres negras, somando pretas e pardas, entre os óbitos por agressão do SIM, de 2019 a 2024.")
salvar(fig, "fig3_negras_uf")

# =====================================================================
# FIG 4 - meio de agressao
# =====================================================================
meio = obf.groupby("meio").qt_obitos.sum().sort_values()
meiop = 100 * meio / meio.sum()
fig, ax = plt.subplots(figsize=(7.4, 3.8))
cores = RAMP_VINHO(0.3 + 0.7 * (meio - meio.min()) / (meio.max() - meio.min()))
ax.barh(meio.index, meiop, color=cores, height=0.72)
for i, (nome, v) in enumerate(meiop.items()):
    ax.text(v + 0.6, i, f"{v:.1f}%", va="center", fontsize=8.2,
            color=INK, fontweight="bold")
ax.set_xlim(0, 56)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.tick_params(axis="y", length=0, labelsize=8.5)
titulo(ax, "Como elas são mortas",
       "Meio da agressão nos óbitos de mulheres do SIM, de 2019 a 2024. Metade é por arma de fogo.")
salvar(fig, "fig4_meio")

# =====================================================================
# FIG 5 - faixa etaria
# =====================================================================
fai = obf.groupby("faixa").qt_obitos.sum().reindex(ordem_faixa)
faip = 100 * fai / fai.sum()
fig, ax = plt.subplots(figsize=(7.4, 3.8))
cores = [SIM if f == fai.idxmax() else "#C9A9A2" for f in fai.index]
ax.bar(range(len(fai)), faip, color=cores, width=0.74)
for i, v in enumerate(faip):
    ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=7.8, color=INK)
ax.set_xticks(range(len(fai)))
ax.set_xticklabels(fai.index, fontsize=8)
ax.set_ylim(0, 28)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
titulo(ax, "Em que idade elas morrem",
       "Idade das mulheres mortas por agressão, segundo o SIM. A maior parte tem de 30 a 39 anos.")
salvar(fig, "fig5_faixa")

# =====================================================================
# FIG 6 - sazonalidade (2 fontes)
# =====================================================================
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
sz_fem = fem.groupby("mes").qt_vitimas.sum().reindex(range(1, 13))
sz_sim = obf.groupby("mes").qt_obitos.sum().reindex(range(1, 13))
fig, ax = plt.subplots(figsize=(7.4, 3.6))
ax.plot(MESES, sz_fem, color=INK, lw=2.0, marker="o", ms=4, label="Feminicídios na SINESP")
ax.plot(MESES, sz_sim, color=SIM, lw=2.0, marker="o", ms=4, label="Óbitos por agressão no SIM")
ax.set_ylim(0, max(sz_sim.max(), sz_fem.max()) * 1.22)
ax.legend(frameon=False, fontsize=8.3, loc="lower left", ncol=2)
titulo(ax, "Os meses mais perigosos",
       "Total somado de 2019 a 2024, por mês. O pico é em dezembro e o ponto mais baixo, em junho.")
salvar(fig, "fig6_sazonalidade")

# =====================================================================
# FIG 7 - heatmap raca x faixa (sequencial)
# =====================================================================
pv = pd.pivot_table(obf, values="qt_obitos", index="faixa", columns="raca",
                    aggfunc="sum", fill_value=0, observed=True).reindex(ordem_faixa)
# percentual por linha (faixa) para leitura de composicao
pvp = pv.div(pv.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(7.4, 4.4))
im = ax.imshow(pvp.values, cmap=RAMP_VINHO, aspect="auto", vmin=0, vmax=60)
ax.set_xticks(range(len(pvp.columns)))
ax.set_xticklabels(pvp.columns, fontsize=8, rotation=20, ha="right")
ax.set_yticks(range(len(pvp.index)))
ax.set_yticklabels(pvp.index, fontsize=8)
for i in range(pvp.shape[0]):
    for j in range(pvp.shape[1]):
        v = pvp.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                color="white" if v > 32 else INK)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
cb.ax.tick_params(labelsize=7)
cb.set_label("participação na faixa, em %", fontsize=7.5, color=MUTE)
titulo(ax, "Raça e idade, lado a lado",
       "Como se distribuem por raça e cor as mulheres de cada faixa de idade mortas por agressão, segundo o SIM.")
salvar(fig, "fig7_heatmap")

# =====================================================================
# FIG 8 - divergencia SINESP x SIM por UF (2024)
# =====================================================================
from scipy import stats
cmp = pd.DataFrame({
    "sinesp": fem[fem.ano == 2024].groupby("sigla").qt_vitimas.sum(),
    "sim": obf[obf.ano == 2024].groupby("sigla").qt_obitos.sum(),
}).dropna()
lr = stats.linregress(cmp.sinesp, cmp.sim)
fig, ax = plt.subplots(figsize=(6.6, 5.2))
ax.scatter(cmp.sinesp, cmp.sim, s=38, color=VINHO, alpha=0.8, zorder=3,
           edgecolor=PAPER, linewidth=0.8)
xs = np.array([cmp.sinesp.min(), cmp.sinesp.max()])
ax.plot(xs, lr.intercept + lr.slope * xs, color=OURO, lw=1.6, ls="--", zorder=2)
for sig, row in cmp.iterrows():
    if row.sinesp > 60 or row.sim > 250 or sig in ("DF", "RS", "SC"):
        ax.annotate(sig, (row.sinesp, row.sim), xytext=(5, 3),
                    textcoords="offset points", fontsize=7.5, color=INK)
ax.text(0.04, 0.94, f"r = {lr.rvalue:.3f}".replace(".", ","), transform=ax.transAxes,
        fontsize=10, color=VINHO, fontweight="bold",
        fontfamily=MONO or SANS, va="top")
ax.set_xlabel("Feminicídios registrados na SINESP em 2024", fontsize=8.5)
ax.set_ylabel("Óbitos de mulheres por agressão no SIM em 2024", fontsize=8.5)
titulo(ax, "As duas fontes contam a mesma história",
       "Cada ponto é um estado. A correlação é forte, de 0,82: onde há mais óbitos, há mais feminicídios registrados.")
salvar(fig, "fig8_divergencia")

print("\nFiguras geradas em:", FIG)
