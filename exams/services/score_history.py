"""Enregistrement de l’historique des notes."""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser

from ..models import Score, ScoreHistory, Teacher


def log_score_change(
    score: Score,
    *,
    old_value: float | None,
    new_value: float,
    reason: str,
    comment: str = "",
    teacher: Teacher | None = None,
    admin_user: AbstractUser | None = None,
) -> ScoreHistory:
    """Crée une entrée d’historique pour une modification de note."""
    return ScoreHistory.objects.create(
        score=score,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        comment=comment or "",
        changed_by_teacher=teacher,
        changed_by_admin=admin_user if admin_user and admin_user.is_authenticated else None,
    )
