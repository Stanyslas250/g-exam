def rank_students(students: list[dict]) -> list[dict]:
    """
    Classe les élèves par moyenne décroissante avec gestion des ex-aequo.

    Entrée : [{'student_id': int, 'average': float, ...}, ...]
    Sortie : [{'student_id': int, 'average': float, 'rank': int, ...}, ...]
    """
    if not students:
        return []

    sorted_students = sorted(
        students, key=lambda s: (-(s.get("average") or 0), s.get("student_id", 0))
    )

    ranked = []
    current_rank = 1
    for i, student in enumerate(sorted_students):
        if i > 0 and student["average"] != sorted_students[i - 1]["average"]:
            current_rank = i + 1
        ranked.append({**student, "rank": current_rank})

    return ranked


def rank_schools(schools: list[dict]) -> list[dict]:
    """
    Classe les établissements par moyenne décroissante.

    Entrée : [{'school_id': int, 'school_name': str, 'average': float, 'total_students': int, 'passed': int}, ...]
    """
    if not schools:
        return []

    sorted_schools = sorted(
        schools, key=lambda s: (-(s.get("average") or 0), s.get("school_name", ""))
    )

    ranked = []
    current_rank = 1
    for i, school in enumerate(sorted_schools):
        if i > 0 and school["average"] != sorted_schools[i - 1]["average"]:
            current_rank = i + 1
        ranked.append({**school, "rank": current_rank})

    return ranked
