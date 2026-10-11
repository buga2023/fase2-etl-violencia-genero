"""Funções de apoio: normalização de texto, hash de arquivos e números em formato BR."""
import hashlib
import re
import unicodedata
from pathlib import Path

import pandas as pd


def normalizar_texto(valor) -> str:
    """'São Gonçalo d'Oeste ' -> 'SAO GONCALO D OESTE' (chave de comparação)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    s = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    s = re.sub(r"[`'´’]", "", s.upper())          # Sant'Ana -> SANTANA
    s = re.sub(r"[^A-Z0-9 ]", " ", s)             # hífen, ponto, parênteses -> espaço
    return re.sub(r"\s+", " ", s).strip()


def chave_nome(valor) -> str:
    """Chave de junção por nome: normalizado e sem espaços ('D OESTE' = 'DOESTE')."""
    return normalizar_texto(valor).replace(" ", "")


def normalizar_coluna(nome: str) -> str:
    """'Total Vítima' -> 'total_vitima'."""
    return re.sub(r"\W+", "_", normalizar_texto(nome).lower()).strip("_")


def inteiro_br(serie: pd.Series) -> pd.Series:
    """Converte contagens que chegam como texto ('1.234', '12,0', '', None) em inteiro.

    Regra: número já numérico passa direto; texto perde separador de milhar '.',
    vírgula decimal vira ponto; vazio/inválido vira 0 (ausência de registro).
    """
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0).round().astype("int64")
    s = (serie.astype("string").str.strip()
         .str.replace(r"\.(?=\d{3}(\D|$))", "", regex=True)
         .str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce").fillna(0).round().astype("int64")


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()
