def alphabetical_dispatch(students: list[dict], rooms: list[dict]) -> list[dict]:
    """
    Répartit les élèves alphabétiquement dans les salles.

    students: [{'id': int, 'last_name': str, 'first_name': str}, ...]
    rooms: [{'id': int, 'name': str, 'capacity': int}, ...]

    Retourne: [{'student_id': int, 'room_id': int, 'seat_number': int}, ...]
    """
    if not students or not rooms:
        return []

    sorted_students = sorted(students, key=lambda s: (s["last_name"].upper(), s["first_name"].upper()))

    total_capacity = sum(r["capacity"] for r in rooms)
    if total_capacity < len(sorted_students):
        raise ValueError(
            f"Capacité totale ({total_capacity}) insuffisante pour {len(sorted_students)} élèves."
        )

    assignments = []
    student_idx = 0
    for room in rooms:
        seat = 1
        while seat <= room["capacity"] and student_idx < len(sorted_students):
            assignments.append({
                "student_id": sorted_students[student_idx]["id"],
                "room_id": room["id"],
                "seat_number": seat,
            })
            student_idx += 1
            seat += 1

    return assignments
