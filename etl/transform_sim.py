"""TRATAMENTO — SIM/DataSUS (uma linha por Declaração de Óbito).

O arquivo nacional tem ~1,5 milhão de linhas/ano. Para caber na memória e no
limite de 1 GB do Aiven, cada bloco (chunk) é filtrado e AGREGADO antes de
seguir; só os agregados são concatenados.

Por bloco:
 1. lê só as 6 colunas necessárias, tudo como texto (evita perder zeros à esquerda)
 2. filtra causa básica CID-10 X85–Y09 (agressões) e sexo feminino
 3. DTOBITO 'DDMMAAAA' → data; aplica o recorte 2019–2024
 4. IDADE codificada (unidade+valor) → anos → faixa etária
 5. RACACOR → domínio IBGE (vazio/inválido = 9 Ignorada)
 6. CAUSABAS → meio da agressão
 7. CODMUNOCOR (6 dígitos) → município IBGE (7 dígitos)
 8. agrega no grão do fato
"""
import pandas as pd

from . import config as cfg

COD_MEIO = {**{f"X{n}": 1 for n in (93, 94, 95)}, "X99": 2, "Y00": 3, "X91": 4, "Y04": 5, "Y05": 5}


def _blocos(arq):
    if arq.suffix == ".parquet":  # saída do PySUS (DBC convertido)
        df = pd.read_parquet(arq, columns=cfg.COLUNAS_SIM).astype("string")
        for i in range(0, len(df), cfg.CHUNK_SIZE):
            yield df.iloc[i:i + cfg.CHUNK_SIZE]
        return
    # OpenDataSUS: ';' e aspas; latin-1 cobre os arquivos antigos e é seguro p/ estas colunas
    yield from pd.read_csv(arq, sep=";", dtype=str, usecols=lambda c: c.strip('"') in cfg.COLUNAS_SIM,
                           chunksize=cfg.CHUNK_SIZE, encoding="latin-1", quotechar='"')


def idade_em_anos(idade: pd.Series) -> pd.Series:
    """IDADE do SIM: 1º dígito = unidade (0 min, 1 h, 2 dias, 3 meses → 0 anos; 4 = anos; 5 = 100 + valor).

    Unidade 9 / código '999' = ignorada (NA)."""
    s = idade.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    s = s.mask(s == "").str.zfill(3)                     # vazio = ignorada, não "000"
    unidade = pd.to_numeric(s.str[0], errors="coerce")
    valor = pd.to_numeric(s.str[1:3], errors="coerce")
    anos = pd.Series(pd.NA, index=s.index, dtype="Int64")
    anos[unidade.between(0, 3)] = 0
    anos[unidade == 4] = valor[unidade == 4]
    anos[unidade == 5] = 100 + valor[unidade == 5]
    return anos


def cid_agressao(causabas: pd.Series) -> pd.Series:
    """CID-10 X85–Y09 (agressões). Regex explícita: comparar texto com between() aceitaria 'X9' ou 'Y0'."""
    return causabas.astype("string").str.strip().str.upper().str.match(r"^(X8[5-9]|X9\d|Y0\d)").fillna(False).astype(bool)


def faixa_etaria(anos: pd.Series) -> pd.Series:
    faixa = pd.Series(9, index=anos.index, dtype="int64")
    for id_f, _, mn, mx in cfg.FAIXAS:
        if mn is not None:
            faixa[anos.between(mn, mx).fillna(False).astype(bool)] = id_f
    return faixa


def _tratar_bloco(b: pd.DataFrame, cod6_para_id: pd.Series, nao_inf_por_uf: pd.Series, stats: dict):
    b = b.rename(columns=lambda c: c.strip('"'))
    stats["lidas"] += len(b)

    sexo = b["SEXO"].astype("string").str.strip()
    b = b[cid_agressao(b["CAUSABAS"]).values & sexo.isin(cfg.SEXO_FEMININO_SIM).fillna(False).values].copy()
    stats["agressao_mulher"] += len(b)
    if b.empty:
        return None

    dt = b["DTOBITO"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)
    data = pd.to_datetime(dt, format="%d%m%Y", errors="coerce")
    stats["data_invalida"] += int(data.isna().sum())
    b["id_tempo"] = data.dt.year * 100 + data.dt.month
    b = b[data.dt.year.between(cfg.ANO_INICIO, cfg.ANO_FIM).fillna(False).values]
    stats["no_recorte"] += len(b)

    b["id_faixa"] = faixa_etaria(idade_em_anos(b["IDADE"]))
    raca = pd.to_numeric(b["RACACOR"], errors="coerce")
    b["id_raca_cor"] = raca.where(raca.isin([1, 2, 3, 4, 5]), 9).astype("int64")
    b["id_meio"] = b["CAUSABAS"].astype("string").str.strip().str.upper().str[:3].map(COD_MEIO).fillna(6).astype("int64")

    cod = b["CODMUNOCOR"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str[:6]
    cod6 = pd.to_numeric(cod, errors="coerce")
    b["id_municipio"] = cod6.map(cod6_para_id)
    sem = b["id_municipio"].isna()
    stats["mun_nao_casado"] += int(sem.sum())
    b.loc[sem, "id_municipio"] = (cod6[sem] // 10000).map(nao_inf_por_uf)   # 2 primeiros dígitos = UF
    descartar = b["id_municipio"].isna()
    stats["sem_uf"] += int(descartar.sum())
    b = b[~descartar]

    b["id_sexo"] = 1
    return (b.groupby(["id_tempo", "id_municipio", "id_sexo", "id_raca_cor", "id_faixa", "id_meio"])
             .size().rename("qt_obitos").reset_index())


def transformar(arquivos, dim_municipio: pd.DataFrame):
    com_cod = dim_municipio[dim_municipio["cod_ibge"].notna()]
    cod6_para_id = pd.Series(com_cod["id_municipio"].values, index=(com_cod["cod_ibge"].astype("int64") // 10).values)
    nao_inf_por_uf = dim_municipio[dim_municipio["cod_ibge"].isna()].set_index("cod_uf")["id_municipio"]

    agregados, cargas = [], []
    total = dict(lidas=0, agressao_mulher=0, data_invalida=0, no_recorte=0, mun_nao_casado=0, sem_uf=0)
    for arq in arquivos:
        stats = dict.fromkeys(total, 0)
        for bloco in _blocos(arq):
            r = _tratar_bloco(bloco, cod6_para_id, nao_inf_por_uf, stats)
            if r is not None:
                agregados.append(r)
        cargas.append({"arquivo": arq.name, "linhas_lidas": stats["lidas"],
                       "linhas_apos_filtro": stats["no_recorte"] - stats["sem_uf"]})
        for k in total:
            total[k] += stats[k]

    cols = ["id_tempo", "id_municipio", "id_sexo", "id_raca_cor", "id_faixa", "id_meio"]
    fato = (pd.concat(agregados).groupby(cols, as_index=False)["qt_obitos"].sum()
            if agregados else pd.DataFrame(columns=cols + ["qt_obitos"]))
    fato = fato.astype("int64")
    log = [
        ("Declarações de óbito lidas", total["lidas"]),
        (f"Após filtro CID-10 {cfg.CID_INICIO}–{cfg.CID_FIM} + sexo feminino", total["agressao_mulher"]),
        ("  dessas, com DTOBITO inválida", total["data_invalida"]),
        (f"Após recorte {cfg.ANO_INICIO}–{cfg.ANO_FIM}", total["no_recorte"]),
        ("Código de município sem correspondência (→ 'NÃO INFORMADO' da UF)", total["mun_nao_casado"]),
        ("Descartadas sem UF identificável", total["sem_uf"]),
        ("Linhas no fato_obitos_agressao_sim (grão final)", len(fato)),
        ("Total de óbitos no fato (conferência)", int(fato["qt_obitos"].sum()) if len(fato) else 0),
    ]
    return fato, log, cargas
