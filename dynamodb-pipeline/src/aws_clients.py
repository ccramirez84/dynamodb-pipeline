"""
Factory para clientes/recursos boto3 apuntando a LocalStack o a AWS real,
según variables de entorno. Centraliza la configuración de retries con
backoff exponencial, que boto3 soporta nativamente desde botocore>=1.26.
"""
from __future__ import annotations

import os
import boto3
from botocore.config import Config

# IMPORTANTE: estas variables se leen DENTRO de cada función (no como
# constantes de módulo) para que los tests puedan cambiar las variables
# de entorno (vía monkeypatch) y que el efecto se refleje en cada llamada,
# en vez de quedar "congelado" con el valor que existía al importar el módulo.


def _retry_config() -> Config:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    # 'adaptive' ajusta dinámicamente la tasa de reintentos en función del
    # throttling observado, en vez de un backoff fijo. Es lo recomendado por
    # AWS para cargas batch contra DynamoDB en modo PAY_PER_REQUEST, donde
    # picos de escritura pueden generar ProvisionedThroughputExceededException.
    return Config(region_name=region, retries={"max_attempts": 8, "mode": "adaptive"})


def _use_localstack() -> bool:
    return os.environ.get("USE_LOCALSTACK", "true").lower() == "true"


def get_dynamodb_resource():
    kwargs = {"config": _retry_config()}
    if _use_localstack():
        kwargs.update(
            endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    return boto3.resource("dynamodb", **kwargs)


def get_s3_client():
    kwargs = {"config": _retry_config()}
    if _use_localstack():
        kwargs.update(
            endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    return boto3.client("s3", **kwargs)
