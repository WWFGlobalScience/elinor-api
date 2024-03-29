# Generated by Django 3.2.13 on 2022-06-02 20:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0008_auto_20211108_1343'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('required', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attribute_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attribute_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SurveyQuestionLikert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('key', models.CharField(max_length=255, unique=True)),
                ('number', models.PositiveSmallIntegerField(unique=True)),
                ('text', models.TextField()),
                ('rationale', models.TextField()),
                ('information', models.TextField()),
                ('guidance', models.TextField()),
                ('dontknow_10', models.TextField()),
                ('poor_20', models.TextField()),
                ('average_30', models.TextField()),
                ('good_40', models.TextField()),
                ('excellent_50', models.TextField()),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attribute_questions', to='api.attribute')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='surveyquestionlikert_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='surveyquestionlikert_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Likert survey question',
            },
        ),
        migrations.CreateModel(
            name='SurveyAnswerLikert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('choice', models.PositiveSmallIntegerField(choices=[(10, "don't know [10]"), (20, 'poor [20]'), (30, 'average [30]'), (40, 'good [40]'), (50, 'excellent [50]')])),
                ('explanation', models.TextField(blank=True)),
                ('assessment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.assessment')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='surveyanswerlikert_created_by', to=settings.AUTH_USER_MODEL)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='questionlikert_answers', to='api.surveyquestionlikert')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='surveyanswerlikert_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Likert survey answer',
            },
        ),
        migrations.CreateModel(
            name='AssessmentVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('year', models.PositiveSmallIntegerField()),
                ('major_version', models.PositiveSmallIntegerField()),
                ('text', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assessmentversion_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assessmentversion_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['year', 'major_version'],
            },
        ),
        migrations.AddField(
            model_name='assessment',
            name='attributes',
            field=models.ManyToManyField(to='api.Attribute'),
        ),
        migrations.AddField(
            model_name='assessment',
            name='published_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='api.assessmentversion'),
        ),
    ]
