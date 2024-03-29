# Generated by Django 3.2.22 on 2024-03-02 16:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0028_auto_20231005_1118'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessment',
            name='checkout',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='checked_out_assessments', to=settings.AUTH_USER_MODEL),
        ),
    ]
