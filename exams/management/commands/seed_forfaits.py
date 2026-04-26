"""
Remplit la table des forfaits (Plan) avec les offres de référence.

  python manage.py seed_forfaits

Avec recréation (met à jour les champs) pour les mêmes slugs :

  python manage.py seed_forfaits --force
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import Plan


# Slugs stables : utilisés pour idempotence (update_or_create)
DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "name": "Gratuit",
        "slug": "gratuit",
        "tagline": "Essai de la plateforme",
        "description": "Plafons modestes pour découvrir les fonctionnalités.",
        "price_fcfa": None,
        "billing_period": Plan.BILLING_FREE,
        "max_exams": 1,
        "max_students_per_exam": 30,
        "max_teachers": 5,
        "max_establishments": 1,
        "features": [
            "1 examen",
            "Jusqu’à 30 candidats / examen",
            "1 établissement",
        ],
        "is_active": True,
        "is_featured": False,
        "sort_order": 0,
    },
    {
        "name": "Pack examen",
        "slug": "pack-examen",
        "tagline": "Un examen, plusieurs établissements",
        "description": "Paiement à la session d’examen, plafond 5 établissements et 150 élèves.",
        "price_fcfa": 50_000,
        "billing_period": Plan.BILLING_BY_EXAM,
        "max_exams": 1,
        "max_students_per_exam": 150,
        "max_teachers": None,
        "max_establishments": 5,
        "features": [
            "1 session d’examen",
            "Jusqu’à 5 établissements",
            "Jusqu’à 150 élèves (candidats) au total",
            "50 000 FCFA",
        ],
        "is_active": True,
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "name": "Abonnement annuel illimité",
        "slug": "abonnement-annuel-illimite",
        "tagline": "Tout illimité pour une année",
        "description": "Examens, établissements et effectifs illimités. Engagement sur 12 mois (facturation annuelle).",
        "price_fcfa": 150_000,
        "billing_period": Plan.BILLING_YEARLY,
        "max_exams": None,
        "max_students_per_exam": None,
        "max_teachers": None,
        "max_establishments": None,
        "features": [
            "Nombre d’examens illimité",
            "Nombre d’établissements illimité",
            "Nombre d’élèves illimité",
            "Valable 1 an (12 mois)",
            "150 000 FCFA / an",
        ],
        "is_active": True,
        "is_featured": True,
        "sort_order": 2,
    },
]


class Command(BaseCommand):
    help = "Insère ou met à jour les forfaits de référence (gratuit, pack examen, abonnement annuel)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Mettre à jour les forfaits existants (même slug).",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        force: bool = options["force"]
        created = 0
        updated = 0

        for data in DEFAULT_PLANS:
            slug = data["slug"]
            values = {k: v for k, v in data.items() if k != "slug"}
            if force:
                _obj, is_created = Plan.objects.update_or_create(
                    slug=slug,
                    defaults=values,
                )
            else:
                _obj, is_created = Plan.objects.get_or_create(
                    slug=slug,
                    defaults=values,
                )
            if is_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Créé : {values['name']} ({slug})"))
            else:
                if force:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(f"Mis à jour : {values['name']} ({slug})")
                    )
                else:
                    self.stdout.write(
                        f"Ignoré (déjà présent) : {values['name']} ({slug}) — relancer avec --force pour appliquer les changements."
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé. Créations : {created}, mises à jour : {updated} (mode force={force})."
            )
        )
