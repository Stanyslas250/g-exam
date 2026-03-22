from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


def generate_results_pdf(exam, students_data: list[dict]) -> BytesIO:
    """
    Génère un PDF des résultats d'un examen.
    Retourne un BytesIO contenant le PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=16, spaceAfter=6,
    )
    elements.append(Paragraph(f"Résultats - {exam.name} ({exam.year})", title_style))
    elements.append(Spacer(1, 10))

    data = [["N°", "N° Candidat", "Nom", "Prénom", "Moyenne", "Rang", "Mention"]]
    for idx, s in enumerate(students_data, 1):
        avg_str = f"{s['average']:.2f}" if s.get("average") is not None else "-"
        data.append([
            str(idx),
            s.get("candidate_number", ""),
            s.get("last_name", ""),
            s.get("first_name", ""),
            avg_str,
            str(s.get("rank", "-")),
            s.get("mention", ""),
        ])

    col_widths = [30, 80, 100, 100, 60, 50, 80]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (3, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FF")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_room_dispatch_pdf(exam, rooms_data: list[dict]) -> BytesIO:
    """
    Génère un PDF de la répartition en salles.
    rooms_data: [{'room_name': str, 'assignments': [{'seat': int, 'name': str, 'candidate_number': str}]}]
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Répartition en salles - {exam.name} ({exam.year})", styles["Title"]))
    elements.append(Spacer(1, 10))

    for room in rooms_data:
        elements.append(Paragraph(f"Salle : {room['room_name']}", styles["Heading2"]))
        data = [["Place", "N° Candidat", "Nom & Prénom"]]
        for a in room["assignments"]:
            data.append([str(a["seat"]), a["candidate_number"], a["name"]])

        table = Table(data, colWidths=[50, 100, 250], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FF")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_transcripts_pdf(exam) -> BytesIO:
    """Un relevé de notes par élève (plusieurs pages)."""
    from ..models import Score, Student

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    elements = []
    styles = getSampleStyleSheet()

    students = Student.objects.filter(exam=exam).select_related("school").order_by("last_name", "first_name")
    subjects = list(exam.subjects.order_by("name"))

    for idx, student in enumerate(students):
        if idx:
            elements.append(PageBreak())
        elements.append(
            Paragraph(
                f"Relevé de notes — {exam.name} ({exam.year})",
                styles["Title"],
            ),
        )
        elements.append(Spacer(1, 6))
        elements.append(
            Paragraph(
                f"<b>{student.last_name}</b> {student.first_name} — N° {student.candidate_number} — {student.school.name}",
                styles["Normal"],
            ),
        )
        elements.append(Spacer(1, 10))

        score_map = {
            sc.subject_id: sc.value
            for sc in Score.objects.filter(student=student).select_related("subject")
        }
        data = [["Épreuve", "Coefficient", "Note", "Sur"]]
        for sub in subjects:
            val = score_map.get(sub.id)
            data.append([
                sub.name,
                str(sub.coefficient) if sub.coefficient is not None else "—",
                f"{val:.2f}" if val is not None else "—",
                str(sub.max_score),
            ])

        table = Table(data, colWidths=[200, 60, 60, 50], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#073763")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FF")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)

    if not elements:
        elements.append(Paragraph("Aucun élève", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer
