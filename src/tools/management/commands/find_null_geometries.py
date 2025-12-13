import csv
from django.core.management.base import BaseCommand
from api.models import Assessment


class Command(BaseCommand):
    help = 'Find ManagementAreas with null geometries in finalized assessments'

    def handle(self, *args, **options):
        # Find finalized assessments with null geometries
        finalized_assessments = Assessment.objects.filter(status=Assessment.FINALIZED)
        problematic_mas = []

        for assessment in finalized_assessments:
            if assessment.management_area and assessment.management_area.point is None and assessment.management_area.polygon is None:
                ma = assessment.management_area
                problematic_mas.append({
                    'management_area_id': ma.id,
                    'management_area_name': ma.name,
                    'assessment_id': assessment.id,
                    'assessment_name': assessment.name,
                    'assessment_year': assessment.year,
                    'assessment_status': assessment.status,
                    'ma_created_on': ma.created_on,
                    'ma_updated_on': ma.updated_on,
                    'ma_created_by': ma.created_by.username if ma.created_by else None,
                    'ma_updated_by': ma.updated_by.username if ma.updated_by else None,
                })

        csv_file = 'null_geometry_management_areas.csv'
        if problematic_mas:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=problematic_mas[0].keys())
                writer.writeheader()
                writer.writerows(problematic_mas)
            self.stdout.write(self.style.SUCCESS(f'Found {len(problematic_mas)} ManagementAreas with null geometries in finalized assessments'))
            self.stdout.write(self.style.SUCCESS(f'Results saved to {csv_file}'))
            for ma in problematic_mas[:10]:
                self.stdout.write(f"  MA ID {ma['management_area_id']}: {ma['management_area_name']} (Assessment: {ma['assessment_name']} {ma['assessment_year']})")
            if len(problematic_mas) > 10:
                self.stdout.write(f'  ... and {len(problematic_mas) - 10} more')
        else:
            self.stdout.write(self.style.WARNING('No ManagementAreas with null geometries found in finalized assessments'))
