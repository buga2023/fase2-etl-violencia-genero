-- Permissões do usuário do dashboard (criado pelo Terraform em terraform/main.tf).
-- Só leitura no schema vde: o painel consulta, nunca altera.
-- Aplicado automaticamente no fim do run_pipeline.py e do scripts/carregar_processados.py.
GRANT USAGE ON SCHEMA vde TO painel_leitura;
GRANT SELECT ON ALL TABLES IN SCHEMA vde TO painel_leitura;
ALTER DEFAULT PRIVILEGES IN SCHEMA vde GRANT SELECT ON TABLES TO painel_leitura;
