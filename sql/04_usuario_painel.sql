-- Permissões do usuário do dashboard (criado pelo Terraform em terraform/main.tf).
-- Só leitura no schema vde: o painel consulta, nunca altera.
-- Rodar depois do terraform apply e da carga: python -m scripts.permissoes_painel
GRANT USAGE ON SCHEMA vde TO painel_leitura;
GRANT SELECT ON ALL TABLES IN SCHEMA vde TO painel_leitura;
ALTER DEFAULT PRIVILEGES IN SCHEMA vde GRANT SELECT ON TABLES TO painel_leitura;
