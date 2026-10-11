"""Pipeline completo: extração → tratamento → carga → relatório.

Uso:
    python run_pipeline.py                # baixa o que puder, trata e carrega no banco do .env
    python run_pipeline.py --sem-download # usa só o que já está em data/raw/
    python run_pipeline.py --sem-banco    # trata e gera data/processed + relatório, sem carregar
"""
import argparse
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from etl import config as cfg
from etl import dimensoes, extract, transform_sim, transform_sinesp


def _fmt(n) -> str:
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)


def relatorio(manifesto, log_sinesp, log_sim, extras, banco) -> str:
    L = [f"# Relatório de tratamento e carga", "",
         f"Gerado automaticamente por `run_pipeline.py` em {datetime.now():%d/%m/%Y %H:%M}.", "",
         "## 1. Versão original utilizada (data/raw/manifest.json)", "",
         "| Fonte | Arquivo | Tamanho | SHA-256 (início) |", "|---|---|---:|---|"]
    L += [f"| {m['fonte']} | `{m['arquivo']}` | {m['tamanho_bytes'] / 1e6:.1f} MB | `{m['sha256'][:16]}` |"
          for m in manifesto]
    for titulo, log in (("2. SINESP-VDE — rastro do tratamento", log_sinesp),
                        ("3. SIM/DataSUS — rastro do tratamento", log_sim)):
        L += ["", f"## {titulo}", "", "| Etapa | Linhas / valor |", "|---|---:|"]
        L += [f"| {etapa} | {_fmt(int(v))} |" for etapa, v in log]
    if extras["eventos_nao_encontrados"]:
        L += ["", "**Eventos configurados que não aparecem nos arquivos:** "
              + ", ".join(extras["eventos_nao_encontrados"])]
    mnc = extras["municipios_nao_casados"]
    if len(mnc):
        L += ["", f"**Municípios da SINESP sem correspondência no IBGE ({len(mnc)})** — "
              "acrescente em `ALIASES_MUNICIPIO` (etl/config.py) se forem grafias alternativas:", ""]
        L += [f"- {u} — {m}" for u, m in mnc.head(50).itertuples(index=False)]
    if banco:
        L += ["", "## 4. Base armazenada (schema `vde`)", "", "| Tabela | Registros | Tamanho |", "|---|---:|---:|"]
        L += [f"| {t} | {_fmt(n)} | {banco['tamanhos'].get(t, 0) / 1024:.0f} KB |" for t, n in banco["contagem"].items()]
        total = sum(banco["tamanhos"].values()) / 1e6
        L += ["", f"**Espaço total ocupado:** {total:.2f} MB de 1.024 MB do Free Tier ({100 * total / 1024:.2f}%).",
              "", "### Campos e tipos (lidos do information_schema)", "",
              "| Tabela | Campo | Tipo | Nulo? |", "|---|---|---|---|"]
        L += [f"| {t} | {c} | {d} | {n} |" for t, c, d, n in banco["colunas"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-download", action="store_true")
    ap.add_argument("--sem-banco", action="store_true")
    args = ap.parse_args()
    load_dotenv()

    print("1/4 Extração")
    if not args.sem_download:
        extract.baixar_fontes()
    manifesto = extract.registrar_manifesto()
    hash_por_arquivo = {m["arquivo"].split("/", 1)[1]: m for m in manifesto}
    arq_sinesp, arq_sim = extract.arquivos("sinesp"), extract.arquivos("sim")
    if not arq_sinesp or not arq_sim:
        raise SystemExit("Faltam arquivos em data/raw/sinesp ou data/raw/sim — veja o README.")

    print("2/4 Dimensões")
    tabelas = dimensoes.dim_estaticas()
    tabelas["dim_tempo"] = dimensoes.dim_tempo()
    tabelas["dim_municipio"] = dimensoes.dim_municipio()

    print("3/4 Tratamento")
    tabelas["fato_vitimas_sinesp"], log_sinesp, carga_sinesp, extras = transform_sinesp.transformar(
        arq_sinesp, tabelas["dim_municipio"], tabelas["dim_evento"])
    tabelas["fato_obitos_agressao_sim"], log_sim, carga_sim = transform_sim.transformar(
        arq_sim, tabelas["dim_municipio"])

    cargas = []
    for fonte, lista in (("SINESP-VDE", carga_sinesp), ("SIM", carga_sim)):
        for c in lista:
            m = hash_por_arquivo[c["arquivo"]]
            # arquivo derivado (SIM 2022/2023 padronizado): registra também o ZIP oficial
            oficial = {f"Mortalidade_Geral_{a}.csv": z for a, (_, z) in cfg.SIM_FONTES.items()}.get(c["arquivo"])
            origem = hash_por_arquivo.get(oficial) if oficial and oficial != c["arquivo"] else None
            cargas.append({**c, "fonte": fonte, "sha256": m["sha256"], "tamanho_bytes": m["tamanho_bytes"],
                           "arquivo_origem": origem["arquivo"].split("/", 1)[1] if origem else None,
                           "sha256_origem": origem["sha256"] if origem else None})
    ibge = next(m for m in manifesto if m["fonte"] == "IBGE")
    cargas.append({"fonte": "IBGE", "arquivo": ibge["arquivo"].split("/", 1)[1], "sha256": ibge["sha256"],
                   "tamanho_bytes": ibge["tamanho_bytes"], "linhas_lidas": len(tabelas["dim_municipio"]) - 27,
                   "linhas_apos_filtro": len(tabelas["dim_municipio"]) - 27})

    # versão resultante (arquivos tratados, pequenos o bastante para o repositório)
    for nome, df in tabelas.items():
        df.to_csv(cfg.DIR_PROCESSED / f"{nome}.csv", index=False)

    banco = None
    if not args.sem_banco:
        print("4/4 Carga no PostgreSQL")
        from etl import load
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise SystemExit("Defina DATABASE_URL no .env (veja .env.example).")
        banco = load.carregar(url, tabelas, cargas)
        for t, n in banco["contagem"].items():
            print(f"   {t:<28} {n:>10,}")

    destino = cfg.DIR_DOCS / "relatorio_tratamento.md"
    destino.write_text(relatorio(manifesto, log_sinesp, log_sim, extras, banco), encoding="utf-8")
    print(f"Relatório: {destino.relative_to(cfg.RAIZ)}")


if __name__ == "__main__":
    main()
