variable "aiven_api_token" {
  description = "Token de API do Aiven (Console > User > Tokens). Passar por TF_VAR_aiven_api_token."
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Nome do projeto no Aiven (aparece no host do serviço, depois do nome do serviço)."
  type        = string
}

variable "pg_service_name" {
  description = "Nome do serviço PostgreSQL."
  type        = string
}

variable "pg_plan" {
  description = "Plano do serviço. free-1-1gb = Free Tier com 1 GB de disco."
  type        = string
  default     = "free-1-1gb"
}

variable "cloud_name" {
  description = "Nuvem e região (o plano free só existe em algumas, ex.: do-nyc, aws-us-east-1)."
  type        = string
  default     = "do-nyc"
}

variable "pg_version" {
  description = "Versão major do PostgreSQL."
  type        = string
  default     = "18"
}

variable "usuario_painel" {
  description = "Usuário somente leitura usado pelo dashboard Streamlit."
  type        = string
  default     = "painel_leitura"
}
