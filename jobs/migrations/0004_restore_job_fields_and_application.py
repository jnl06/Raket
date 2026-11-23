"""Bring back the Job fields and the Application model that 0003 dropped.

Background: a merge overwrote ``jobs/models.py`` and 0003 (auto-generated from that
broken state) deleted the columns the API depends on. 0003 may already be applied on a
developer's database, so it stays in the history and this migration restores everything.

Unlike 0002, the content fields are added **without a permanent default**. The
``default=`` values below only back-fill rows that already exist (``preserve_default=False``
drops them from the model afterwards).
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0003_remove_application_unique_application_per_job_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="employment_type",
            field=models.CharField(
                choices=[
                    ("full_time", "Full-time"),
                    ("part_time", "Part-time"),
                    ("one_time", "One-time"),
                ],
                default="one_time",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="duration",
            field=models.CharField(
                choices=[
                    ("one_day", "1 day"),
                    ("few_days", "2-6 days"),
                    ("one_two_weeks", "1-2 weeks"),
                    ("up_to_month", "Up to 1 month"),
                    ("ongoing", "Ongoing"),
                ],
                default="one_day",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="pay_period",
            field=models.CharField(
                choices=[("day", "Day"), ("hour", "Hour"), ("job", "Whole job")],
                default="day",
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="max_payment",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Upper end of a pay range (e.g. 500 - 900 a day). Optional.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="experience",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="industry",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="how_to_apply",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("closed", "Closed")],
                db_index=True,
                default="active",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="job",
            name="number_of_workers",
            field=models.PositiveSmallIntegerField(
                validators=[django.core.validators.MinValueValidator(1)]
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="requirements",
            field=models.TextField(
                blank=True, help_text="One qualification per line (shown as bullets)."
            ),
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cover_note", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("under_review", "Under review"),
                            ("hired", "Hired"),
                            ("rejected", "Not selected"),
                        ],
                        db_index=True,
                        default="submitted",
                        max_length=15,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applications",
                        to="jobs.job",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("job", "applicant"), name="unique_application_per_job"
                    )
                ],
            },
        ),
    ]
