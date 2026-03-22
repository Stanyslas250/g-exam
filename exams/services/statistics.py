import statistics
from collections import Counter


def compute_global_stats(students_data: list[dict], passing_grade: float = 10.0) -> dict:
    """
    Calcule les statistiques globales d'un examen.

    students_data: [{'student_id': int, 'average': float | None, 'gender': str, ...}, ...]
    """
    if not students_data:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "absent": 0,
            "pass_rate": 0,
            "overall_average": 0,
            "highest": 0,
            "lowest": 0,
            "gender_stats": {},
        }

    averages = [s["average"] for s in students_data if s.get("average") is not None]
    absent = sum(1 for s in students_data if s.get("is_absent"))
    passed = sum(1 for a in averages if a >= passing_grade)
    failed = sum(1 for a in averages if a < passing_grade)

    gender_counts = Counter(s.get("gender", "") for s in students_data)
    gender_passed = {}
    for g in ["M", "F"]:
        g_averages = [
            s["average"] for s in students_data
            if s.get("gender") == g and s.get("average") is not None
        ]
        g_passed = sum(1 for a in g_averages if a >= passing_grade)
        gender_passed[g] = {
            "total": gender_counts.get(g, 0),
            "passed": g_passed,
            "failed": len(g_averages) - g_passed,
            "pass_rate": round(g_passed / len(g_averages) * 100, 1) if g_averages else 0,
        }

    return {
        "total": len(students_data),
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "pass_rate": round(passed / len(averages) * 100, 1) if averages else 0,
        "overall_average": round(sum(averages) / len(averages), 2) if averages else 0,
        "highest": round(max(averages), 2) if averages else 0,
        "lowest": round(min(averages), 2) if averages else 0,
        "gender_stats": gender_passed,
    }


def compute_subject_stats(scores: list[dict], max_score: float = 20.0) -> dict:
    """
    Calcule les statistiques d'une épreuve.

    scores: [{'value': float}, ...]
    """
    values = [s["value"] for s in scores if s.get("value") is not None]
    if not values:
        return {
            "count": 0,
            "average": 0,
            "highest": 0,
            "lowest": 0,
            "above_avg": 0,
            "median": 0,
            "stdev": 0,
        }

    avg = sum(values) / len(values)
    med = statistics.median(values)
    sd = round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0
    return {
        "count": len(values),
        "average": round(avg, 2),
        "highest": round(max(values), 2),
        "lowest": round(min(values), 2),
        "above_avg": sum(1 for v in values if v >= max_score / 2),
        "median": round(med, 2),
        "stdev": sd,
    }


def compute_distribution(averages: list[float], bins: int = 5, max_val: float = 20.0) -> list[dict]:
    """
    Calcule la distribution des moyennes par tranches.
    """
    if not averages:
        return []

    step = max_val / bins
    result = []
    for i in range(bins):
        low = round(i * step, 1)
        high = round((i + 1) * step, 1)
        label = f"{low}-{high}"
        count = sum(1 for a in averages if low <= a < high) if i < bins - 1 else sum(1 for a in averages if low <= a <= high)
        result.append({"label": label, "count": count})

    return result
