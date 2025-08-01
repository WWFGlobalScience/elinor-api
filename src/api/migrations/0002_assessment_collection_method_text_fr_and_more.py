# Generated by Django 4.2.16 on 2025-04-11 19:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessment',
            name='collection_method_text_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assessment',
            name='context_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assessment',
            name='name_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='assessment',
            name='needs_explanation_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assessment',
            name='strengths_explanation_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assessmentversion',
            name='text_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='description_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='document',
            name='description_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='name_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='governancetype',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='managementarea',
            name='geospatial_sources_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='managementarea',
            name='name_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='managementarea',
            name='objectives_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='managementareazone',
            name='description_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='managementareazone',
            name='name_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='managementauthority',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='protectedarea',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='region',
            name='name_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='stakeholdergroup',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='supportsource',
            name='name_fr',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='surveyanswerlikert',
            name='explanation_fr',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='average_1_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='excellent_3_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='good_2_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='guidance_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='information_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='poor_0_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='rationale_fr',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='surveyquestionlikert',
            name='text_fr',
            field=models.TextField(null=True),
        ),
    ]
