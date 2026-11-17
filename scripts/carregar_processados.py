"""Recarrega o banco a partir dos CSVs tratados (data/processed), sem baixar as fontes de novo.

Usado quando o banco é recriado pelo Terraform: o ETL completo (run_pipeline.py) baixa ~2,6 GB,
mas o resultado dele já está versionado em data/processed. A linhagem (meta_carga) é montada
com o manifesto SHA-256 dos arquivos originais e as contagens da última execução completa.

Uso:  python -m scripts.carregar_processados
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from etl import config as cfg
from etl import load
from etl.utils import sha256_arquivo

RAIZ = Path(__file__).resolve().parent.parent


def montar_cargas() -> list[dict]:
    manifesto = json.loads((cfg.DIR_RAW / "manifest.json").read_text(encoding="utf-8"))
    por_nome = {Path(m["arquivo"]).name: m for m in manifesto}
    ultima = json.loads((cfg.DIR_DOCS / "verificacao_banco.json").read_text(encoding="utf-8"))["meta_carga"]
    cols = ultima["colunas"]
    cargas = []
    for linha in ultima["linhas"]:
        r = dict(zip(cols, linha))
        if r["arquivo"] == cfg.ARQ_IBGE_PROJECAO:
            continue  # a projeção é recalculada logo abaixo
        m = por_nome[r["arquivo"]]
        origem = por_nome.get(r["arquivo_origem"]) if r["arquivo_origem"] else None
        cargas.append({
            "fonte": r["fonte"], "arquivo": r["arquivo"], "sha256": m["sha256"],
            "tamanho_bytes": m["tamanho_bytes"], "linhas_lidas": r["linhas_lidas"],
            "linhas_apos_filtro": r["linhas_apos_filtro"],
            "arquivo_origem": r["arquivo_origem"], "sha256_origem": origem["sha256"] if origem else None,
        })
    # população do IBGE (entrou na Fase 4): hash calculado na hora e registrado no manifesto
    proj = cfg.DIR_RAW / "ibge" / cfg.ARQ_IBGE_PROJECAO
    if proj.exists():
        entrada = {"fonte": "IBGE", "arquivo": f"ibge/{proj.name}", "tamanho_bytes": proj.stat().st_size,
                   "sha256": sha256_arquivo(proj),
                   "modificado_em": datetime.fromtimestamp(proj.stat().st_mtime, timezone.utc).isoformat()}
        manifesto = [m for m in manifesto if not m["arquivo"].endswith(proj.name)] + [entrada]
        (cfg.DIR_RAW / "manifest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
        pop = pd.read_csv(cfg.DIR_PROCESSED / "populacao_feminina_uf.csv")
        cargas.append({"fonte": "IBGE", "arquivo": proj.name, "sha256": entrada["sha256"],
                       "tamanho_bytes": entrada["tamanho_bytes"], "linhas_lidas": len(pd.read_excel(proj, header=5)),
                       "linhas_apos_filtro": len(pop), "arquivo_origem": None, "sha256_origem": None})
    return cargas


def main() -> None:
    load_dotenv(RAIZ / ".env")
    url = os.environ["DATABASE_URL"]
    tabelas = {}
    for nome in load.ORDEM:
        df = pd.read_csv(cfg.DIR_PROCESSED / f"{nome}.csv")
        # coluna inteira com vazio vira float no CSV (1100015.0); volta para inteiro anulável
        for c in df.select_dtypes("float").columns:
            if (df[c].dropna() % 1 == 0).all():
                df[c] = df[c].astype("Int64")
        tabelas[nome] = df
    res = load.carregar(url, tabelas, montar_cargas())
    for nome, n in res["contagem"].items():
        print(f"{nome:28s} {n:>8,}".replace(",", "."))

    if load.aplicar_permissoes_painel(url):
        print("GRANT de leitura aplicado para painel_leitura")
    else:
        print("usuário painel_leitura não existe (rode o terraform apply antes)")


if __name__ == "__main__":
    main()
