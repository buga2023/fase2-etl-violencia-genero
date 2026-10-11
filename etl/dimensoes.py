"""Dimensões: estáticas (config) + municípios a partir da API de localidades do IBGE (JSON)."""
import json

import pandas as pd

from . import config as cfg
from .utils import normalizar_texto


def dim_estaticas() -> dict[str, pd.DataFrame]:
    eventos = [(i, nome, g, v) for i, (nome, (g, v)) in enumerate(cfg.EVENTOS.items(), start=1)]
    return {
        "dim_uf": pd.DataFrame(cfg.UFS, columns=["cod_uf", "sigla", "nome", "regiao"]),
        "dim_sexo": pd.DataFrame(cfg.SEXOS, columns=["id_sexo", "codigo", "descricao"]),
        "dim_raca_cor": pd.DataFrame(cfg.RACAS, columns=["id_raca_cor", "descricao", "negra"]),
        "dim_faixa_etaria": pd.DataFrame(cfg.FAIXAS, columns=["id_faixa", "descricao", "idade_min", "idade_max"])
                               .astype({"idade_min": "Int64", "idade_max": "Int64"}),
        "dim_evento": pd.DataFrame(eventos, columns=["id_evento", "nome", "grupo", "violencia_genero"]),
        "dim_meio_agressao": pd.DataFrame(cfg.MEIOS, columns=["id_meio", "descricao", "cids"]),
    }


def dim_tempo() -> pd.DataFrame:
    datas = pd.date_range(f"{cfg.ANO_INICIO}-01-01", f"{cfg.ANO_FIM}-12-01", freq="MS")
    return pd.DataFrame({
        "id_tempo": datas.year * 100 + datas.month,
        "ano": datas.year, "mes": datas.month, "trimestre": datas.quarter,
        "data_referencia": datas.date,
    })


def dim_municipio() -> pd.DataFrame:
    """Lê o JSON do IBGE (semi-estruturado) e achata na tabela de municípios.

    Acrescenta uma linha 'NÃO INFORMADO' por UF para receber registros
    sem município identificável — preserva o total da UF em vez de descartar.
    """
    bruto = json.loads((cfg.DIR_RAW / "ibge" / "municipios.json").read_text(encoding="utf-8"))
    df = pd.json_normalize(bruto)
    df = pd.DataFrame({
        "cod_ibge": df["municipio-id"].astype("int64"),
        "nome": df["municipio-nome"].str.strip(),
        "cod_uf": df["UF-id"].astype("int64"),
    })
    nao_inf = pd.DataFrame({"cod_ibge": pd.NA, "nome": cfg.MUNICIPIO_NAO_INFORMADO,
                            "cod_uf": [c for c, *_ in cfg.UFS]})
    df = pd.concat([df, nao_inf], ignore_index=True)
    df["cod_ibge"] = df["cod_ibge"].astype("Int64")
    df["nome_normalizado"] = df["nome"].map(normalizar_texto)
    df.insert(0, "id_municipio", range(1, len(df) + 1))
    return df
