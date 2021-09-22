# Generated by Django 3.2.2 on 2021-09-22 02:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_managementarea_countries'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='protectedarea',
            name='wdpa_id',
        ),
        migrations.AddField(
            model_name='managementarea',
            name='wdpa_protected_area',
            field=models.IntegerField(blank=True, null=True, verbose_name='WDPA ID'),
        ),
    ]
