"""População feminina por UF e ano a partir da Projeção da População do IBGE (revisão 2024).

A planilha vem em formato largo (uma coluna por ano, de 2000 a 2070) e com uma linha por
grupo de idade de 5 anos. Aqui somamos os grupos, ficamos só com Mulheres e com as 27 UFs
(códigos 11 a 53) e despivotamos para uma linha por UF e ano.
"""
import pandas as pd

from . import config as cfg


def transformar() -> pd.DataFrame:
    arq = cfg.DIR_RAW / "ibge" / cfg.ARQ_IBGE_PROJECAO
    df = pd.read_excel(arq, header=5)
    lidas = len(df)
    df = df[(df["SEXO"].str.strip() == "Mulheres") & (df["CÓD."] >= 11)]
    anos = [a for a in range(cfg.ANO_INICIO, cfg.ANO_FIM + 1)]
    df = df.rename(columns={"CÓD.": "cod_uf"})[["cod_uf"] + anos]
    pop = (df.groupby("cod_uf")[anos].sum()
             .reset_index()
             .melt(id_vars="cod_uf", var_name="ano", value_name="populacao"))
    pop["ano"] = pop["ano"].astype(int)
    pop["populacao"] = pop["populacao"].round().astype(int)
    if len(pop) != 27 * len(anos):
        raise ValueError(f"esperava {27 * len(anos)} linhas de população, veio {len(pop)}")
    pop = pop.sort_values(["cod_uf", "ano"]).reset_index(drop=True)
    pop.attrs["linhas_lidas"] = lidas
    return pop
