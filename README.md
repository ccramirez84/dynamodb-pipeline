# Pipeline de Ingesta Batch a DynamoDB con Terraform

Pipeline de ingesta de datos que valida, transforma y carga registros en
DynamoDB de forma idempotente, con la infraestructura completamente
definida como código (Terraform) y probada en LocalStack.

Los datos de ejemplo son reales: 1000 películas extraídas del dataset
público **Sakila** (jOOQ/sakila), tratadas como catálogo de productos.

## Por qué este proyecto

La mayoría de ejemplos de "boto3 + DynamoDB" en internet hacen `put_item`
en un loop sin manejar fallos parciales, duplicados o reintentos. Este
proyecto resuelve esos problemas explícitamente:

- **Idempotencia real**: si el pipeline se cae a mitad de carga y se
  vuelve a correr, no duplica datos. Una tabla de control (`ingestion_log`)
  registra qué archivos ya se procesaron con éxito.
- **Batch writes, no loops**: usa `batch_writer()` de boto3, que agrupa
  automáticamente en lotes de 25 (límite real de DynamoDB) y reintenta los
  `UnprocessedItems` sin intervención manual.
- **Validación de esquema antes de escribir**: con Pydantic. Los registros
  inválidos se reportan, no se descartan en silencio ni rompen todo el job.
- **Retries con backoff adaptativo**: configurado en botocore (`mode=adaptive`)
  para absorber throttling de DynamoDB sin fallar la ingesta completa.
- **Infraestructura versionada**: tablas, índices, bucket S3 y rol IAM con
  permisos mínimos, todo en Terraform — nada creado a mano en la consola.

## Arquitectura

```
data/raw/*.sql (Sakila)
        │
        ▼
scripts_setup/extract_sakila_to_json.py   (extrae catálogo real a JSON)
        │
        ▼
data/processed/product_catalog.json
        │
        ▼
src/main.py  ──►  src/ingest.py
                     │
                     ├─► valida cada registro (src/models.py / Pydantic)
                     │
                     ├─► consulta tabla de control (¿ya se ingirió este archivo?)
                     │
                     ├─► batch_writer() ──► DynamoDB: tabla product-catalog
                     │
                     └─► registra el resultado ──► DynamoDB: tabla ingestion-log
```

Infraestructura (`infra/*.tf`):

| Recurso | Propósito |
|---|---|
| `aws_dynamodb_table.product_catalog` | Tabla principal. PK `product_id`, GSI por `category` + `release_year` para evitar Scans costosos. |
| `aws_dynamodb_table.ingestion_log` | Control de idempotencia: qué archivo se procesó, cuándo, con qué resultado. |
| `aws_s3_bucket.raw_landing_zone` | Zona de aterrizaje para los archivos crudos (con versionado y lifecycle). |
| `aws_iam_role` / `aws_iam_role_policy` | Permisos mínimos (least privilege): solo las acciones de DynamoDB/S3 necesarias. |

## Requisitos

- Python 3.11+
- Docker (para LocalStack)
- Terraform >= 1.5
- [LocalStack CLI](https://docs.localstack.cloud/getting-started/installation/) o Docker directo

## Cómo correrlo

```bash
# 1. Instalar dependencias
make install

# 2. Levantar LocalStack
make localstack-up

# 3. Crear infraestructura (DynamoDB, S3, IAM) en LocalStack
make tf-init
make tf-apply

# 4. (Opcional) Regenerar el JSON de productos desde el SQL crudo de Sakila
make extract-data

# 5. Correr el pipeline de ingesta
make ingest

# 6. Verificar en LocalStack
aws --endpoint-url=http://localhost:4566 dynamodb scan \
    --table-name data-pipeline-dev-product-catalog --max-items 3
```

## Tests

Los tests **no requieren LocalStack ni Docker**: usan
[`moto`](https://github.com/getmoto/moto) para mockear DynamoDB en memoria,
por lo que corren en milisegundos y son los que efectivamente se ejecutan en
CI (`.github/workflows/ci.yml`).

```bash
make test          # 17 tests
make test-cov       # con reporte de cobertura (96% sobre src/)
```

Casos cubiertos: validación de esquema, conversión de tipos (float→Decimal,
un error común al trabajar con DynamoDB), idempotencia en reintentos,
`--force` para reprocesar, y el CLI completo.

## Decisiones de diseño que vale la pena explicar en una entrevista

1. **¿Por qué PAY_PER_REQUEST y no PROVISIONED?** Para un pipeline batch con
   tráfico intermitente, evita pagar capacidad aprovisionada ociosa. Con
   tráfico alto y predecible, `PROVISIONED + autoscaling` sería más barato;
   por eso queda como variable de Terraform (`dynamodb_billing_mode`), no
   hardcodeado.
2. **¿Por qué un GSI por `category` + `release_year`?** Sin él, "listar
   productos de una categoría" requeriría un `Scan` completo de la tabla
   (lento y caro a escala). El GSI lo convierte en una `Query` directa.
3. **¿Por qué Decimal y no float?** boto3 rechaza `float` explícitamente al
   escribir en DynamoDB porque pierde precisión binaria; DynamoDB almacena
   números como `Decimal`. Es un error que aparece la primera vez que se
   prueba con datos reales (precios, en este caso) y no con literales `int`.

## Estructura del repo

```
.
├── infra/                  # Terraform: DynamoDB, S3, IAM
├── src/
│   ├── models.py            # Esquema Pydantic + conversión a formato DynamoDB
│   ├── aws_clients.py        # Factory de clientes boto3 (LocalStack o AWS real)
│   ├── ingest.py              # Lógica de ingesta: validación, idempotencia, batch write
│   └── main.py                  # CLI
├── tests/                   # Tests con moto (sin dependencias externas)
├── scripts_setup/
│   └── extract_sakila_to_json.py  # Extrae datos reales de Sakila a JSON
└── data/
    ├── raw/                  # SQL crudo de Sakila (no versionado, ver .gitignore)
    └── processed/             # JSON/CSV generado, listo para ingestar
```

## Fuente de datos

[Sakila Sample Database](https://github.com/jOOQ/sakila) — base de datos de
ejemplo de MySQL AB, licencia BSD. Se usa la tabla `film` (tratada como
catálogo de productos) cruzada con `category` para obtener 1000 registros
reales con relaciones consistentes.
