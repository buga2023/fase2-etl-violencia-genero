# Teste do usuário painel_leitura

Executado em 17/11/2026 09:05, no PostgreSQL do Aiven, com a mesma credencial que o Streamlit Cloud usa.

| operação | comando | resultado |
|---|---|---|
| SELECT | `SELECT COUNT(*) FROM vde.fato_obitos_agressao_sim` | permitido (22005 linhas) |
| INSERT | `INSERT INTO vde.dim_sexo VALUES (99, 'X', 'teste')` | bloqueado: InsufficientPrivilege |
| DELETE | `DELETE FROM vde.fato_vitimas_sinesp WHERE false` | bloqueado: InsufficientPrivilege |
| UPDATE | `UPDATE vde.dim_uf SET nome = nome WHERE false` | bloqueado: InsufficientPrivilege |
| DROP | `DROP TABLE vde.meta_carga` | bloqueado: InsufficientPrivilege |
| CREATE | `CREATE TABLE vde.teste (x int)` | bloqueado: InsufficientPrivilege |
