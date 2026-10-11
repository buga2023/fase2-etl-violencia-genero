"""TRATAMENTO — SINESP-VDE (vítimas por município/mês/evento, quebradas por sexo).

Passos (cada um registrado no log de qualidade):
 1. padroniza nomes de coluna (as planilhas variam entre anos)
 2. converte data_referencia em data (dia 01) e aplica o recorte 2019–2024
 3. mantém só os eventos de interesse (comparação sem acento/caixa)
 4. converte contagens texto → inteiro e valida sexo × total_vitima
 5. remove duplicatas exatas
 6. casa o município pelo nome com o IBGE (com tabela de aliases)
 7. despivota feminino/masculino/nao_informado em linhas (dimensão sexo)
 8. agrega no grão final (mês × município × evento × sexo)
"""
import pandas as pd

from . import config as cfg
from .utils import chave_nome, inteiro_br, normalizar_coluna, normalizar_texto


def _ler(arq) -> pd.DataFrame:
    if arq.suffix == ".xlsx":
        df = pd.read_excel(arq, dtype=object)
    else:
        df = pd.read_csv(arq, sep=None, engine="python", dtype=str, encoding="utf-8-sig")
    df.columns = [normalizar_coluna(c) for c in df.columns]
    return df


def _data_referencia(df: pd.DataFrame) -> pd.Series:
    if "data_referencia" in df:
        bruto = df["data_referencia"]
        data = pd.to_datetime(bruto, errors="coerce", dayfirst=True)
        # formato 'MM/AAAA' (espelho ISP) não é entendido acima
        faltando = data.isna() & bruto.notna()
        if faltando.any():
            data[faltando] = pd.to_datetime(bruto[faltando].astype(str).str.strip(),
                                            format="%m/%Y", errors="coerce")
    elif {"ano", "mes"} <= set(df.columns):
        data = pd.to_datetime(dict(year=inteiro_br(df["ano"]), month=inteiro_br(df["mes"]), day=1),
                              errors="coerce")
    else:
        raise ValueError("SINESP: sem data_referencia nem ano/mes")
    return data.dt.to_period("M").dt.to_timestamp()


def transformar(arquivos, dim_municipio: pd.DataFrame, dim_evento: pd.DataFrame):
    log, cargas = [], []
    partes = []
    for arq in arquivos:
        df = _ler(arq)
        faltam = [c for c in cfg.COLUNAS_SINESP_OBRIGATORIAS if c not in df.columns]
        if faltam:
            raise ValueError(f"{arq.name}: colunas ausentes {faltam}")
        df["arquivo"] = arq.name
        cargas.append({"arquivo": arq.name, "linhas_lidas": len(df)})
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    log.append(("Linhas lidas (todos os arquivos)", len(df)))

    # 2. data + recorte temporal
    df["data"] = _data_referencia(df)
    sem_data = df["data"].isna().sum()
    df = df[df["data"].dt.year.between(cfg.ANO_INICIO, cfg.ANO_FIM)]
    log.append((f"Após recorte {cfg.ANO_INICIO}–{cfg.ANO_FIM} (sem data válida: {sem_data})", len(df)))

    # 3. eventos de interesse
    mapa_evento = {normalizar_texto(n): i for i, n in zip(dim_evento["id_evento"], dim_evento["nome"])}
    df["id_evento"] = df["evento"].map(normalizar_texto).map(mapa_evento)
    nao_encontrados = sorted(set(mapa_evento) - set(df["evento"].map(normalizar_texto)))
    df = df[df["id_evento"].notna()].copy()
    log.append((f"Após filtro de {len(mapa_evento)} eventos de interesse", len(df)))

    # evidência para descartar colunas de detalhe (preenchidas em outros indicadores)
    for c in ("agente", "arma", "faixa_etaria"):
        if c in df:
            preenchidas = int(df[c].notna().sum() - (df[c].astype("string").str.strip() == "").sum())
            log.append((f"Linhas do escopo com '{c}' preenchida (coluna descartada)", preenchidas))

    # 4. contagens e coerência sexo × total
    for c in ["feminino", "masculino", "nao_informado", "total_vitima"]:
        df[c] = inteiro_br(df[c])
    soma_sexo = df[["feminino", "masculino", "nao_informado"]].sum(axis=1)
    sem_quebra = (soma_sexo == 0) & (df["total_vitima"] > 0)
    df.loc[sem_quebra, "nao_informado"] = df.loc[sem_quebra, "total_vitima"]
    divergentes = int(((soma_sexo != df["total_vitima"]) & ~sem_quebra).sum())
    log.append((f"Linhas sem quebra por sexo → total atribuído a 'Não informado'", int(sem_quebra.sum())))
    log.append((f"Linhas com soma por sexo ≠ total_vitima (mantida a quebra por sexo)", divergentes))

    # 5. duplicatas: mesma linha publicada em dois arquivos. Linhas idênticas DENTRO do
    #    mesmo arquivo são registros distintos (o DF informa uma linha por Região
    #    Administrativa, todas como 'BRASÍLIA') e por isso são mantidas e somadas.
    chave_dup = [c for c in df.columns if c != "arquivo"]
    repetidas = df.duplicated(subset=chave_dup + ["arquivo"], keep="first")
    log.append(("Linhas repetidas no mesmo arquivo (mantidas: DF informa por Região Administrativa)",
                int(repetidas.sum())))
    df["_ocorrencia"] = df.groupby(chave_dup + ["arquivo"], dropna=False, sort=False).cumcount()
    antes = len(df)
    df = df.drop_duplicates(subset=chave_dup + ["_ocorrencia"]).drop(columns="_ocorrencia")
    log.append(("Duplicatas entre arquivos removidas", antes - len(df)))

    # 6. município → dim_municipio
    df["uf"] = df["uf"].astype(str).str.strip().str.upper()
    uf_invalida = ~df["uf"].isin(cfg.SIGLA_PARA_COD)
    log.append(("Linhas descartadas por UF inválida", int(uf_invalida.sum())))
    df = df[~uf_invalida].copy()
    df["cod_uf"] = df["uf"].map(cfg.SIGLA_PARA_COD)
    df["nome_norm"] = df["municipio"].map(normalizar_texto)
    df["nome_norm"] = [cfg.ALIASES_MUNICIPIO.get((u, n), n) for u, n in zip(df["uf"], df["nome_norm"])]
    df.loc[df["nome_norm"].isin(cfg.VALORES_SEM_MUNICIPIO), "nome_norm"] = normalizar_texto(cfg.MUNICIPIO_NAO_INFORMADO)

    chave = pd.Series(dim_municipio["id_municipio"].values,
                      index=pd.MultiIndex.from_arrays([dim_municipio["cod_uf"],
                                                       dim_municipio["nome_normalizado"].map(chave_nome)]))
    df["id_municipio"] = pd.MultiIndex.from_arrays([df["cod_uf"], df["nome_norm"].map(chave_nome)]).map(chave)
    nao_casados = (df.loc[df["id_municipio"].isna(), ["uf", "municipio"]]
                   .drop_duplicates().sort_values(["uf", "municipio"]))
    # sem correspondência → 'NÃO INFORMADO' da UF (preserva o total estadual)
    nao_inf = dim_municipio[dim_municipio["cod_ibge"].isna()].set_index("cod_uf")["id_municipio"]
    df["id_municipio"] = df["id_municipio"].fillna(df["cod_uf"].map(nao_inf)).astype("int64")
    log.append(("Nomes de município sem correspondência no IBGE (→ 'NÃO INFORMADO' da UF)", len(nao_casados)))

    # 7. despivotar sexo
    longo = df.melt(id_vars=["data", "id_municipio", "id_evento"],
                    value_vars=["feminino", "masculino", "nao_informado"],
                    var_name="sexo", value_name="qt_vitimas")
    longo["id_sexo"] = longo["sexo"].map({"feminino": 1, "masculino": 2, "nao_informado": 3})
    longo = longo[longo["qt_vitimas"] > 0]

    # 8. agregação no grão do fato
    longo["id_tempo"] = longo["data"].dt.year * 100 + longo["data"].dt.month
    fato = (longo.groupby(["id_tempo", "id_municipio", "id_evento", "id_sexo"], as_index=False)["qt_vitimas"].sum())
    fato = fato.astype({"id_tempo": "int64", "id_evento": "int64", "id_sexo": "int64"})
    log.append(("Linhas no fato_vitimas_sinesp (grão final)", len(fato)))
    log.append(("Total de vítimas no fato (conferência)", int(fato["qt_vitimas"].sum())))

    for c in cargas:
        c["linhas_apos_filtro"] = int((df["arquivo"] == c["arquivo"]).sum())
    return fato, log, cargas, {"eventos_nao_encontrados": nao_encontrados,
                               "municipios_nao_casados": nao_casados}
