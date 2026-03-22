# Generated manually for exam grading_scale (barème)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0003_exam_code_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="exam",
            name="grading_scale",
            field=models.FloatField(
                default=20.0,
                help_text="Échelle des moyennes et du seuil (ex. 20 pour le bac, 10 pour un contrôle). Les notes par épreuve restent sur leur propre note max.",
                verbose_name="Barème (note max de référence)",
            ),
        ),
    ]
