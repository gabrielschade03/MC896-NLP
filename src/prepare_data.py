"""CLI da etapa 1. Execute na raiz: python -m src.prepare_data."""

import argparse
import csv
import io
import json
from pathlib import Path

from .data_io import DataError, read_csv, sha256_file
from .splitting import split_by_article
from .validation import validate

ROOT = Path(__file__).resolve().parents[1]
CASE_FIELDS = {"article_id", "case_id", "case_text", "age", "gender"}
METADATA_FIELDS = {"article_id", "title", "keywords", "mesh_terms", "major_mesh_terms"}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _split_csv(rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["case_id", "article_id"], lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row[key] for key in writer.fieldnames} for row in rows)
    return stream.getvalue()


def prepare(input_dir: Path, output_dir: Path, evaluation_fraction: float = 0.2, seed: int = 42) -> dict:
    cases_path, metadata_path = input_dir / "cases.csv", input_dir / "metadata.csv"
    cases = read_csv(cases_path, CASE_FIELDS)
    metadata = read_csv(metadata_path, METADATA_FIELDS)
    report = validate(cases, metadata)
    if report["errors"]:
        raise DataError("Validação falhou:\n- " + "\n- ".join(report["errors"]))

    groups = split_by_article(cases, evaluation_fraction, seed)
    article_index = {row["article_id"]: row for row in metadata}
    report["splits"] = {
        name: {"cases": len(rows), "articles": len({row["article_id"] for row in rows})}
        for name, rows in groups.items()
    }
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "evaluation_fraction": evaluation_fraction,
        "algorithm": "sha256(seed:article_id), ascending; ceil(fraction * articles)",
        "sources": {"cases.csv": sha256_file(cases_path), "metadata.csv": sha256_file(metadata_path)},
        "article_ids": {
            name: sorted({row["article_id"] for row in rows}) for name, rows in groups.items()
        },
    }
    files = {
        "validation_report.json": _json(report),
        "manifest.json": _json(manifest),
    }
    for name, rows in groups.items():
        files[f"splits/{name}.csv"] = _split_csv(rows)
        # Mantém os campos do artigo separados dos campos do caso (sem colisões).
        records = ({"case": row, "article": article_index[row["article_id"]]} for row in rows)
        files[f"records/{name}.jsonl"] = "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        )

    # Não troca silenciosamente uma divisão já utilizada nos experimentos.
    for relative, content in files.items():
        path = output_dir / relative
        if path.exists() and path.read_bytes() != content.encode("utf-8"):
            raise DataError(f"Saída existente incompatível: {path}. Use outro --output-dir para uma nova versão.")
    for relative, content in files.items():
        path = output_dir / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida e separa casos clínicos por artigo.")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "Projeto 1" / "sample")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "prepared")
    parser.add_argument("--evaluation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        report = prepare(args.input_dir, args.output_dir, args.evaluation_fraction, args.seed)
    except (DataError, OSError, UnicodeError, csv.Error) as exc:
        parser.exit(1, f"Erro: {exc}\n")
    print(f"Validação concluída: {report['counts']['cases']} casos, {report['counts']['metadata_articles']} artigos.")
    for name, counts in report["splits"].items():
        print(f"{name}: {counts['cases']} casos, {counts['articles']} artigos")
    print(f"Avisos: {len(report['warnings'])}. Consulte validation_report.json.")
    print(f"Saída: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
