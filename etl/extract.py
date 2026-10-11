"""EXTRAÇÃO — baixa (quando possível) e registra a VERSÃO ORIGINAL de cada arquivo.

O manifesto data/raw/manifest.json guarda nome, origem, tamanho, data e SHA-256
de cada arquivo bruto. Assim qualquer pessoa confere se está usando exatamente a
mesma versão que gerou a base tratada. Os arquivos brutos não são alterados.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config as cfg
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


def baixar_fontes(baixar_sim: bool = True) -> None:
    """Baixa IBGE e SIM. A SINESP é baixada manualmente (portal bloqueia robôs)."""
    _baixar(cfg.URL_IBGE_MUNICIPIOS, cfg.DIR_RAW / "ibge" / "municipios.json")
    if baixar_sim:
        for ano in range(cfg.ANO_INICIO, cfg.ANO_FIM + 1):
            _baixar(cfg.URL_SIM_CSV.format(ano=ano), cfg.DIR_RAW / "sim" / f"Mortalidade_Geral_{ano}.csv")


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
