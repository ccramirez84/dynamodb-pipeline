# Tabla principal: catálogo de productos (películas de Sakila).
#
# Diseño de claves:
#   - PK (HASH):  product_id   -> acceso directo O(1) por producto
#   - GSI:        category     -> permite "listar productos por categoría"
#                                  sin hacer Scan (que es costoso y lento)
#
# Justificación de PAY_PER_REQUEST: para un pipeline batch con tráfico
# desconocido/intermitente, evita pagar capacidad aprovisionada ociosa.
# En un escenario de tráfico predecible y alto volumen, PROVISIONED + autoscaling
# sería más económico; se deja como variable para que sea decisión explícita.

resource "aws_dynamodb_table" "product_catalog" {
  name         = "${var.project_name}-${var.environment}-product-catalog"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "product_id"

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  attribute {
    name = "release_year"
    type = "N"
  }

  global_secondary_index {
    name            = "category-release_year-index"
    hash_key        = "category"
    range_key       = "release_year"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "portfolio-demo"
  }
}

# Tabla de control de ingestas: permite idempotencia y trazabilidad.
# Cada ejecución del pipeline registra qué archivo procesó y cuántos
# items insertó/fallaron, evitando reprocesar el mismo archivo dos veces.
resource "aws_dynamodb_table" "ingestion_log" {
  name         = "${var.project_name}-${var.environment}-ingestion-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_file"
  range_key    = "run_timestamp"

  attribute {
    name = "source_file"
    type = "S"
  }

  attribute {
    name = "run_timestamp"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "idempotency-control"
  }
}
