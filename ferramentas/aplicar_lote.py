"""Aplica um lote revisavel de traducoes ao catalogo mestre PT-BR."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main(catalog: Path, batch: Path) -> None:
    rows = read_rows(catalog)
    translations = {row["en"]: row for row in read_rows(batch)}
    unknown = set(translations) - {row["en"] for row in rows}
    if unknown:
        raise SystemExit(f"ERRO: texto do lote nao existe no catalogo: {next(iter(unknown))!r}")

    changed = 0
    for row in rows:
        replacement = translations.get(row["en"])
        if replacement:
            row["pt_br"] = replacement["pt_br"]
            row["status"] = replacement.get("status") or "draft"
            row["notes"] = replacement.get("notes", "")
            changed += 1

    with catalog.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(translations)} textos distintos aplicados em {changed} ocorrencias")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("uso: aplicar_lote.py CATALOGO LOTE")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
