"""Padroniza os CSVs do SIM 2022 e 2023 do OpenDataSUS para o layout que o ETL lê.

Esses dois anos são publicados (Mortalidade_Geral_<ano>_csv.zip) SEM linha de
cabeçalho e com DTOBITO em 'DD-MM-AAAA'. Os demais anos têm cabeçalho e
DTOBITO em 'DDMMAAAA'. Este passo não trata dado nenhum: só nomeia as 6
colunas usadas pelo ETL (pela posição do layout oficial) e reescreve a data
no formato dos outros anos. O ZIP original fica em data/raw/sim/ e entra no
manifest.json e na meta_carga (arquivo_origem / sha256_origem).
"""
import csv
import io
import zipfile
from pathlib import Path

COLUNAS = ["DTOBITO", "IDADE", "SEXO", "RACACOR", "CAUSABAS", "CODMUNOCOR"]
# posição (base 0) de cada coluna no arquivo sem cabeçalho, conferida contra
# o layout com cabeçalho de 2021 (para 2022) e de 2024 (para 2023, que tem "contador")
POSICOES = {
    2022: [2, 7, 8, 9, 45, 19],
    2023: [3, 8, 9, 10, 45, 19],
}


def _data(valor: str) -> str:
    partes = valor.strip().split("-")
    if len(partes) != 3:
        return valor.strip()
    d, m, a = partes
    return f"{d.zfill(2)}{m.zfill(2)}{a}"


def padronizar(origem_zip: Path, destino: Path, ano: int) -> int:
    """Escreve o CSV padronizado e devolve o número de linhas. Falha se houver linha curta."""
    pos = POSICOES[ano]
    n, curtas = 0, 0
    tmp = destino.with_suffix(destino.suffix + ".part")
    with zipfile.ZipFile(origem_zip) as z:
        membro = next(m for m in z.namelist() if m.lower().endswith(".csv"))
        with z.open(membro) as bruto, open(tmp, "w", encoding="latin-1", newline="") as out:
            leitor = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
            escritor = csv.writer(out, delimiter=";", lineterminator="\n")
            escritor.writerow(COLUNAS)
            for linha in leitor:
                if len(linha) <= max(pos):
                    curtas += 1
                    continue
                valores = [linha[p] for p in pos]
                valores[0] = _data(valores[0])
                escritor.writerow(valores)
                n += 1
    if curtas:
        tmp.unlink()
        raise ValueError(f"{Path(origem_zip).name}: {curtas} linha(s) com menos colunas que o layout esperado")
    tmp.replace(destino)
    return n
