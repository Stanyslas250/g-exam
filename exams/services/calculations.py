from typing import Optional


def calculate_student_average(
    scores: list[dict],
    target_scale: float = 20.0,
) -> Optional[float]:
    """
    Calcule la moyenne d'un élève.

    Chaque score est un dict : {
        'value': float,
        'coefficient': float | None,
        'max_score': float | None,
    }

    Règles :
    - Si au moins un coefficient est défini → moyenne pondérée
    - Sinon → moyenne simple
    - Si des maxScore différents → normalisation vers target_scale
    """
    valid_scores = [s for s in scores if s.get("value") is not None]
    if not valid_scores:
        return None

    has_coefficients = any(
        s.get("coefficient") is not None and s["coefficient"] > 0
        for s in valid_scores
    )
    has_variable_max = any(
        s.get("max_score") is not None and s["max_score"] > 0
        for s in valid_scores
    )

    if has_variable_max:
        if has_coefficients:
            total_weighted = 0.0
            total_coef = 0.0
            for s in valid_scores:
                coef = s.get("coefficient") or 1.0
                max_score = s.get("max_score") or target_scale
                normalized = (s["value"] / max_score) * target_scale if max_score > 0 else 0
                total_weighted += normalized * coef
                total_coef += coef
            return round(total_weighted / total_coef, 2) if total_coef > 0 else None
        else:
            total_score = sum(s["value"] for s in valid_scores)
            total_max = sum((s.get("max_score") or target_scale) for s in valid_scores)
            return round((total_score / total_max) * target_scale, 2) if total_max > 0 else None
    else:
        if has_coefficients:
            total_weighted = 0.0
            total_coef = 0.0
            for s in valid_scores:
                coef = s.get("coefficient") or 1.0
                total_weighted += s["value"] * coef
                total_coef += coef
            return round(total_weighted / total_coef, 2) if total_coef > 0 else None
        else:
            total = sum(s["value"] for s in valid_scores)
            return round(total / len(valid_scores), 2)


def get_mention(
    average: float,
    passing_grade: float = 10.0,
    scale_max: float = 20.0,
) -> str:
    """Retourne la mention en fonction de la moyenne (seuils proportionnels au barème)."""
    if average is None:
        return ""
    if average < passing_grade:
        return "Ajourné"
    r = (scale_max / 20.0) if scale_max and scale_max > 0 else 1.0
    if average < 12 * r:
        return "Passable"
    if average < 14 * r:
        return "Assez Bien"
    if average < 16 * r:
        return "Bien"
    if average < 18 * r:
        return "Très Bien"
    return "Excellent"
