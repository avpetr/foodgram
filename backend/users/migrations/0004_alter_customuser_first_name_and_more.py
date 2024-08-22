# Generated by Django 5.1 on 2024-08-18 00:13

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_customuser_avatar"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="first_name",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="last_name",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="username",
            field=models.CharField(
                max_length=150,
                validators=[
                    django.core.validators.RegexValidator(
                        code="invalid_registration",
                        message="Enter a valid registration username",
                        regex="^[\\w.@+-]+\\z",
                    )
                ],
            ),
        ),
    ]
