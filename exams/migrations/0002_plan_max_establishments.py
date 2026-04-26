# Generated manually for Plan.max_establishments

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="max_establishments",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Vide = illimité.",
                null=True,
                verbose_name="Nb max d'établissements",
            ),
        ),
        migrations.AddField(
            model_name="historicalplan",
            name="max_establishments",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Vide = illimité.",
                null=True,
                verbose_name="Nb max d'établissements",
            ),
        ),
    ]
