"""Leitura dos CSVs originais, preservando textos e campos dos artigos."""

import csv
import hashlib
from pathlib import Path


class DataError(ValueError):
    """Entrada inválida ou saída existente incompatível com esta execução."""


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Lê registros CSV (não linhas físicas), incluindo textos multilinha."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise DataError(f"{path.name}: cabeçalhos repetidos.")
        missing = required - set(fields)
        if missing:
            raise DataError(f"{path.name}: colunas ausentes: {sorted(missing)}")
        rows = []
        for number, row in enumerate(reader, start=1):
            if None in row or any(value is None for value in row.values()):
                raise DataError(f"{path.name}: registro {number} com número incorreto de campos.")
            rows.append(row)
    if not rows:
        raise DataError(f"{path.name}: nenhum registro encontrado.")
    return rows


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
