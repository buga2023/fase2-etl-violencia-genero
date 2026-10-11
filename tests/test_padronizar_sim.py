"""Padronização dos CSVs do SIM 2022/2023 publicados sem cabeçalho."""
import zipfile

from scripts.padronizar_sim import padronizar


def _zip(tmp_path, linhas):
    z = tmp_path / "orig.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("dados.csv", "\n".join(linhas) + "\n")
    return z


def test_layout_2022_sem_cabecalho(tmp_path):
    campos = [""] * 87
    campos[2], campos[7], campos[8], campos[9], campos[19], campos[45] = (
        "05-03-2022", "435", "2", "4", "355030", "X954")
    destino = tmp_path / "out.csv"
    n = padronizar(_zip(tmp_path, [";".join(campos)]), destino, 2022)
    assert n == 1
    assert destino.read_text(encoding="latin-1").splitlines() == [
        "DTOBITO;IDADE;SEXO;RACACOR;CAUSABAS;CODMUNOCOR",
        "05032022;435;2;4;X954;355030",
    ]


def test_layout_2023_com_contador(tmp_path):
    campos = [""] * 86
    campos[3], campos[8], campos[9], campos[10], campos[19], campos[45] = (
        "1-12-2023", "430", "2", "2", "292740", "Y09")
    destino = tmp_path / "out.csv"
    padronizar(_zip(tmp_path, [";".join(campos)]), destino, 2023)
    assert destino.read_text(encoding="latin-1").splitlines()[1] == "01122023;430;2;2;Y09;292740"
