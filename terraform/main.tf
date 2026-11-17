terraform {
  required_version = ">= 1.5"

  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "~> 4.0"
    }
  }
}

# O token vem da variável de ambiente TF_VAR_aiven_api_token (ou AIVEN_TOKEN).
# Nunca escrever o token neste arquivo nem no terraform.tfvars commitado.
provider "aiven" {
  api_token = var.aiven_api_token
}

# Projeto já existe na conta (criado junto com a conta Aiven).
data "aiven_project" "projeto" {
  project = var.aiven_project
}

# Banco do projeto: PostgreSQL no plano gratuito (free-1-1gb, 1 GB de disco, custo zero).
# Na Fase 2 o banco tinha sido criado pelo console durante o trial (plano developer-1).
# Quando o trial acabou ele foi desligado, então recriamos tudo aqui pelo Terraform.
resource "aiven_pg" "banco" {
  project      = data.aiven_project.projeto.project
  service_name = var.pg_service_name
  plan         = var.pg_plan
  cloud_name   = var.cloud_name

  termination_protection = false # plano free não aceita proteção contra exclusão

  pg_user_config {
    pg_version = var.pg_version
  }

  tag {
    key   = "projeto"
    value = "feminicidio-interseccional"
  }
}

# Usuário só de leitura para o dashboard (o painel não usa o avnadmin).
# As permissões (GRANT SELECT no schema vde) ficam em sql/04_usuario_painel.sql.
resource "aiven_pg_user" "painel" {
  project      = aiven_pg.banco.project
  service_name = aiven_pg.banco.service_name
  username     = var.usuario_painel
}
