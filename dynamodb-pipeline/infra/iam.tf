# Rol que asumiría una función Lambda o un job de ingesta en un escenario real.
# Se incluye aunque LocalStack no aplique IAM de forma estricta, porque
# en un proyecto real esto es lo que un reviewer/entrevistador espera ver:
# permisos explícitos y acotados, no "*:*".

resource "aws_iam_role" "ingestion_pipeline_role" {
  name = "${var.project_name}-${var.environment}-ingestion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

resource "aws_iam_role_policy" "ingestion_pipeline_policy" {
  name = "${var.project_name}-${var.environment}-ingestion-policy"
  role = aws_iam_role.ingestion_pipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBWriteAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.product_catalog.arn,
          "${aws_dynamodb_table.product_catalog.arn}/index/*",
          aws_dynamodb_table.ingestion_log.arn
        ]
      },
      {
        Sid    = "S3ReadRawZone"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_landing_zone.arn,
          "${aws_s3_bucket.raw_landing_zone.arn}/*"
        ]
      }
    ]
  })
}
