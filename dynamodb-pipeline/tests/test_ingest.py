import json

from src.ingest import ingest_file, load_and_validate, _was_already_ingested
from src.aws_clients import get_dynamodb_resource


def test_ingest_file_inserta_items_validos_y_reporta_invalidos(
    dynamodb_tables, sample_products_file
):
    result = ingest_file(
        file_path=sample_products_file,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )

    assert result.inserted == 2
    assert result.validation_errors == 1
    assert result.total_records == 3
    assert not result.success  # hubo errores de validación
    assert len(result.errors) == 1


def test_items_insertados_son_recuperables_de_dynamodb(
    dynamodb_tables, sample_products_file
):
    ingest_file(
        file_path=sample_products_file,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )

    table = dynamodb_tables["resource"].Table(dynamodb_tables["catalog_table_name"])
    response = table.get_item(Key={"product_id": "1"})

    assert "Item" in response
    assert response["Item"]["title"] == "ACADEMY DINOSAUR"
    assert response["Item"]["category"] == "Documentary"


def test_segunda_ejecucion_se_omite_por_idempotencia(
    dynamodb_tables, sample_products_file
):
    first_result = ingest_file(
        file_path=sample_products_file,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )
    assert not first_result.skipped_already_ingested

    second_result = ingest_file(
        file_path=sample_products_file,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )
    # La primera ejecución tuvo errores de validación, así que su status
    # es PARTIAL_FAILURE, no SUCCESS. La idempotencia solo se activa sobre
    # ejecuciones SUCCESS, así que la segunda corrida vuelve a procesar.
    assert not second_result.skipped_already_ingested


def test_idempotencia_real_con_archivo_100_por_ciento_valido(
    dynamodb_tables, tmp_path
):
    data = [
        {"product_id": "1", "title": "ACADEMY DINOSAUR", "category": "Documentary"},
        {"product_id": "2", "title": "ACE GOLDFINGER", "category": "Action"},
    ]
    file_path = tmp_path / "all_valid.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    first_result = ingest_file(
        file_path=file_path,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )
    assert first_result.success
    assert first_result.inserted == 2

    second_result = ingest_file(
        file_path=file_path,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )
    assert second_result.skipped_already_ingested
    assert second_result.inserted == 0  # no reprocesó nada


def test_force_reprocesa_aunque_ya_haya_sido_exitoso(dynamodb_tables, tmp_path):
    data = [{"product_id": "1", "title": "ACADEMY DINOSAUR", "category": "Documentary"}]
    file_path = tmp_path / "all_valid.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    ingest_file(
        file_path=file_path,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
    )

    forced_result = ingest_file(
        file_path=file_path,
        catalog_table_name=dynamodb_tables["catalog_table_name"],
        log_table_name=dynamodb_tables["log_table_name"],
        force=True,
    )
    assert not forced_result.skipped_already_ingested
    assert forced_result.inserted == 1


def test_load_and_validate_separa_correctamente_validos_e_invalidos(
    sample_products_file,
):
    products, errors = load_and_validate(sample_products_file)
    assert len(products) == 2
    assert len(errors) == 1
    assert "product_id=3" in errors[0]
