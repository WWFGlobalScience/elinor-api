# Generated by Django 3.2.13 on 2022-07-14 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_alter_surveyquestionlikert_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='order',
            field=models.PositiveSmallIntegerField(unique=True),
        ),
    ]
