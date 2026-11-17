"""
Carregador do schema estrela da Fase 2 (CSVs tratados) para DataFrames
desnormalizados prontos para analise. Nada e inventado aqui: apenas joins
pelas chaves do modelo entregue na Fase 2.
"""
from pathlib import Path
import pandas as pd

# Caminho para os CSVs tratados da Fase 2 (data/processed do repositorio).
# Pode ser sobrescrito por variavel de ambiente FASE2_PROCESSED.
import os
# Por padrao, procura os CSVs tratados da Fase 2 em data/processed na raiz do
# repositorio. Para apontar para outro lugar, defina a variavel FASE2_PROCESSED.
_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED = Path(os.environ.get("FASE2_PROCESSED", _DEFAULT))


def _csv(nome):
    return pd.read_csv(PROCESSED / f"{nome}.csv")


def dimensoes():
    tempo = _csv("dim_tempo")
    uf = _csv("dim_uf").rename(columns={"nome": "uf_nome"})
    mun = (_csv("dim_municipio")
           .rename(columns={"nome": "mun_nome"})
           .merge(uf, on="cod_uf"))
    sexo = _csv("dim_sexo").rename(columns={"codigo": "sexo_cod",
                                            "descricao": "sexo"})
    raca = _csv("dim_raca_cor").rename(columns={"descricao": "raca"})
    faixa = _csv("dim_faixa_etaria").rename(columns={"descricao": "faixa"})
    evento = _csv("dim_evento").rename(columns={"nome": "evento"})
    meio = _csv("dim_meio_agressao").rename(columns={"descricao": "meio"})
    return dict(tempo=tempo, uf=uf, mun=mun, sexo=sexo, raca=raca,
                faixa=faixa, evento=evento, meio=meio)


def fato_sinesp(d=None):
    """Vitimas registradas pela SINESP (registro policial), desnormalizado."""
    d = d or dimensoes()
    fv = _csv("fato_vitimas_sinesp")
    return (fv.merge(d["tempo"], on="id_tempo")
              .merge(d["mun"], on="id_municipio")
              .merge(d["evento"], on="id_evento")
              .merge(d["sexo"], on="id_sexo"))


def fato_sim(d=None):
    """Obitos de mulheres por agressao (SIM/DataSUS), desnormalizado."""
    d = d or dimensoes()
    fo = _csv("fato_obitos_agressao_sim")
    return (fo.merge(d["tempo"], on="id_tempo")
              .merge(d["mun"], on="id_municipio")
              .merge(d["sexo"], on="id_sexo")
              .merge(d["raca"], on="id_raca_cor")
              .merge(d["faixa"], on="id_faixa")
              .merge(d["meio"], on="id_meio"))


if __name__ == "__main__":
    d = dimensoes()
    v = fato_sinesp(d)
    o = fato_sim(d)
    print("SINESP:", v.shape, "| soma vitimas:", int(v.qt_vitimas.sum()))
    print("SIM   :", o.shape, "| soma obitos :", int(o.qt_obitos.sum()))
    print("\nColunas SINESP:", list(v.columns))
    print("Colunas SIM   :", list(o.columns))
