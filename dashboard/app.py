"""Painel de feminicídio interseccional (Fase 4).

Lê direto do PostgreSQL no Aiven (schema vde) a cada interação. Rodar local:
    streamlit run dashboard/app.py
A conexão vem de st.secrets["DATABASE_URL"] (Streamlit Cloud ou .streamlit/secrets.toml)
ou, se não tiver, da variável DATABASE_URL do .env.
"""
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import consultas as q

st.set_page_config(page_title="Feminicídio interseccional", layout="wide")

# paleta (categórica em ordem fixa + rampa sequencial azul)
AZUL, LARANJA, VERDE_AGUA, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
COR_GRUPO = {"Negras (pretas e pardas)": LARANJA, "Não negras": AZUL, "Ignorada": CINZA}
RAMPA = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
FUSO = ZoneInfo("America/Bahia")


def url_banco() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        pass
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        st.error("Sem conexão configurada: defina DATABASE_URL no Secrets ou no .env.")
        st.stop()
    return url


URL = url_banco()


@st.cache_data(ttl=120, show_spinner=False)
def rodar(sql: str, params: dict | None = None):
    t0 = time.perf_counter()
    df = q.consultar(URL, sql, params)
    return df, (time.perf_counter() - t0) * 1000, datetime.now(FUSO)


LOG: list[tuple[str, float, datetime]] = []


def dados(nome: str, sql: str, params: dict | None = None) -> pd.DataFrame:
    df, ms, quando = rodar(sql, params)
    LOG.append((nome, ms, quando))
    return df


def layout(fig, altura=360):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white",
                      paper_bgcolor="white", font=dict(size=13, color="#2b2b2b"),
                      legend=dict(orientation="h", y=1.08, x=0, title=None), hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False, linecolor="#d0cfca")
    fig.update_yaxes(gridcolor="#ecebe7", zeroline=False)
    return fig


def fmt(n, casas=0):
    if pd.isna(n):
        return "–"
    return f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- filtros (barra lateral)
op = {k: dados(f"opções {k}", s) for k, s in q.SQL_OPCOES.items()}
ano_min, ano_max = (int(x) for x in op["anos"].iloc[0])

with st.sidebar:
    st.header("Filtros")
    anos = st.slider("Ano", ano_min, ano_max, (ano_min, ano_max))
    regioes = st.multiselect("Região", op["regioes"].iloc[:, 0].tolist(), placeholder="Todas")
    ufs_disp = op["ufs"][op["ufs"].regiao.isin(regioes)] if regioes else op["ufs"]
    ufs = st.multiselect("Estado (UF)", ufs_disp.sigla.tolist(), placeholder="Todos")
    st.caption("Recorte da vítima (óbitos do SIM)")
    racas = st.multiselect("Raça/cor", op["racas"].iloc[:, 0].tolist(), placeholder="Todos")
    faixas = st.multiselect("Faixa etária", op["faixas"].iloc[:, 0].tolist(), placeholder="Todas")
    meios = st.multiselect("Meio da agressão", op["meios"].iloc[:, 0].tolist(), placeholder="Todos")
    st.caption("Registro policial (SINESP)")
    sexos = st.multiselect("Sexo da vítima", op["sexos"].iloc[:, 0].tolist(), default=["Feminino"], placeholder="Todos")
    if st.button("Consultar o banco de novo", use_container_width=True):
        rodar.clear()
        st.rerun()

f = q.Filtros(anos[0], anos[1], regioes, ufs, racas, faixas, meios, sexos)
p = f.params()

# ---------------------------------------------------------------- cabeçalho
st.title("Feminicídio no Brasil por gênero, raça e idade")
st.markdown(
    "Mortes violentas de mulheres de 2019 a 2024, cruzando o registro policial (SINESP-VDE) com a "
    "declaração de óbito (SIM/DataSUS) e a população feminina do IBGE. ODS 5 e ODS 18.")

serie = dados("série anual", q.SQL_SERIE_ANUAL, p)
tot = serie[["populacao", "obitos", "obitos_negras", "obitos_arma", "feminicidios"]].sum()
anos_n = len(serie)

# ---------------------------------------------------------------- KPIs
k1, k2, k3, k4 = st.columns(4)
taxa = 1e5 * tot.obitos / tot.populacao if tot.populacao else float("nan")
taxa_ini = 1e5 * serie.obitos.iloc[0] / serie.populacao.iloc[0] if anos_n else float("nan")
taxa_fim = 1e5 * serie.obitos.iloc[-1] / serie.populacao.iloc[-1] if anos_n else float("nan")
k1.metric("Taxa de óbitos por agressão", f"{fmt(taxa, 2)} por 100 mil",
          delta=f"{fmt(taxa_fim - taxa_ini, 2)} de {anos[0]} a {anos[1]}", delta_color="inverse",
          help="Óbitos de mulheres por agressão (CID X85 a Y09) ÷ população feminina × 100 mil, média do período.")
pct_negras = 100 * tot.obitos_negras / tot.obitos if tot.obitos else float("nan")
k2.metric("Vítimas negras", f"{fmt(pct_negras, 1)}%",
          help="Pretas + pardas sobre o total de óbitos (raça ignorada fica no total, então o número é conservador).")
fem_ini, fem_fim = (serie.feminicidios.iloc[0], serie.feminicidios.iloc[-1]) if anos_n else (0, 0)
k3.metric("Feminicídios registrados", fmt(serie.feminicidios.sum()),
          delta=f"{fmt(100 * (fem_fim - fem_ini) / fem_ini, 1)}% de {anos[0]} a {anos[1]}" if fem_ini else None,
          delta_color="off", help="Vítimas do evento Feminicídio na SINESP, com o filtro de sexo aplicado.")
# raça, idade e meio só existem no SIM: com esses filtros o numerador (SINESP) não acompanha o denominador
captacao = (100 * serie.feminicidios.sum() / tot.obitos
            if tot.obitos and not f.recorte_populacional else float("nan"))
k4.metric("Mortes nomeadas como feminicídio", "–" if pd.isna(captacao) else f"{fmt(captacao, 1)}%",
          help="Feminicídios (SINESP) ÷ óbitos de mulheres por agressão (SIM). Mede quanto das mortes a polícia "
               "classifica como feminicídio. Conceitos próximos, não idênticos.")
st.caption(f"Arma de fogo em {fmt(100 * tot.obitos_arma / tot.obitos if tot.obitos else float('nan'), 1)}% "
           f"dos óbitos do recorte · {fmt(tot.obitos)} óbitos no SIM no período.")
if f.recorte_populacional:
    st.info("Raça/cor, faixa etária e meio da agressão só existem no SIM. Com esses filtros, a taxa por 100 mil "
            "usa no denominador todas as mulheres da região, os feminicídios (SINESP) não mudam e o indicador "
            "de mortes nomeadas como feminicídio fica em branco.")

# ---------------------------------------------------------------- seletor de métrica
METRICAS = {
    "Taxa de óbitos por 100 mil mulheres": ("taxa_obitos", 2),
    "Óbitos de mulheres por agressão (SIM)": ("obitos", 0),
    "Taxa de feminicídio por 100 mil mulheres": ("taxa_fem", 2),
    "Feminicídios registrados (SINESP)": ("feminicidios", 0),
    "% de vítimas negras (SIM)": ("pct_negras", 1),
}


def calcular(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pop = df["populacao"].astype(float)
    df["taxa_obitos"] = 1e5 * df.obitos / pop
    df["taxa_fem"] = 1e5 * df.feminicidios / pop
    df["pct_negras"] = 100 * df.obitos_negras / df.obitos.where(df.obitos > 0)
    return df


metrica = st.radio("Métrica dos gráficos", list(METRICAS), horizontal=True)
col_m, casas = METRICAS[metrica]

# ---------------------------------------------------------------- série anual + drill-down
c1, c2 = st.columns([1, 1.25])
with c1:
    st.subheader("Evolução por ano")
    s = calcular(serie)
    fig = px.line(s, x="ano", y=col_m, markers=True, color_discrete_sequence=[AZUL],
                  labels={"ano": "", col_m: metrica})
    fig.update_traces(line_width=2.5, marker_size=9,
                      hovertemplate="%{x}: %{y:,.2f}<extra></extra>" if casas else "%{x}: %{y:,.0f}<extra></extra>")
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(rangemode="tozero")
    if anos[1] == 2024:
        fig.add_annotation(x=2024, y=s[col_m].iloc[-1], text="SIM 2024 preliminar", showarrow=True,
                           arrowhead=0, ay=-30, font=dict(size=11, color="#6b6a65"))
    st.plotly_chart(layout(fig), use_container_width=True)

with c2:
    st.session_state.setdefault("drill", [])
    # se a região ou a UF mudarem na barra lateral, o drill-down volta para o começo
    assinatura = (tuple(regioes), tuple(ufs))
    if st.session_state.get("drill_filtros") != assinatura:
        st.session_state["drill_filtros"] = assinatura
        st.session_state["drill"] = []
    caminho = st.session_state["drill"]  # [] -> regiões; [região] -> UFs; [região, UF] -> municípios
    nivel = ["regiao", "uf", "municipio"][len(caminho)]
    st.subheader({"regiao": "Por região", "uf": f"Estados do {caminho[0] if caminho else ''}",
                  "municipio": f"Municípios de {caminho[-1] if caminho else ''} (top 15)"}[nivel])
    pr = dict(p)
    if len(caminho) >= 1:
        pr["regioes"] = [caminho[0]]
    if len(caminho) == 2:
        pr["ufs"] = [caminho[1]]
    rk = calcular(dados(f"ranking {nivel}", q.sql_ranking(nivel), pr))
    col_rk, casas_rk = col_m, casas
    if nivel == "municipio" and col_m in ("taxa_obitos", "taxa_fem"):
        col_rk, casas_rk = ("obitos" if col_m == "taxa_obitos" else "feminicidios"), 0
        st.caption("Sem população por município na base: aqui o ranking usa o número absoluto.")
    rk = rk.dropna(subset=[col_rk]).sort_values(col_rk, ascending=False).head(15).sort_values(col_rk)
    fig = px.bar(rk, x=col_rk, y="local", orientation="h", color_discrete_sequence=[AZUL],
                 labels={"local": "", col_rk: ""}, text=rk[col_rk].map(lambda v: fmt(v, casas_rk)))
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0,
                      hovertemplate="%{y}: %{x:,.2f}<extra></extra>")
    fig.update_layout(bargap=0.35)
    evento = st.plotly_chart(layout(fig, 360 if nivel != "municipio" else 460), use_container_width=True,
                             on_select="rerun", selection_mode="points", key=f"rk_{nivel}_{len(caminho)}")
    pontos = evento.selection.points if evento and evento.selection else []
    if pontos and nivel != "municipio":
        st.session_state["drill"] = caminho + [pontos[0]["y"]]
        st.rerun()
    b1, b2 = st.columns(2)
    if caminho and b1.button("← Voltar um nível", use_container_width=True):
        st.session_state["drill"] = caminho[:-1]
        st.rerun()
    if nivel != "municipio":
        b2.caption("Clique numa barra para descer de nível (região → estado → município).")

# ---------------------------------------------------------------- interseccional
st.divider()
st.subheader("O cruzamento raça × idade")
c3, c4 = st.columns(2)
with c3:
    rf = dados("raça × faixa", q.SQL_RACA_FAIXA, p)
    if len(rf):
        rf = rf[rf.faixa != "Ignorada"]
        piv = rf.pivot_table(index="faixa", columns="grupo_racial", values="obitos", aggfunc="sum",
                             fill_value=0, sort=False)
        pct = piv.div(piv.sum(axis=1), axis=0) * 100
        ordem = [c for c in ["Negras (pretas e pardas)", "Não negras", "Ignorada"] if c in pct.columns]
        fig = go.Figure()
        for g in ordem:
            fig.add_bar(y=pct.index, x=pct[g], name=g, orientation="h", marker_color=COR_GRUPO[g],
                        marker_line=dict(color="white", width=2),
                        customdata=piv[g], hovertemplate=f"{g}<br>%{{y}}: %{{x:.1f}}% (%{{customdata:,}} óbitos)<extra></extra>")
        fig.update_layout(barmode="stack", xaxis_title="% dos óbitos da faixa")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(layout(fig, 380), use_container_width=True)
        st.caption("Leitura por linha: em cada faixa de idade, quem são as mulheres mortas.")
with c4:
    mr = dados("meio × raça", q.SQL_MEIO_RACA, p)
    if len(mr):
        mr["pct"] = 100 * mr.obitos / mr.groupby("grupo_racial").obitos.transform("sum")
        fig = px.bar(mr.sort_values("pct"), x="pct", y="meio", color="grupo_racial", barmode="group",
                     orientation="h", color_discrete_map=COR_GRUPO, labels={"pct": "% dos óbitos do grupo", "meio": ""},
                     custom_data=["obitos"])
        fig.update_traces(marker_line_width=0, hovertemplate="%{y}: %{x:.1f}% (%{customdata[0]:,} óbitos)<extra></extra>")
        st.plotly_chart(layout(fig, 380), use_container_width=True)
        st.caption("Como cada grupo racial é morto. Raça ignorada fica de fora deste gráfico.")

# ---------------------------------------------------------------- sazonalidade + tabela
c5, c6 = st.columns([1, 1.25])
with c5:
    st.subheader("Mês do ano")
    ms = dados("mês", q.SQL_MES, p)
    nomes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    ms["mes_nome"] = ms.mes.map(lambda m: nomes[int(m) - 1])
    fig = px.bar(ms, x="mes_nome", y="obitos", color_discrete_sequence=[AZUL], labels={"mes_nome": "", "obitos": "óbitos"})
    fig.update_traces(marker_line_width=0, hovertemplate="%{x}: %{y:,} óbitos<extra></extra>")
    st.plotly_chart(layout(fig, 320), use_container_width=True)
with c6:
    st.subheader("Tabela do recorte")
    tab = calcular(serie)[["ano", "populacao", "obitos", "taxa_obitos", "feminicidios", "taxa_fem", "pct_negras"]]
    tab.columns = ["Ano", "Pop. feminina", "Óbitos (SIM)", "Taxa óbitos/100 mil", "Feminicídios (SINESP)",
                   "Taxa feminicídio/100 mil", "% negras"]
    st.dataframe(tab.round(2), hide_index=True, use_container_width=True)
    st.download_button("Baixar CSV", tab.to_csv(index=False).encode("utf-8"), "recorte_feminicidio.csv", "text/csv")

# ---------------------------------------------------------------- rodapé: prova de consulta ao vivo
st.divider()
ultimo = max(LOG, key=lambda x: x[2]) if LOG else None
if ultimo:
    st.caption(f"Dados consultados no PostgreSQL do Aiven (schema vde) às {ultimo[2]:%H:%M:%S} de "
               f"{ultimo[2]:%d/%m/%Y}. Cache de 2 minutos; o botão na barra lateral força nova consulta.")
with st.expander("Ver as consultas e o tempo de cada uma"):
    st.dataframe(pd.DataFrame([(n, round(ms, 1), w.strftime("%H:%M:%S")) for n, ms, w in LOG],
                              columns=["consulta", "ms", "executada às"]), hide_index=True)
    st.code(q.SQL_SERIE_ANUAL.strip(), language="sql")
st.caption("Fontes: SINESP-VDE (MJSP), SIM (DataSUS), IBGE (Projeção da População 2024). "
           "Projeto da disciplina Big Data e Analytics, UCSal 2026/2.")
