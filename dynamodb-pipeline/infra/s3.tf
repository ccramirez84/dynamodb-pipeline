# Bucket de "raw landing zone": aquí llegan los archivos JSON/CSV originales
# antes de ser procesados. Separar raw de processed es una práctica estándar
# en arquitecturas de data lake (permite reprocesar desde el origen si el
# pipeline de transformación cambia o falla).

resource "aws_s3_bucket" "raw_landing_zone" {
  bucket = "${var.project_name}-${var.environment}-raw-landing-zone"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    DataLayer   = "raw"
  }
}

resource "aws_s3_bucket_versioning" "raw_landing_zone_versioning" {
  bucket = aws_s3_bucket.raw_landing_zone.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_landing_zone_lifecycle" {
  bucket = aws_s3_bucket.raw_landing_zone.id

  rule {
    id     = "expire-old-raw-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
