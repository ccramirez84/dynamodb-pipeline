"""
Fixtures compartidos. Usamos moto para mockear DynamoDB en memoria: los
tests corren en milisegundos, no requieren Docker/LocalStack, y son
deterministas. Esto es lo que correría en un pipeline de CI (GitHub Actions)
sin necesidad de levantar infraestructura real.
"""
import os
import json
import pytest
import boto3
from moto import mock_aws

CATALOG_TABLE_NAME = "test-product-catalog"
LOG_TABLE_NAME = "test-ingestion-log"


@pytest.fixture(autouse=True)
def _force_test_region(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("USE_LOCALSTACK", "false")


@pytest.fixture
def dynamodb_tables():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        dynamodb.create_table(
            TableName=CATALOG_TABLE_NAME,
            KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "product_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        dynamodb.create_table(
            TableName=LOG_TABLE_NAME,
            KeySchema=[
                {"AttributeName": "source_file", "KeyType": "HASH"},
                {"AttributeName": "run_timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "source_file", "AttributeType": "S"},
                {"AttributeName": "run_timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield {
            "catalog_table_name": CATALOG_TABLE_NAME,
            "log_table_name": LOG_TABLE_NAME,
            "resource": dynamodb,
        }


@pytest.fixture
def sample_products_file(tmp_path):
    data = [
        {
            "product_id": "1",
            "title": "ACADEMY DINOSAUR",
            "description": "A Epic Drama of a Feminist And a Mad Scientist",
            "category": "Documentary",
            "release_year": 2006,
            "rental_rate": 0.99,
            "replacement_cost": 20.99,
            "rating": "PG",
            "length_minutes": 86,
            "special_features": ["Deleted Scenes", "Behind the Scenes"],
        },
        {
            "product_id": "2",
            "title": "ACE GOLDFINGER",
            "description": "A Astounding Epistle of a Database Administrator",
            "category": "Action",
            "release_year": 2006,
            "rental_rate": 4.99,
            "replacement_cost": 12.99,
            "rating": "G",
            "length_minutes": 48,
            "special_features": ["Trailers"],
        },
        {
            # Item inválido a propósito: release_year fuera de rango razonable
            "product_id": "3",
            "title": "BAD ITEM",
            "category": "Horror",
            "release_year": 1500,
        },
    ]
    file_path = tmp_path / "sample_products.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path
