"""EXTRAÇÃO — baixa (quando possível) e registra a VERSÃO ORIGINAL de cada arquivo.

O manifesto data/raw/manifest.json guarda nome, origem, tamanho, data e SHA-256
de cada arquivo bruto. Assim qualquer pessoa confere se está usando exatamente a
mesma versão que gerou a base tratada. Os arquivos brutos não são alterados.
"""
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config as cfg
from . import padronizar_sim
from .utils import sha256_arquivo

MANIFESTO = cfg.DIR_RAW / "manifest.json"


def _baixar(url: str, destino: Path) -> bool:
    if destino.exists():
        return True
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            tmp = destino.with_suffix(destino.suffix + ".part")
            with open(tmp, "wb") as f:
                for bloco in r.iter_content(1 << 20):
                    f.write(bloco)
            tmp.rename(destino)
        print(f"  baixado: {destino.name}")
        return True
    except requests.RequestException as e:
        print(f"  [aviso] não foi possível baixar {url}: {e}")
        return False


def _csv_do_sim(ano: int) -> None:
    """Garante data/raw/sim/Mortalidade_Geral_<ano>.csv a partir do arquivo oficial do ano."""
    url, oficial = cfg.SIM_FONTES[ano]
    destino = cfg.DIR_RAW / "sim" / f"Mortalidade_Geral_{ano}.csv"
    if destino.exists():
        return
    if not oficial.endswith(".zip"):
        _baixar(url, destino)
        return
    arq_zip = cfg.DIR_RAW / "sim" / oficial
    if not _baixar(url, arq_zip):
        return
    if ano in padronizar_sim.POSICOES:          # publicado sem cabeçalho
        padronizar_sim.padronizar(arq_zip, destino, ano)
    else:
        with zipfile.ZipFile(arq_zip) as z:
            membro = next(m for m in z.namelist() if m.lower().endswith(".csv"))
            with z.open(membro) as src, open(destino, "wb") as dst:
                shutil.copyfileobj(src, dst)
    print(f"  extraído: {destino.name}")


def baixar_fontes(baixar_sim: bool = True) -> None:
    """Baixa IBGE, SINESP e SIM (arquivos oficiais) para data/raw/."""
    _baixar(cfg.URL_IBGE_MUNICIPIOS, cfg.DIR_RAW / "ibge" / "municipios.json")
    for ano in range(cfg.ANO_INICIO, cfg.ANO_FIM + 1):
        _baixar(cfg.URL_SINESP.format(ano=ano), cfg.DIR_RAW / "sinesp" / f"BancoVDE {ano}.xlsx")
        if baixar_sim:
            _csv_do_sim(ano)


def arquivos(fonte: str) -> list[Path]:
    pastas = {"sinesp": ("*.xlsx", "*.csv"), "sim": ("*.csv", "*.parquet")}
    encontrados = []
    for padrao in pastas[fonte]:
        encontrados += sorted((cfg.DIR_RAW / fonte).glob(padrao))
    return encontrados


def registrar_manifesto() -> list[dict]:
    """Calcula hash de todos os arquivos brutos e grava o manifesto."""
    itens = []
    for fonte in ("sinesp", "sim", "ibge"):
        for arq in sorted((cfg.DIR_RAW / fonte).glob("*")):
            if arq.name.startswith(".") or arq.suffix == ".part":
                continue
            itens.append({
                "fonte": {"sinesp": "SINESP-VDE", "sim": "SIM", "ibge": "IBGE"}[fonte],
                "arquivo": f"{fonte}/{arq.name}",
                "tamanho_bytes": arq.stat().st_size,
                "sha256": sha256_arquivo(arq),
                "modificado_em": datetime.fromtimestamp(arq.stat().st_mtime, timezone.utc).isoformat(),
            })
    MANIFESTO.write_text(json.dumps(itens, indent=2, ensure_ascii=False), encoding="utf-8")
    return itens
