"""Verifica integridade dos IDs, vínculo entre arquivos e campos ausentes."""

from collections import Counter
from math import isfinite


def _duplicates(rows: list[dict], key: str) -> list[str]:
    counts = Counter(row[key] for row in rows if row[key].strip())
    return sorted(value for value, count in counts.items() if count > 1)


def _missing(rows: list[dict]) -> dict[str, int]:
    return {key: sum(not row[key].strip() for row in rows) for key in rows[0]}


def validate(cases: list[dict], metadata: list[dict]) -> dict:
    """Erros bloqueiam a preparação; avisos são preservados no relatório."""
    errors, warnings = [], []
    for name, rows, required in (
        ("cases.csv", cases, ("case_id", "article_id", "case_text")),
        ("metadata.csv", metadata, ("article_id",)),
    ):
        for key in required:
            count = sum(not row[key].strip() for row in rows)
            if count:
                errors.append(f"{name}: {count} registros sem {key}.")
        for key in ("case_id", "article_id") if name == "cases.csv" else ("article_id",):
            if any(row[key] != row[key].strip() for row in rows):
                errors.append(f"{name}: espaços nas extremidades de {key}; revisar a origem.")

    duplicates = {
        "case_id": _duplicates(cases, "case_id"),
        "metadata_article_id": _duplicates(metadata, "article_id"),
    }
    for key, values in duplicates.items():
        if values:
            errors.append(f"IDs duplicados em {key}: {values}")

    case_articles = {row["article_id"] for row in cases}
    metadata_articles = {row["article_id"] for row in metadata}
    orphans = sorted(case_articles - metadata_articles)
    unused = sorted(metadata_articles - case_articles)
    if orphans:
        errors.append(f"Artigos dos casos sem metadata: {orphans}")
    if unused:
        warnings.append(f"{len(unused)} artigos sem casos; não participam da divisão.")

    invalid_ages = []
    for row in cases:
        value = row["age"].strip()
        if value:
            try:
                number = float(value)
                valid = isfinite(number) and number >= 0
            except ValueError:
                valid = False
            if not valid:
                invalid_ages.append(row["case_id"])
    if invalid_ages:
        warnings.append(f"Idades não numéricas ou inválidas, preservadas: {invalid_ages}")

    actual_counts = Counter(row["article_id"] for row in cases)
    mismatches = []
    for row in metadata:
        raw = row.get("case_amount", "").strip()
        if not raw:
            continue
        try:
            expected = int(raw)
        except ValueError:
            warnings.append(f"case_amount inválido no artigo {row['article_id']}: {raw}")
            continue
        actual = actual_counts[row["article_id"]]
        if expected != actual:
            mismatches.append({"article_id": row["article_id"], "declared": expected, "observed": actual})
    if mismatches:
        warnings.append("Há divergências em case_amount; ver case_amount_mismatches.")

    missing = {"cases": _missing(cases), "metadata": _missing(metadata)}
    for name, fields in missing.items():
        for field, count in fields.items():
            if count:
                warnings.append(f"{name}.{field}: {count} valores vazios (não preenchidos automaticamente).")
    return {
        "counts": {"cases": len(cases), "metadata_articles": len(metadata),
                   "case_articles": len(case_articles)},
        "missing_fields": missing,
        "duplicate_ids": duplicates,
        "orphan_article_ids": orphans,
        "unused_article_ids": unused,
        "gender_counts": dict(sorted(Counter(row["gender"] for row in cases).items())),
        "invalid_age_case_ids": invalid_ages,
        "case_amount_mismatches": mismatches,
        "errors": errors,
        "warnings": warnings,
    }
