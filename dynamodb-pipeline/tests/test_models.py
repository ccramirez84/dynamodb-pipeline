import pytest
from pydantic import ValidationError

from src.models import Product


def test_product_valido_se_construye_correctamente():
    product = Product(
        product_id="1",
        title="ACADEMY DINOSAUR",
        category="Documentary",
        release_year=2006,
        rental_rate=0.99,
    )
    assert product.product_id == "1"
    assert product.category == "Documentary"


def test_product_sin_title_falla():
    with pytest.raises(ValidationError):
        Product(product_id="1", category="Documentary")


def test_product_con_release_year_fuera_de_rango_falla():
    with pytest.raises(ValidationError):
        Product(product_id="1", title="X", category="Y", release_year=1500)


def test_product_con_rental_rate_negativo_falla():
    with pytest.raises(ValidationError):
        Product(product_id="1", title="X", category="Y", rental_rate=-5.0)


def test_to_dynamodb_item_omite_campos_none():
    product = Product(product_id="1", title="X", category="Y")
    item = product.to_dynamodb_item()
    assert "release_year" not in item
    assert "rental_rate" not in item
    assert item["product_id"] == "1"


def test_special_features_default_es_lista_vacia():
    product = Product(product_id="1", title="X", category="Y")
    assert product.special_features == []


def test_to_dynamodb_item_convierte_floats_a_decimal():
    from decimal import Decimal

    product = Product(
        product_id="1", title="X", category="Y", rental_rate=0.99, replacement_cost=20.99
    )
    item = product.to_dynamodb_item()
    assert isinstance(item["rental_rate"], Decimal)
    assert isinstance(item["replacement_cost"], Decimal)
    assert item["rental_rate"] == Decimal("0.99")
