import io
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core import mail
from django.test.utils import override_settings
from api.models import Assessment, Collaborator, ManagementArea, Organization


User = get_user_model()


class Command(BaseCommand):
    help = "Test collaborator email notifications by simulating add/update/delete scenarios"

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='collaborator_email_test_output.txt',
            help='Output file path for test results'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        output_buffer = io.StringIO()

        def log(message):
            """Log to both stdout and buffer"""
            self.stdout.write(message)
            output_buffer.write(message + '\n')

        # Use test email backend to capture emails
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            log("=" * 80)
            log("COLLABORATOR EMAIL NOTIFICATION TEST")
            log("=" * 80)
            log("")

            # Setup test data
            log("Setting up test data...")

            # Create or get test users
            admin_user, _ = User.objects.get_or_create(
                username='AdminUser',
                defaults={
                    'email': 'admin@example.com',
                    'first_name': 'Admin',
                    'last_name': 'User'
                }
            )

            collab_user, _ = User.objects.get_or_create(
                username='CollabUser',
                defaults={
                    'email': 'collab@example.com',
                    'first_name': 'Collab',
                    'last_name': 'User'
                }
            )

            # Create test organization
            org, _ = Organization.objects.get_or_create(
                name='Test Organization'
            )

            # Create test management area
            ma, _ = ManagementArea.objects.get_or_create(
                name='Test Management Area',
                defaults={
                    'countries': 'US',
                }
            )

            # Create test assessment
            assessment, created = Assessment.objects.get_or_create(
                name='TestAssessment',
                year=2024,
                defaults={
                    'person_responsible': admin_user,
                    'organization': org,
                    'management_area': ma,
                }
            )

            if created:
                # Create admin collaborator for the assessment
                Collaborator.objects.create(
                    assessment=assessment,
                    user=admin_user,
                    role=Collaborator.ADMIN
                )

            log(f"✓ Created test users: {admin_user.email}, {collab_user.email}")
            log(f"✓ Created test assessment: {assessment.name}")
            log("")

            # Test Scenario 1: Add CollabUser to TestAssessment
            log("=" * 80)
            log("SCENARIO 1: Add CollabUser to TestAssessment as OBSERVER")
            log("=" * 80)
            log("")

            mail.outbox = []  # Clear email outbox

            collaborator = Collaborator.objects.create(
                assessment=assessment,
                user=collab_user,
                role=Collaborator.OBSERVER
            )

            log(f"Action: Created collaborator (role: {collaborator.get_role_display()})")
            log(f"Emails sent: {len(mail.outbox)}")
            log("")

            for i, email in enumerate(mail.outbox, 1):
                log(f"--- Email {i} ---")
                log(f"To: {', '.join(email.to)}")
                log(f"Subject: {email.subject}")
                log(f"Body:\n{email.body}")
                log("")

            # Test Scenario 2: Change CollabUser role to ADMIN
            log("=" * 80)
            log("SCENARIO 2: Change CollabUser role to ADMIN on TestAssessment")
            log("=" * 80)
            log("")

            mail.outbox = []  # Clear email outbox

            collaborator.role = Collaborator.ADMIN
            collaborator.save()

            log(f"Action: Updated collaborator role to {collaborator.get_role_display()}")
            log(f"Emails sent: {len(mail.outbox)}")
            log("")

            for i, email in enumerate(mail.outbox, 1):
                log(f"--- Email {i} ---")
                log(f"To: {', '.join(email.to)}")
                log(f"Subject: {email.subject}")
                log(f"Body:\n{email.body}")
                log("")

            # Test Scenario 3: Remove CollabUser from TestAssessment
            log("=" * 80)
            log("SCENARIO 3: Remove CollabUser from TestAssessment")
            log("=" * 80)
            log("")

            mail.outbox = []  # Clear email outbox

            collaborator.delete()

            log(f"Action: Deleted collaborator")
            log(f"Emails sent: {len(mail.outbox)}")
            log("")

            for i, email in enumerate(mail.outbox, 1):
                log(f"--- Email {i} ---")
                log(f"To: {', '.join(email.to)}")
                log(f"Subject: {email.subject}")
                log(f"Body:\n{email.body}")
                log("")

            # Cleanup
            log("=" * 80)
            log("CLEANUP")
            log("=" * 80)
            log("")
            log("Deleting test data...")

            # Delete in correct order to avoid foreign key constraints
            assessment_id = assessment.id
            assessment_name = assessment.name
            org_name = org.name
            ma_name = ma.name

            # Delete assessment (cascades to collaborators)
            assessment.delete()
            log(f"✓ Deleted assessment: {assessment_name} (ID: {assessment_id})")

            # Delete users
            admin_user.delete()
            log(f"✓ Deleted user: AdminUser")

            collab_user.delete()
            log(f"✓ Deleted user: CollabUser")

            # Delete organization
            org.delete()
            log(f"✓ Deleted organization: {org_name}")

            # Delete management area
            ma.delete()
            log(f"✓ Deleted management area: {ma_name}")

            log("")
            log("All test data cleaned up successfully.")
            log("")

            # Write output to file
            log("=" * 80)
            log(f"WRITING OUTPUT TO: {output_file}")
            log("=" * 80)

            with open(output_file, 'w') as f:
                f.write(output_buffer.getvalue())

            self.stdout.write(self.style.SUCCESS(f'\n✓ Test complete! Output saved to {output_file}'))
            self.stdout.write(self.style.SUCCESS('✓ All test data cleaned up'))
