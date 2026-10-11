"""Atalho de linha de comando para etl/padronizar_sim.py (SIM 2022/2023 sem cabeçalho).

O pipeline já chama a padronização ao baixar o SIM; use isto só se os ZIPs
oficiais foram colocados à mão em data/raw/sim/.

Uso:  python -m scripts.padronizar_sim
"""
import sys

from etl import config as cfg
from etl.padronizar_sim import POSICOES, padronizar  # noqa: F401  (reexportado para os testes)


def main() -> None:
    for ano in POSICOES:
        url, oficial = cfg.SIM_FONTES[ano]
        origem = cfg.DIR_RAW / "sim" / oficial
        if not origem.exists():
            sys.exit(f"Falta {origem} — baixe de {url}")
        n = padronizar(origem, cfg.DIR_RAW / "sim" / f"Mortalidade_Geral_{ano}.csv", ano)
        print(f"  {ano}: {n:,} linhas padronizadas".replace(",", "."))


if __name__ == "__main__":
    main()
