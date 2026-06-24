terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configuración del provider apuntando a LocalStack en lugar de AWS real.
# No requiere credenciales reales: usa valores dummy aceptados por LocalStack.
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    dynamodb = var.localstack_endpoint
    s3       = var.localstack_endpoint
    iam      = var.localstack_endpoint
    sts      = var.localstack_endpoint
  }
}
