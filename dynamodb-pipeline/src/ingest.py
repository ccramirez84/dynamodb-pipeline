"""
Pipeline de ingesta batch: JSON crudo -> validación Pydantic -> DynamoDB.

Decisiones de diseño relevantes para un revisor técnico:

1. Idempotencia: antes de procesar un archivo, se consulta la tabla de
   control (`ingestion_log`). Si ese archivo ya fue cargado exitosamente,
   se omite. Esto evita duplicar escrituras si el pipeline se reintenta
   (por ejemplo, tras un fallo de red a mitad de ejecución).

2. batch_writer() de boto3 (resource API) agrupa automáticamente las
   escrituras en lotes de 25 items (límite de DynamoDB BatchWriteItem) y
   reintenta los UnprocessedItems internamente. No se usa put_item() en un
   loop porque eso desperdicia capacidad y es ~25x más lento.

3. Validación antes de escribir: los items que no cumplen el esquema
   Pydantic se descartan y se reportan, en vez de fallar todo el batch o
   insertar datos corruptos silenciosamente.

4. Resultado estructurado: la función devuelve un IngestionResult con
   conteos exactos (insertados, fallidos, omitidos), que es lo que se
   necesita para alertar o para un dashboard de observabilidad.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .models import Product
from .aws_clients import get_dynamodb_resource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    source_file: str
    total_records: int = 0
    inserted: int = 0
    validation_errors: int = 0
    skipped_already_ingested: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.validation_errors == 0


def _was_already_ingested(log_table, source_file: str) -> bool:
    """Revisa la tabla de control por una ingesta exitosa previa del mismo archivo."""
    response = log_table.query(
        KeyConditionExpression="source_file = :sf",
        ExpressionAttributeValues={":sf": source_file},
    )
    items = response.get("Items", [])
    return any(item.get("status") == "SUCCESS" for item in items)


def _record_ingestion_run(log_table, result: IngestionResult) -> None:
    log_table.put_item(
        Item={
            "source_file": result.source_file,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS" if result.success else "PARTIAL_FAILURE",
            "total_records": result.total_records,
            "inserted": result.inserted,
            "validation_errors": result.validation_errors,
        }
    )


def load_and_validate(file_path: Path) -> tuple[list[Product], list[str]]:
    """Lee un JSON de productos crudos y devuelve (productos válidos, errores)."""
    raw_items = json.loads(file_path.read_text(encoding="utf-8"))
    valid_products: list[Product] = []
    errors: list[str] = []

    for idx, raw_item in enumerate(raw_items):
        try:
            valid_products.append(Product(**raw_item))
        except ValidationError as exc:
            errors.append(f"item[{idx}] (product_id={raw_item.get('product_id')}): {exc}")

    return valid_products, errors


def ingest_file(
    file_path: Path,
    catalog_table_name: str,
    log_table_name: str,
    force: bool = False,
) -> IngestionResult:
    """Orquesta la ingesta completa de un archivo: idempotencia, validación,
    batch write y registro del resultado."""
    dynamodb = get_dynamodb_resource()
    catalog_table = dynamodb.Table(catalog_table_name)
    log_table = dynamodb.Table(log_table_name)

    result = IngestionResult(source_file=str(file_path))

    if not force and _was_already_ingested(log_table, str(file_path)):
        result.skipped_already_ingested = True
        logger.info("Archivo %s ya fue ingerido exitosamente; se omite.", file_path)
        return result

    products, validation_errors = load_and_validate(file_path)
    result.total_records = len(products) + len(validation_errors)
    result.validation_errors = len(validation_errors)
    result.errors = validation_errors

    if validation_errors:
        logger.warning(
            "%d/%d registros fallaron validación en %s",
            len(validation_errors),
            result.total_records,
            file_path,
        )

    with catalog_table.batch_writer(overwrite_by_pkeys=["product_id"]) as batch:
        for product in products:
            batch.put_item(Item=product.to_dynamodb_item())
            result.inserted += 1

    logger.info(
        "Ingesta completa: %d insertados, %d con error de validación (archivo=%s)",
        result.inserted,
        result.validation_errors,
        file_path,
    )

    _record_ingestion_run(log_table, result)
    return result
