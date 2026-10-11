"""Gera arquivos SINTÉTICOS no mesmo formato das fontes reais, com os defeitos
típicos de cada uma, para testar o pipeline sem depender de download.

    python -m tests.gerar_fixtures <pasta_raw>
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

MUNICIPIOS = [  # cod IBGE, nome, UF-id, UF-sigla
    (2927408, "Salvador", 29, "BA"), (2910800, "Feira de Santana", 29, "BA"),
    (2919207, "Lauro de Freitas", 29, "BA"), (3550308, "São Paulo", 35, "SP"),
    (3515004, "Embu das Artes", 35, "SP"), (3304557, "Rio de Janeiro", 33, "RJ"),
    (2611606, "Recife", 26, "PE"), (4317103, "Sant'Ana do Livramento", 43, "RS"),
    (5300108, "Brasília", 53, "DF"),
]

COLS_VDE = ["uf", "municipio", "evento", "data_referencia", "agente", "arma", "faixa_etaria",
            "feminino", "masculino", "nao_informado", "total", "total_peso", "total_vitima"]


def _vde(uf, mun, ev, data, f, m, ni, tv):
    return [uf, mun, ev, data, None, None, None, f, m, ni, None, None, tv]


def gerar(raw: Path):
    for sub in ("sinesp", "sim", "ibge"):
        (raw / sub).mkdir(parents=True, exist_ok=True)

    # IBGE — formato da API /localidades/municipios?view=nivelado
    (raw / "ibge" / "municipios.json").write_text(json.dumps([
        {"municipio-id": c, "municipio-nome": n, "UF-id": u, "UF-sigla": s, "regiao-nome": "-"}
        for c, n, u, s in MUNICIPIOS], ensure_ascii=False), encoding="utf-8")

    d = datetime
    vde_2019 = [
        _vde("BA", "Salvador", "Feminicídio", d(2019, 3, 1), 2, 0, 0, 2),
        _vde("BA", "Salvador", "Homicídio doloso", d(2019, 3, 1), 5, "1.050", 1, "1.056"),  # texto c/ milhar
        _vde("DF", "Brasília", "Feminicídio", d(2019, 9, 1), 1, 0, 0, 1),                   # DF: uma linha por RA,
        _vde("DF", "Brasília", "Feminicídio", d(2019, 9, 1), 1, 0, 0, 1),                   # idênticas e legítimas
        _vde("ba ", "FEIRA DE SANTANA", "FEMINICIDIO", d(2019, 4, 1), 1, 0, 0, 1),          # caixa/acentos
        _vde("SP", "Embu", "Estupro", d(2019, 5, 1), 3, 1, 0, 4),                           # alias IBGE
        _vde("RS", "Santana do Livramento", "Feminicídio", d(2019, 6, 1), 1, 0, 0, 1),      # apóstrofo
        _vde("BA", "Lauro de Freitas", "Tentativa de feminicídio", d(2019, 7, 1), None, None, None, 3),  # sem quebra
        _vde("BA", "Não informado", "Homicídio doloso", d(2019, 7, 1), 1, 2, 0, 3),
        _vde("PE", "Cidade Fantasma", "Feminicídio", d(2019, 8, 1), 1, 0, 0, 1),            # não casa
        _vde("XX", "Salvador", "Feminicídio", d(2019, 8, 1), 1, 0, 0, 1),                   # UF inválida
        _vde("SP", "São Paulo", "Roubo de veículo", d(2019, 8, 1), 0, 0, 0, 0),              # fora do escopo
        _vde("SP", "São Paulo", "Feminicídio", d(2018, 12, 1), 4, 0, 0, 4),                 # fora do recorte
    ]
    vde_2020 = [
        _vde("RJ", "Rio de Janeiro", "Feminicídio", d(2020, 1, 1), 6, 0, 0, 6),
        _vde("BA", "Salvador", "Homicídio doloso", d(2019, 3, 1), 5, "1.050", 1, "1.056"),  # mesma linha em outro arquivo
        _vde("RJ", "Rio de Janeiro", "Homicídio doloso", d(2020, 1, 1), 10, 90, 0, 101),    # soma ≠ total
    ]
    pd.DataFrame(vde_2019, columns=COLS_VDE).to_excel(raw / "sinesp" / "BancoVDE 2019.xlsx", index=False)
    pd.DataFrame(vde_2020, columns=COLS_VDE).to_excel(raw / "sinesp" / "BancoVDE 2020.xlsx", index=False)

    # SIM — CSV OpenDataSUS: ';', aspas, todas as colunas como texto
    sim = [  # DTOBITO, SEXO, RACACOR, IDADE, CAUSABAS, CODMUNOCOR
        ("1032019", "2", "4", "435", "X954", "292740"),    # zero à esquerda perdido; parda, 35a, arma de fogo
        ("15032019", "2", "2", "428", "X990", "292740"),   # preta, 28a, cortante
        ("15032019", "F", "", "", "Y090", "292740"),       # sexo 'F' antigo, raça e idade ignoradas
        ("20052019", "2", "1", "502", "X910", "355030"),   # 102 anos, enforcamento
        ("20052019", "2", "4", "215", "Y00", "290000"),    # 15 meses → 0 anos; município inexistente → BA n/inf.
        ("20052019", "2", "4", "430", "X954", "999999"),   # UF 99 inexistente → descartado
        ("20052019", "1", "4", "430", "X954", "292740"),   # masculino → fora
        ("20052019", "2", "4", "470", "I219", "292740"),   # infarto → fora
        ("31122018", "2", "4", "430", "X954", "292740"),   # fora do recorte
    ]
    df = pd.DataFrame(sim, columns=["DTOBITO", "SEXO", "RACACOR", "IDADE", "CAUSABAS", "CODMUNOCOR"])
    df.insert(0, "ORIGEM", "1"); df.insert(1, "TIPOBITO", "2")
    df.to_csv(raw / "sim" / "Mortalidade_Geral_2019.csv", sep=";", index=False, quoting=1, encoding="latin-1")


if __name__ == "__main__":
    gerar(Path(sys.argv[1]))
