import json
import sys

from src.main import main


def _run_cli(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["main.py"] + args)
    return main()


def test_cli_ingesta_exitosa_retorna_0(dynamodb_tables, sample_products_file, monkeypatch, capsys):
    exit_code = _run_cli(
        monkeypatch,
        [
            "--file",
            str(sample_products_file),
            "--catalog-table",
            dynamodb_tables["catalog_table_name"],
            "--log-table",
            dynamodb_tables["log_table_name"],
        ],
    )
    captured = capsys.readouterr()
    # sample_products_file tiene 1 item invalido a propósito -> exit code 2
    assert exit_code == 2
    assert "Insertados:" in captured.out
    assert "2" in captured.out


def test_cli_archivo_inexistente_retorna_1(monkeypatch, capsys, tmp_path):
    missing_file = tmp_path / "no_existe.json"
    exit_code = _run_cli(monkeypatch, ["--file", str(missing_file)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "no existe" in captured.err


def test_cli_archivo_100_valido_retorna_0(dynamodb_tables, monkeypatch, capsys, tmp_path):
    data = [{"product_id": "1", "title": "ACADEMY DINOSAUR", "category": "Documentary"}]
    file_path = tmp_path / "valid.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = _run_cli(
        monkeypatch,
        [
            "--file",
            str(file_path),
            "--catalog-table",
            dynamodb_tables["catalog_table_name"],
            "--log-table",
            dynamodb_tables["log_table_name"],
        ],
    )
    assert exit_code == 0


def test_cli_omitido_por_idempotencia_imprime_mensaje(
    dynamodb_tables, monkeypatch, capsys, tmp_path
):
    data = [{"product_id": "1", "title": "ACADEMY DINOSAUR", "category": "Documentary"}]
    file_path = tmp_path / "valid.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    args = [
        "--file",
        str(file_path),
        "--catalog-table",
        dynamodb_tables["catalog_table_name"],
        "--log-table",
        dynamodb_tables["log_table_name"],
    ]
    _run_cli(monkeypatch, args)
    capsys.readouterr()  # limpia el buffer de la primera corrida

    exit_code = _run_cli(monkeypatch, args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ya fue ingerido" in captured.out
