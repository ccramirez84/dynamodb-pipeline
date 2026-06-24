variable "aws_region" {
  description = "Región AWS simulada por LocalStack"
  type        = string
  default     = "us-east-1"
}

variable "localstack_endpoint" {
  description = "Endpoint local donde corre LocalStack"
  type        = string
  default     = "http://localhost:4566"
}

variable "environment" {
  description = "Nombre del entorno (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nombre del proyecto, usado como prefijo de recursos"
  type        = string
  default     = "data-pipeline"
}

variable "dynamodb_billing_mode" {
  description = "Modo de facturación de DynamoDB: PAY_PER_REQUEST o PROVISIONED"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "dynamodb_billing_mode debe ser PAY_PER_REQUEST o PROVISIONED."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Habilita PITR en la tabla DynamoDB (recomendado en producción)"
  type        = bool
  default     = true
}
