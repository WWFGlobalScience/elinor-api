# Generated by Django 3.2.13 on 2022-08-09 21:51

from django.db import migrations
from ..models import Assessment, GovernanceType, ManagementArea


def convert_choices(*args, **kwargs):
    mg = GovernanceType.objects.get(name="Mixed governance")
    sg = GovernanceType.objects.get(name="Shared governance/co-management")
    ManagementArea.objects.filter(governance_type=mg).update(governance_type=sg)
    mg.delete()

    Assessment.objects.filter(collection_method=20).update(
        collection_method=Assessment.DESKBASED
    )
    Assessment.objects.filter(collection_method=40).update(
        collection_method=Assessment.OTHER_COLLECTION_METHOD
    )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0016_assessmentflag"),
    ]

    operations = [migrations.RunPython(convert_choices, migrations.RunPython.noop)]
