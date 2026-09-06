"""Divisão determinística por artigo: pacientes do mesmo artigo ficam juntos."""

import hashlib
import math

from .data_io import DataError


def split_by_article(cases: list[dict], evaluation_fraction: float, seed: int) -> dict[str, list[dict]]:
    if not 0 < evaluation_fraction < 1:
        raise DataError("A fração de avaliação deve estar entre 0 e 1, sem incluir os extremos.")
    articles = sorted({row["article_id"] for row in cases})
    if len(articles) < 2:
        raise DataError("São necessários pelo menos dois artigos para separar os grupos.")
    # Hash evita dependência da ordem do CSV e da versão do gerador aleatório.
    ranked = sorted(articles, key=lambda article: (
        hashlib.sha256(f"{seed}:{article}".encode()).hexdigest(), article
    ))
    count = min(len(articles) - 1, max(1, math.ceil(len(articles) * evaluation_fraction)))
    evaluation = set(ranked[:count])
    groups = {"development": [], "evaluation": []}
    for row in sorted(cases, key=lambda item: item["case_id"]):
        group = "evaluation" if row["article_id"] in evaluation else "development"
        groups[group].append(row)
    return groups
