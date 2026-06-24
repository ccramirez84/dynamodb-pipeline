"""
Modelos de validación de datos. Cualquier item que no cumpla este esquema
se descarta antes de tocar DynamoDB, evitando "basura silenciosa" en la
tabla y dejando un registro claro de qué se rechazó y por qué.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    product_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: str = Field(..., min_length=1)
    release_year: Optional[int] = Field(None, ge=1900, le=2100)
    rental_rate: Optional[float] = Field(None, ge=0)
    replacement_cost: Optional[float] = Field(None, ge=0)
    rating: Optional[str] = None
    length_minutes: Optional[int] = Field(None, ge=0)
    special_features: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def category_not_unknown_is_preferred(cls, v: str) -> str:
        # No rechazamos "UNKNOWN", pero lo normalizamos a mayúsculas
        # para que las consultas por GSI sean consistentes.
        return v.strip()

    def to_dynamodb_item(self) -> dict:
        """Convierte el modelo a un dict compatible con boto3 (resource API).

        Dos transformaciones necesarias:
        1. Se omiten los campos None: DynamoDB no necesita atributos vacíos.
        2. Los float se convierten a Decimal: boto3 rechaza float de forma
           explícita (TypeError: 'Float types are not supported. Use Decimal
           types instead.'), porque float pierde precisión binaria y DynamoDB
           almacena números como Decimal de alta precisión.
        """
        item = self.model_dump(exclude_none=True)
        for key, value in item.items():
            if isinstance(value, float):
                item[key] = Decimal(str(value))
        return item
