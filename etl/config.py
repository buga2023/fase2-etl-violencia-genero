"""Parâmetros do pipeline. Toda decisão de recorte está aqui, num lugar só."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_PROCESSED = RAIZ / "data" / "processed"
DIR_DOCS = RAIZ / "docs"
DIR_SQL = RAIZ / "sql"

# ---------------------------------------------------------------- recorte
ANO_INICIO, ANO_FIM = 2019, 2024          # Fase 1: recorte temporal
CHUNK_SIZE = 200_000                       # leitura do SIM em blocos

# ---------------------------------------------------------------- fontes
URL_IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
# OpenDataSUS — Declarações de Óbito (CSV nacional por ano, separador ';'). ano: (URL, arquivo oficial)
# Recursos listados em https://dadosabertos.saude.gov.br/dataset/sim (links conferidos em out/2026).
# ZIPs de 2022 e 2023 vêm sem cabeçalho: etl/padronizar_sim.py gera o CSV que o ETL lê.
_S3_SIM = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/csv/"
SIM_FONTES = {
    2019: ("https://diaad.s3.sa-east-1.amazonaws.com/sim/Mortalidade_Geral_2019.csv", "Mortalidade_Geral_2019.csv"),
    2020: ("https://diaad.s3.sa-east-1.amazonaws.com/sim/Mortalidade_Geral_2020.csv", "Mortalidade_Geral_2020.csv"),
    2021: (_S3_SIM + "Mortalidade_Geral_2021_csv.zip", "Mortalidade_Geral_2021_csv.zip"),
    2022: (_S3_SIM + "Mortalidade_Geral_2022_csv.zip", "Mortalidade_Geral_2022_csv.zip"),
    2023: (_S3_SIM + "Mortalidade_Geral_2023_csv.zip", "Mortalidade_Geral_2023_csv.zip"),
    2024: (_S3_SIM + "DO24OPEN_csv.zip", "DO24OPEN_csv.zip"),   # preliminar
}
# SINESP-VDE: "BancoVDE <ano>.xlsx" no gov.br/mj (o antigo dados.mj.gov.br saiu do ar).
URL_SINESP = ("https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/"
              "download/dnsp-base-de-dados/bancovde-{ano}.xlsx/@@download/file")

# ---------------------------------------------------------------- SINESP
# Eventos mantidos (comparação sem acento/caixa). grupo, violencia_genero
EVENTOS = {
    "Feminicídio":                          ("Letal", True),
    "Homicídio doloso":                     ("Letal", False),
    "Lesão corporal seguida de morte":      ("Letal", False),
    "Roubo seguido de morte (latrocínio)":  ("Letal", False),
    "Tentativa de feminicídio":             ("Tentativa", True),
    "Tentativa de homicídio":               ("Tentativa", False),
    "Estupro":                              ("Sexual", False),
    "Estupro de vulnerável":                ("Sexual", False),
}
COLUNAS_SINESP_OBRIGATORIAS = ["uf", "municipio", "evento", "feminino", "masculino",
                               "nao_informado", "total_vitima"]

# Grafias da SINESP que não batem com o IBGE → nome IBGE (normalizado)
ALIASES_MUNICIPIO = {
    ("SP", "EMBU"): "EMBU DAS ARTES",
    ("PA", "SANTA ISABEL DO PARA"): "SANTA IZABEL DO PARA",
    ("RN", "AUGUSTO SEVERO"): "CAMPO GRANDE",
    ("PB", "SANTAREM"): "JOCA CLAUDINO",
    ("TO", "SAO VALERIO DA NATIVIDADE"): "SAO VALERIO",
    ("MG", "BARAO DE MONTE ALTO"): "BARAO DO MONTE ALTO",
    ("MT", "SANTO ANTONIO DO LEVERGER"): "SANTO ANTONIO DE LEVERGER",
    ("RN", "ARES"): "AREZ",
    ("RN", "ACU"): "ASSU",
    ("RR", "SAO LUIZ"): "SAO LUIZ DO ANAUA",
    ("SE", "GRACHO CARDOSO"): "GRACCHO CARDOSO",
}  # o relatório lista os nomes não casados — acrescente aqui e rode de novo
MUNICIPIO_NAO_INFORMADO = "NÃO INFORMADO"
VALORES_SEM_MUNICIPIO = {"", "NAO INFORMADO", "NAO INFORMADA", "NI", "SEM INFORMACAO", "IGNORADO"}

# ---------------------------------------------------------------- SIM
COLUNAS_SIM = ["DTOBITO", "SEXO", "RACACOR", "IDADE", "CAUSABAS", "CODMUNOCOR"]
CID_INICIO, CID_FIM = "X85", "Y09"         # agressões (homicídios) na CID-10
SEXO_FEMININO_SIM = {"2", "F"}             # 2 a partir de ~2008; F em arquivos antigos

# ---------------------------------------------------------------- dimensões estáticas
UFS = [  # cod IBGE, sigla, nome, região
    (11, "RO", "Rondônia", "Norte"), (12, "AC", "Acre", "Norte"), (13, "AM", "Amazonas", "Norte"),
    (14, "RR", "Roraima", "Norte"), (15, "PA", "Pará", "Norte"), (16, "AP", "Amapá", "Norte"),
    (17, "TO", "Tocantins", "Norte"), (21, "MA", "Maranhão", "Nordeste"), (22, "PI", "Piauí", "Nordeste"),
    (23, "CE", "Ceará", "Nordeste"), (24, "RN", "Rio Grande do Norte", "Nordeste"),
    (25, "PB", "Paraíba", "Nordeste"), (26, "PE", "Pernambuco", "Nordeste"), (27, "AL", "Alagoas", "Nordeste"),
    (28, "SE", "Sergipe", "Nordeste"), (29, "BA", "Bahia", "Nordeste"), (31, "MG", "Minas Gerais", "Sudeste"),
    (32, "ES", "Espírito Santo", "Sudeste"), (33, "RJ", "Rio de Janeiro", "Sudeste"),
    (35, "SP", "São Paulo", "Sudeste"), (41, "PR", "Paraná", "Sul"), (42, "SC", "Santa Catarina", "Sul"),
    (43, "RS", "Rio Grande do Sul", "Sul"), (50, "MS", "Mato Grosso do Sul", "Centro-Oeste"),
    (51, "MT", "Mato Grosso", "Centro-Oeste"), (52, "GO", "Goiás", "Centro-Oeste"),
    (53, "DF", "Distrito Federal", "Centro-Oeste"),
]
SIGLA_PARA_COD = {s: c for c, s, _, _ in UFS}

SEXOS = [(1, "F", "Feminino"), (2, "M", "Masculino"), (3, "I", "Não informado")]

RACAS = [  # id = código do SIM
    (1, "Branca", False), (2, "Preta", True), (3, "Amarela", False),
    (4, "Parda", True), (5, "Indígena", False), (9, "Ignorada", False),
]

FAIXAS = [  # id, descrição, min, max
    (1, "0-11", 0, 11), (2, "12-17", 12, 17), (3, "18-24", 18, 24), (4, "25-29", 25, 29),
    (5, "30-39", 30, 39), (6, "40-49", 40, 49), (7, "50-59", 50, 59), (8, "60+", 60, 150),
    (9, "Ignorada", None, None),
]

MEIOS = [  # id, descrição, faixa de CID (3 caracteres)
    (1, "Arma de fogo", "X93-X95"),
    (2, "Objeto cortante/penetrante", "X99"),
    (3, "Objeto contundente", "Y00"),
    (4, "Enforcamento/estrangulamento", "X91"),
    (5, "Força corporal/agressão sexual", "Y04-Y05"),
    (6, "Outros meios / não especificado", "demais X85-Y09"),
]
