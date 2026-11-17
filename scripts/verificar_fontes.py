"""Confere se as fontes oficiais mudaram desde a última carga (V de Velocidade).

As fontes são publicadas em lote, uma vez por ano. Em vez de baixar 2,6 GB todo mês,
este script faz só um HEAD em cada URL e compara o tamanho com o manifesto. Se algo
mudou (ou um ano novo apareceu), avisa que está na hora de rodar o run_pipeline.py.

Uso: python -m scripts.verificar_fontes   (roda também no GitHub Actions, todo dia 1º)
"""
import json
import sys
from pathlib import Path

import requests

from etl import config as cfg

MANIFESTO = json.loads((cfg.DIR_RAW / "manifest.json").read_text(encoding="utf-8"))
TAMANHO = {Path(m["arquivo"]).name: m["tamanho_bytes"] for m in MANIFESTO}


def head(url: str) -> tuple[int | None, int | None]:
    cab = {"User-Agent": "Mozilla/5.0 (projeto academico; verificacao de fontes)"}
    try:
        r = requests.head(url, allow_redirects=True, timeout=30, headers=cab)
        if r.status_code in (403, 405):  # o gov.br recusa HEAD; GET em stream só lê o cabeçalho
            r = requests.get(url, stream=True, timeout=30, headers=cab)
            r.close()
        return r.status_code, int(r.headers["Content-Length"]) if "Content-Length" in r.headers else None
    except requests.RequestException:
        return None, None


def main() -> int:
    linhas, mudou = [], False
    alvos = [(f"BancoVDE {a}.xlsx", cfg.URL_SINESP.format(ano=a)) for a in range(cfg.ANO_INICIO, cfg.ANO_FIM + 2)]
    alvos += [(arq, url) for _, (url, arq) in cfg.SIM_FONTES.items()]
    alvos += [(cfg.ARQ_IBGE_PROJECAO, cfg.URL_IBGE_PROJECAO)]
    for nome, url in alvos:
        status, tam = head(url)
        antes = TAMANHO.get(nome)
        if status != 200:
            situacao = "ainda não publicado" if antes is None else f"indisponível (HTTP {status})"
        elif antes is None:
            situacao, mudou = "NOVO arquivo publicado", True
        elif tam is not None and tam != antes:
            situacao, mudou = f"MUDOU ({antes} -> {tam} bytes)", True
        else:
            situacao = "igual ao carregado"
        linhas.append(f"| {nome} | {situacao} |")
    print("| arquivo | situação |\n|---|---|\n" + "\n".join(linhas))
    print("\nResultado:", "tem dado novo, rodar python run_pipeline.py" if mudou else "nada novo nas fontes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
