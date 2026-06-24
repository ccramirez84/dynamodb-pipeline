"""
Punto de entrada CLI del pipeline.

Uso:
    python -m src.main --file data/processed/product_catalog.json \
        --catalog-table data-pipeline-dev-product-catalog \
        --log-table data-pipeline-dev-ingestion-log

Los nombres de tabla por defecto coinciden con los outputs de Terraform
(infra/outputs.tf) cuando se usa project_name=data-pipeline y environment=dev.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.ingest import ingest_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline de ingesta batch a DynamoDB")
    parser.add_argument("--file", type=Path, required=True, help="Ruta al JSON de productos")
    parser.add_argument(
        "--catalog-table",
        default="data-pipeline-dev-product-catalog",
        help="Nombre de la tabla DynamoDB del catálogo",
    )
    parser.add_argument(
        "--log-table",
        default="data-pipeline-dev-ingestion-log",
        help="Nombre de la tabla DynamoDB de control de ingestas",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocesa el archivo aunque ya haya sido ingerido exitosamente",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.file.exists():
        print(f"Error: el archivo {args.file} no existe", file=sys.stderr)
        return 1

    result = ingest_file(
        file_path=args.file,
        catalog_table_name=args.catalog_table,
        log_table_name=args.log_table,
        force=args.force,
    )

    if result.skipped_already_ingested:
        print(f"Omitido: {args.file} ya fue ingerido exitosamente. Usa --force para reprocesar.")
        return 0

    print(f"Total registros:        {result.total_records}")
    print(f"Insertados:              {result.inserted}")
    print(f"Errores de validación:   {result.validation_errors}")

    if result.errors:
        print("\nPrimeros errores:")
        for err in result.errors[:5]:
            print(f"  - {err}")

    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
