"""
Crée (ou promeut) un superutilisateur pour l’admin Django.

Usage non interactif (recommandé en déploiement) :
  set SUPER_ADMIN_USERNAME=
  set SUPER_ADMIN_EMAIL=
  set SUPER_ADMIN_PASSWORD=
  python manage.py create_super_admin --noinput

Alias de variables d’environnement (comme `createsuperuser --noinput`) :
  DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD

Mode interactif :
  python manage.py create_super_admin
"""

from __future__ import annotations

import getpass
import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email


def _env(*keys: str) -> str:
    for key in keys:
        v = os.environ.get(key, "").strip()
        if v:
            return v
    return ""


class Command(BaseCommand):
    help = "Crée un compte superutilisateur (is_staff + is_superuser) ou promeut un utilisateur existant."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--username",
            type=str,
            help="Nom d’utilisateur (ou SUPER_ADMIN_USERNAME / DJANGO_SUPERUSER_USERNAME en --noinput).",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="",
            help="E-mail (optionnel).",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Mot de passe (déconseillé : risque d’apparaître dans l’historique du shell).",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Lire identifiants depuis l’environnement ; pas d’invite interactive.",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Si l’utilisateur existe : promouvoir superuser / mettre à jour le mot de passe si fourni.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        User = get_user_model()
        noinput: bool = options["noinput"]
        update: bool = options["update"]

        username = (options.get("username") or "").strip()
        email = (options.get("email") or "").strip()
        password = options.get("password") or None

        if noinput:
            if not username:
                username = _env("SUPER_ADMIN_USERNAME", "DJANGO_SUPERUSER_USERNAME")
            if not email:
                email = _env("SUPER_ADMIN_EMAIL", "DJANGO_SUPERUSER_EMAIL")
            if not password:
                password = _env("SUPER_ADMIN_PASSWORD", "DJANGO_SUPERUSER_PASSWORD")
        else:
            if not username:
                username = input("Nom d’utilisateur : ").strip()
            if not email:
                email = input("E-mail (Entrée pour laisser vide) : ").strip()
            if not password:
                p1 = getpass.getpass("Mot de passe : ")
                p2 = getpass.getpass("Confirmer le mot de passe : ")
                if p1 != p2:
                    raise CommandError("Les mots de passe ne correspondent pas.")
                password = p1

        if not username:
            raise CommandError("Le nom d’utilisateur est obligatoire.")
        if not password and not noinput:
            raise CommandError("Le mot de passe est obligatoire.")
        if not password and noinput:
            raise CommandError(
                "En mode --noinput, définissez SUPER_ADMIN_PASSWORD ou "
                "DJANGO_SUPERUSER_PASSWORD (ou --password)."
            )

        if email:
            try:
                validate_email(email)
            except ValidationError as e:
                raise CommandError("E-mail invalide.") from e

        exists = User.objects.filter(username=username).exists()
        if exists and not update:
            raise CommandError(
                f"Un utilisateur « {username} » existe déjà. "
                f"Utilisez --update pour le promouvoir en superutilisateur, ou choisissez un autre nom."
            )

        if exists:
            user = User.objects.get(username=username)
            user.is_staff = True
            user.is_superuser = True
            if email:
                user.email = email
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Superutilisateur mis à jour : {username}")
            )
            return

        user = User(
            username=username,
            email=email,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(f"Superutilisateur créé : {username}")
        )
