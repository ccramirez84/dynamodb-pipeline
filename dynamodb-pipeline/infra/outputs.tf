output "product_catalog_table_name" {
  description = "Nombre de la tabla DynamoDB del catálogo de productos"
  value       = aws_dynamodb_table.product_catalog.name
}

output "ingestion_log_table_name" {
  description = "Nombre de la tabla DynamoDB de control de ingestas"
  value       = aws_dynamodb_table.ingestion_log.name
}

output "raw_landing_zone_bucket" {
  description = "Nombre del bucket S3 de aterrizaje de datos crudos"
  value       = aws_s3_bucket.raw_landing_zone.bucket
}

output "ingestion_pipeline_role_arn" {
  description = "ARN del rol IAM usado por el pipeline de ingesta"
  value       = aws_iam_role.ingestion_pipeline_role.arn
}
