"""Executa sql/03_verificacao.sql no banco do .env e grava as evidências.

Saídas: docs/verificacao_banco.md (para leitura) e docs/verificacao_banco.json
(alimenta o documento de entrega). Útil quando o psql não está instalado.
A DATABASE_URL nunca é impressa.

Uso:  python -m scripts.verificar_banco
"""
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
CHAVES = ["contagem", "tamanho", "colunas", "fks", "meta_carga", "comparativo"]
TITULOS = ["1. Registros por tabela", "2. Espaço ocupado pelo schema vde", "3. Campos e tipos",
           "4. Relacionamentos (chaves estrangeiras)", "5. Linhagem (meta_carga)",
           "6. Amostra de vw_comparativo_uf_ano"]


def _consultas() -> list[str]:
    sql = (RAIZ / "sql" / "03_verificacao.sql").read_text(encoding="utf-8")
    sem_comentario = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
    partes = [p.strip() for p in sem_comentario.split(";") if p.strip()]
    return [p for p in partes if not p.upper().startswith("SET ")]


def _valor(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat(timespec="seconds") if isinstance(v, datetime) else v.isoformat()
    return v


def _tabela(cols, linhas) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if v is None else str(v) for v in l) + " |" for l in linhas]
    return out


def main() -> None:
    load_dotenv(RAIZ / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url or "SENHA@" in url:
        raise SystemExit("Defina DATABASE_URL no .env (Service URI do Aiven).")
    host = urlparse(url).hostname or ""
    md = ["# Verificação do banco (sql/03_verificacao.sql)", "",
          f"Executado em {datetime.now():%d/%m/%Y %H:%M}.", ""]
    dados = {"executado_em": datetime.now().isoformat(timespec="seconds"),
             "aiven": host.endswith("aivencloud.com")}
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT version()")
        dados["versao"] = cur.fetchone()[0]
        md += [f"Servidor: `{dados['versao']}`", ""]
        cur.execute("SET search_path TO vde")
        for chave, titulo, sql in zip(CHAVES, TITULOS, _consultas()):
            cur.execute(sql)
            cols = [d.name for d in cur.description]
            linhas = cur.fetchall()
            dados[chave] = {"colunas": cols, "linhas": [[_valor(v) for v in l] for l in linhas]}
            md += [f"## {titulo}", ""] + _tabela(cols, linhas) + [""]
        cur.execute("""SELECT SUM(pg_total_relation_size(c.oid)) FROM pg_class c
                       JOIN pg_namespace n ON n.oid = c.relnamespace
                       WHERE n.nspname = 'vde' AND c.relkind = 'r'""")  # já inclui índices e TOAST
        dados["tamanho_bytes"] = int(cur.fetchone()[0])
    (RAIZ / "docs" / "verificacao_banco.md").write_text("\n".join(md), encoding="utf-8")
    (RAIZ / "docs" / "verificacao_banco.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Verificação gravada em docs/verificacao_banco.md e docs/verificacao_banco.json")


if __name__ == "__main__":
    main()
