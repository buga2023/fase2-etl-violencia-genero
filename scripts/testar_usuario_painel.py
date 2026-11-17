"""Prova que o usuário do dashboard só lê: tenta SELECT, INSERT, DELETE e DROP e grava o resultado.

Uso: python -m scripts.testar_usuario_painel   (lê .streamlit/secrets.toml)
Saída: docs/teste_usuario_painel.md
"""
import tomllib
from datetime import datetime
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parent.parent
TESTES = [
    ("SELECT", "SELECT COUNT(*) FROM vde.fato_obitos_agressao_sim"),
    ("INSERT", "INSERT INTO vde.dim_sexo VALUES (99, 'X', 'teste')"),
    ("DELETE", "DELETE FROM vde.fato_vitimas_sinesp WHERE false"),
    ("UPDATE", "UPDATE vde.dim_uf SET nome = nome WHERE false"),
    ("DROP", "DROP TABLE vde.meta_carga"),
    ("CREATE", "CREATE TABLE vde.teste (x int)"),
]


def main() -> None:
    url = tomllib.loads((RAIZ / ".streamlit" / "secrets.toml").read_text(encoding="utf-8"))["DATABASE_URL"]
    linhas = []
    for nome, sql in TESTES:
        with psycopg.connect(url, autocommit=True) as con:
            try:
                r = con.execute(sql)
                res = f"permitido ({r.fetchone()[0]} linhas)" if nome == "SELECT" else "PERMITIDO (problema!)"
            except psycopg.Error as e:
                res = f"bloqueado: {type(e).__name__}"
        linhas.append(f"| {nome} | `{sql}` | {res} |")
    texto = (f"# Teste do usuário painel_leitura\n\nExecutado em {datetime.now():%d/%m/%Y %H:%M}, "
             "no PostgreSQL do Aiven, com a mesma credencial que o Streamlit Cloud usa.\n\n"
             "| operação | comando | resultado |\n|---|---|---|\n" + "\n".join(linhas) + "\n")
    (RAIZ / "docs" / "teste_usuario_painel.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
