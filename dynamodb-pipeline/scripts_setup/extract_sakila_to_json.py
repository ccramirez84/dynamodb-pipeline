"""
Extrae datos reales del dataset público Sakila (jOOQ/sakila en GitHub)
directamente de los scripts SQL de inserción, sin necesidad de un
servidor MySQL corriendo. Genera un JSON de "catálogo de productos"
(películas) listo para cargar en DynamoDB.

Fuente: https://github.com/jOOQ/sakila (BSD License, MySQL AB / jOOQ)
"""
import re
import json
import csv
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INSERT_DATA_SQL = RAW_DIR / "sakila-insert-data.sql"


def extract_table_block(sql_text: str, table_name: str) -> str:
    """Aísla el bloque de texto correspondiente a los INSERT de una tabla,
    delimitado por el comentario '-- table <nombre>' y el siguiente '-- table'."""
    pattern = rf"-- table {table_name}\n(.*?)(?=\n-- table |\Z)"
    match = re.search(pattern, sql_text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"No se encontró el bloque de la tabla '{table_name}'")
    return match.group(1)


def parse_values_tuple(raw_values: str) -> list[str]:
    """Convierte el contenido entre paréntesis de un VALUES(...) en una lista
    de strings, respetando comas dentro de comillas simples y NULL literal."""
    fields = []
    current = ""
    in_quotes = False
    i = 0
    while i < len(raw_values):
        ch = raw_values[i]
        if ch == "'" and not in_quotes:
            in_quotes = True
            i += 1
            continue
        if ch == "'" and in_quotes:
            # Comilla escapada como '' dentro de un string SQL
            if i + 1 < len(raw_values) and raw_values[i + 1] == "'":
                current += "'"
                i += 2
                continue
            in_quotes = False
            i += 1
            continue
        if ch == "," and not in_quotes:
            fields.append(current.strip())
            current = ""
            i += 1
            continue
        current += ch
        i += 1
    if current.strip() != "":
        fields.append(current.strip())
    return [None if f == "NULL" else f for f in fields]


def parse_inserts(block: str) -> list[dict]:
    """Parsea todos los statements 'Insert into <tabla> (cols) Values (...)'
    de un bloque de texto y devuelve una lista de diccionarios columna->valor."""
    statements = re.findall(
        r"Insert into \w+\s*\(([^)]+)\)\s*Values\s*\(([^;]+?)\)\s*;",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    rows = []
    for cols_raw, vals_raw in statements:
        cols = [c.strip().strip("`") for c in cols_raw.split(",")]
        values = parse_values_tuple(vals_raw)
        if len(values) != len(cols):
            # Salta filas mal formadas en lugar de fallar todo el extractor
            continue
        rows.append(dict(zip(cols, values)))
    return rows


def main():
    sql_text = INSERT_DATA_SQL.read_text(encoding="utf-8", errors="ignore")

    films = parse_inserts(extract_table_block(sql_text, "film"))
    categories = parse_inserts(extract_table_block(sql_text, "category"))
    film_category = parse_inserts(extract_table_block(sql_text, "film_category"))

    cat_by_id = {c["category_id"]: c["name"] for c in categories}
    film_to_cat = {fc["film_id"]: cat_by_id.get(fc["category_id"]) for fc in film_category}

    catalog = []
    for f in films:
        catalog.append(
            {
                "product_id": f["film_id"],
                "title": f["title"],
                "description": f["description"],
                "category": film_to_cat.get(f["film_id"], "UNKNOWN"),
                "release_year": int(f["release_year"]) if f["release_year"] else None,
                "rental_rate": float(f["rental_rate"]) if f["rental_rate"] else None,
                "replacement_cost": float(f["replacement_cost"]) if f["replacement_cost"] else None,
                "rating": f["rating"],
                "length_minutes": int(f["length"]) if f["length"] else None,
                "special_features": f["special_features"].split(",") if f["special_features"] else [],
            }
        )

    out_path = OUT_DIR / "product_catalog.json"
    out_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = OUT_DIR / "product_catalog.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=catalog[0].keys())
        writer.writeheader()
        for row in catalog:
            row = dict(row)
            row["special_features"] = ";".join(row["special_features"])
            writer.writerow(row)

    print(f"Extraídos {len(catalog)} productos reales de Sakila")
    print(f"JSON -> {out_path}")
    print(f"CSV  -> {csv_path}")
    print("Ejemplo:", json.dumps(catalog[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
