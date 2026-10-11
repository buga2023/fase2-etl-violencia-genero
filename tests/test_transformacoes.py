"""Testes das regras de tratamento sobre os dados sintéticos (pytest)."""
import pandas as pd
import pytest

from etl import config as cfg
from etl import dimensoes, transform_sim, transform_sinesp
from etl.utils import inteiro_br, normalizar_texto
from tests.gerar_fixtures import gerar


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory, monkeypatch_module):
    raw = tmp_path_factory.mktemp("raw")
    gerar(raw)
    monkeypatch_module.setattr(cfg, "DIR_RAW", raw)
    dim_mun = dimensoes.dim_municipio()
    dim_ev = dimensoes.dim_estaticas()["dim_evento"]
    return raw, dim_mun, dim_ev


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def id_mun(dim, nome):
    return int(dim.loc[dim["nome"] == nome, "id_municipio"].iloc[0])


def test_inteiro_br():
    s = pd.Series(["1.234", "12", "", None, "1.234.567", "3,0"])
    assert inteiro_br(s).tolist() == [1234, 12, 0, 0, 1234567, 3]


def test_normalizar_texto():
    assert normalizar_texto("  Sant'Ana do Livramento ") == "SANTANA DO LIVRAMENTO"
    assert normalizar_texto("Feminicídio") == normalizar_texto("FEMINICIDIO")


def test_idade_e_faixa():
    # unidade: 0 minutos, 1 horas, 2 dias, 3 meses (< 1 ano), 4 anos, 5 = 100 + valor; 999 ignorada
    anos = transform_sim.idade_em_anos(pd.Series(["435", "502", "215", "010", "123", "311", "", "999"]))
    assert anos.tolist()[:6] == [35, 102, 0, 0, 0, 0]
    assert anos.isna().tolist()[6:] == [True, True]
    assert transform_sim.faixa_etaria(anos).tolist() == [5, 8, 1, 1, 1, 1, 9, 9]


def test_filtro_cid_agressao():
    cids = pd.Series(["X849", "X850", "X954", "Y099", "Y100", "X9", "Y0", "XA01", None])
    assert transform_sim.cid_agressao(cids).tolist() == [False, True, True, True, False, False, False, False, False]


def test_sinesp(ambiente):
    raw, dim_mun, dim_ev = ambiente
    fato, log, cargas, extras = transform_sinesp.transformar(
        sorted((raw / "sinesp").glob("*.xlsx")), dim_mun, dim_ev)
    ssa = id_mun(dim_mun, "Salvador")
    hom = int(dim_ev.loc[dim_ev["nome"] == "Homicídio doloso", "id_evento"].iloc[0])
    # cópia da mesma linha em outro arquivo removida e '1.050' convertido
    linha = fato.query("id_tempo == 201903 and id_municipio == @ssa and id_evento == @hom and id_sexo == 2")
    assert linha["qt_vitimas"].item() == 1050
    # alias e apóstrofo casam com o IBGE
    assert id_mun(dim_mun, "Embu das Artes") in set(fato["id_municipio"])
    assert id_mun(dim_mun, "Sant'Ana do Livramento") in set(fato["id_municipio"])
    # sem quebra por sexo → 'Não informado'
    lauro = id_mun(dim_mun, "Lauro de Freitas")
    assert fato.query("id_municipio == @lauro")[["id_sexo", "qt_vitimas"]].values.tolist() == [[3, 3]]
    # fora do recorte, UF inválida e evento fora do escopo não entram
    assert fato["id_tempo"].min() >= 201901
    # município inexistente vai para 'NÃO INFORMADO' de PE
    assert extras["municipios_nao_casados"]["municipio"].tolist() == ["Cidade Fantasma"]
    # DF informa uma linha por Região Administrativa, todas como 'Brasília': as duas contam
    bsb = id_mun(dim_mun, "Brasília")
    assert fato.query("id_municipio == @bsb")["qt_vitimas"].sum() == 2
    # total confere: 2 + (5+1050+1) + 1 + 4 + 1 + 3 + 3 (BA n/inf) + 1 + 2 (DF) + 6 + 100
    assert fato["qt_vitimas"].sum() == 1179


def test_sim(ambiente):
    raw, dim_mun, _ = ambiente
    fato, log, cargas = transform_sim.transformar(sorted((raw / "sim").glob("*.csv")), dim_mun)
    assert fato["qt_obitos"].sum() == 5            # 9 linhas − masc − infarto − 2018 − UF 99
    assert set(fato["id_sexo"]) == {1}
    ssa = id_mun(dim_mun, "Salvador")
    assert fato.query("id_municipio == @ssa")["qt_obitos"].sum() == 3
    assert 201903 in set(fato["id_tempo"])         # '1032019' recuperado como 01/03/2019
    assert set(fato["id_raca_cor"]) == {1, 2, 4, 9}
    assert cargas[0]["linhas_lidas"] == 9
