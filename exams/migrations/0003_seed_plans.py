from django.db import migrations


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("exams", "Plan")

    Plan.objects.bulk_create([
        Plan(
            name="Découverte",
            slug="decouverte",
            tagline="Idéal pour tester G-Exam sur une petite session",
            price_fcfa=None,
            billing_period="FREE",
            max_exams=1,
            max_students_per_exam=50,
            max_teachers=2,
            features=[
                "1 examen",
                "Jusqu'à 50 candidats",
                "2 correcteurs",
                "Saisie des notes",
                "Classements",
                "Export PDF",
            ],
            is_active=True,
            is_featured=False,
            sort_order=10,
        ),
        Plan(
            name="Standard",
            slug="standard",
            tagline="Pour les centres d'examen et établissements de taille moyenne",
            price_fcfa=25000,
            billing_period="MONTHLY",
            max_exams=5,
            max_students_per_exam=500,
            max_teachers=20,
            features=[
                "Jusqu'à 5 examens",
                "500 candidats / examen",
                "20 correcteurs",
                "Saisie des notes",
                "Classements & statistiques",
                "Exports PDF + Excel",
                "Répartition en salles",
                "Historique des modifications",
            ],
            is_active=True,
            is_featured=True,
            sort_order=20,
        ),
        Plan(
            name="Établissement",
            slug="etablissement",
            tagline="Pour les grandes structures avec des besoins illimités",
            price_fcfa=75000,
            billing_period="MONTHLY",
            max_exams=None,
            max_students_per_exam=None,
            max_teachers=None,
            features=[
                "Examens illimités",
                "Candidats illimités",
                "Correcteurs illimités",
                "Toutes les fonctionnalités Standard",
                "Harmonisation des notes",
                "Support prioritaire",
                "Répartition en salles",
                "Import / export JSON complet",
            ],
            is_active=True,
            is_featured=False,
            sort_order=30,
        ),
    ])


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("exams", "Plan")
    Plan.objects.filter(slug__in=["decouverte", "standard", "etablissement"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0002_plan_userprofile"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
