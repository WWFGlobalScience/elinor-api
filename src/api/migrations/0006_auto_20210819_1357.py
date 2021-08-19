# Generated by Django 3.2.2 on 2021-08-19 13:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20210815_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessment',
            name='management_area_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, default=None, related_name='ma_assessments', to='api.managementareaversion'),
        ),
        migrations.AlterField(
            model_name='assessment',
            name='person_responsible_role',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(10, 'nonprofit staff'), (20, 'management area manager'), (30, 'management area personnel'), (40, 'government personnel'), (50, 'members of local community / indigenous committees'), (60, 'community leaders / representatives')], null=True),
        ),
    ]
