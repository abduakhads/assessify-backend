# Generated by Django 5.2.4 on 2025-07-15 04:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0003_alter_question_order_alter_studentquizattempt_score"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="time_limit",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="studentquizattempt",
            name="score",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True
            ),
        ),
    ]
