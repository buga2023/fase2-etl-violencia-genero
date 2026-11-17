output "pg_host" {
  description = "Host do PostgreSQL."
  value       = aiven_pg.banco.service_host
}

output "pg_port" {
  description = "Porta do PostgreSQL."
  value       = aiven_pg.banco.service_port
}

output "pg_service_uri" {
  description = "URI do avnadmin, usada pelo ETL (vai para o .env). terraform output -raw pg_service_uri"
  value       = aiven_pg.banco.service_uri
  sensitive   = true
}

output "painel_usuario" {
  description = "Usuário do dashboard."
  value       = aiven_pg_user.painel.username
}

output "painel_senha" {
  description = "Senha do usuário do dashboard (vai para o Secrets do Streamlit Cloud)."
  value       = aiven_pg_user.painel.password
  sensitive   = true
}
