"""
Management command to test email verification login scenarios.

This command creates test users with various email case combinations and
tests the IExactLoginSerializer to ensure it handles case-insensitive
email verification correctly while matching the original LoginSerializer behavior.

Usage:
    python manage.py test_email_verification
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from allauth.account.models import EmailAddress
from api.resources.authuser import IExactLoginSerializer


User = get_user_model()


class Command(BaseCommand):
    help = "Test email verification with various case scenarios"

    def __init__(self):
        super().__init__()
        self.test_users = []
        self.passed = 0
        self.failed = 0

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('  Email Verification Test Suite - IExactLoginSerializer'))
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))

        # Clean up any existing test users
        self.cleanup_test_users()

        # Run test scenarios
        self.test_case_mismatch_user_uppercase_ea_lowercase()
        self.test_case_mismatch_user_lowercase_ea_uppercase()
        self.test_mixed_case_variations()
        self.test_exact_match()
        self.test_unverified_email()
        self.test_missing_emailaddress_record()
        self.test_user_with_no_email()
        self.test_multiple_emailaddress_records()
        self.test_inactive_user_email_check()
        self.test_emailaddress_different_from_user_email()

        # Clean up after tests
        self.cleanup_test_users()

        # Summary
        self.stdout.write('\n' + '=' * 70)
        total = self.passed + self.failed
        if self.failed == 0:
            self.stdout.write(self.style.SUCCESS(
                f'✓ ALL {total} TESTS PASSED'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'✗ {self.failed} of {total} tests FAILED'
            ))
        self.stdout.write('=' * 70 + '\n')

    def cleanup_test_users(self):
        """Remove test users created by this script"""
        test_usernames = [f'testuser_{i}' for i in range(1, 20)]
        deleted = User.objects.filter(username__in=test_usernames).delete()
        if deleted[0] > 0:
            self.stdout.write(f"Cleaned up {deleted[0]} test user(s)\n")

    def create_test_user(self, username, user_email, emailaddress_email=None,
                        verified=True, is_active=True):
        """Create a test user with specific email configurations"""
        # Create user
        user = User.objects.create_user(
            username=username,
            email=user_email,
            password='testpass123',
            first_name='Test',
            last_name='User',
            is_active=is_active
        )
        self.test_users.append(user)

        # Remove auto-created EmailAddress (from signals)
        EmailAddress.objects.filter(user=user).delete()

        # Create EmailAddress with specific casing if provided
        if emailaddress_email is not None:
            EmailAddress.objects.create(
                user=user,
                email=emailaddress_email,
                verified=verified,
                primary=True
            )

        return user

    def test_serializer(self, user, test_name, should_pass=True):
        """Test the serializer with a user"""
        serializer = IExactLoginSerializer()
        try:
            serializer.validate_email_verification_status(user, email=user.email)
            if should_pass:
                self.stdout.write(self.style.SUCCESS(f'  ✓ PASS: {test_name}'))
                self.passed += 1
                return True
            else:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ FAIL: {test_name} - Expected failure but passed'
                ))
                self.failed += 1
                return False
        except Exception as e:
            if not should_pass:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ PASS: {test_name} - Correctly rejected'
                ))
                self.stdout.write(f'         Error: {str(e)}')
                self.passed += 1
                return True
            else:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ FAIL: {test_name} - Unexpected error: {str(e)}'
                ))
                self.failed += 1
                return False

    def print_test_header(self, title):
        """Print a formatted test header"""
        self.stdout.write(f'\n{"-" * 70}')
        self.stdout.write(self.style.WARNING(f'{title}'))
        self.stdout.write('-' * 70)

    def print_user_details(self, user):
        """Print user and EmailAddress details"""
        self.stdout.write(f'  User.email: "{user.email}"')
        self.stdout.write(f'  User.is_active: {user.is_active}')
        ea_list = EmailAddress.objects.filter(user=user)
        if ea_list.exists():
            for ea in ea_list:
                self.stdout.write(
                    f'  EmailAddress: "{ea.email}" '
                    f'(verified={ea.verified}, primary={ea.primary})'
                )
        else:
            self.stdout.write('  EmailAddress: None')

    def test_case_mismatch_user_uppercase_ea_lowercase(self):
        """Test: User.email='Test@Example.com', EmailAddress.email='test@example.com'"""
        self.print_test_header('Test 1: Case Mismatch - User uppercase, EmailAddress lowercase')

        user = self.create_test_user(
            username='testuser_1',
            user_email='Test@Example1.com',
            emailaddress_email='test@example1.com',
            verified=True
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login with case mismatch (upper->lower)', should_pass=True)

    def test_case_mismatch_user_lowercase_ea_uppercase(self):
        """Test: User.email='test@example.com', EmailAddress.email='TEST@EXAMPLE.COM'"""
        self.print_test_header('Test 2: Case Mismatch - User lowercase, EmailAddress uppercase')

        user = self.create_test_user(
            username='testuser_2',
            user_email='test@example2.com',
            emailaddress_email='TEST@EXAMPLE2.COM',
            verified=True
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login with case mismatch (lower->upper)', should_pass=True)

    def test_mixed_case_variations(self):
        """Test: Both have mixed case differently"""
        self.print_test_header('Test 3: Mixed Case Variations')

        user = self.create_test_user(
            username='testuser_3',
            user_email='TeSt@ExAmPlE3.cOm',
            emailaddress_email='tEsT@eXaMpLe3.CoM',
            verified=True
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login with mixed case variations', should_pass=True)

    def test_exact_match(self):
        """Test: Exact match (control test)"""
        self.print_test_header('Test 4: Exact Match (Control Test)')

        user = self.create_test_user(
            username='testuser_4',
            user_email='test@example4.com',
            emailaddress_email='test@example4.com',
            verified=True
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login with exact match', should_pass=True)

    def test_unverified_email(self):
        """Test: EmailAddress exists but verified=False"""
        self.print_test_header('Test 5: Unverified Email (Should Fail)')

        user = self.create_test_user(
            username='testuser_5',
            user_email='test@example5.com',
            emailaddress_email='test@example5.com',
            verified=False
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login with unverified email', should_pass=False)

    def test_missing_emailaddress_record(self):
        """Test: User exists but no EmailAddress record"""
        self.print_test_header('Test 6: Missing EmailAddress Record (Should Fail)')

        user = self.create_test_user(
            username='testuser_6',
            user_email='test@example6.com',
            emailaddress_email=None,  # Don't create EmailAddress
        )
        self.print_user_details(user)
        self.test_serializer(user, 'Login without EmailAddress record', should_pass=False)

    def test_user_with_no_email(self):
        """Test: User with empty email field"""
        self.print_test_header('Test 7: User With No Email (Edge Case)')

        user = self.create_test_user(
            username='testuser_7',
            user_email='',  # Empty email
            emailaddress_email=None,
        )
        self.print_user_details(user)
        # With empty email, the filter will not find anything, so should fail
        self.test_serializer(user, 'Login with empty user.email', should_pass=False)

    def test_multiple_emailaddress_records(self):
        """Test: User with multiple email addresses"""
        self.print_test_header('Test 8: Multiple EmailAddress Records')

        user = self.create_test_user(
            username='testuser_8',
            user_email='PRIMARY@EXAMPLE8.COM',  # uppercase
            emailaddress_email='primary@example8.com',  # lowercase, verified
            verified=True
        )

        # Add a secondary email (unverified)
        EmailAddress.objects.create(
            user=user,
            email='secondary@example8.com',
            verified=False,
            primary=False
        )

        # Add a third email (verified)
        EmailAddress.objects.create(
            user=user,
            email='TERTIARY@EXAMPLE8.COM',
            verified=True,
            primary=False
        )

        self.print_user_details(user)
        # Should pass because primary email (case-insensitive match) is verified
        self.test_serializer(user, 'Login with primary (case mismatch)', should_pass=True)

    def test_inactive_user_email_check(self):
        """Test: Inactive user - email verification should still pass"""
        self.print_test_header('Test 9: Inactive User (Email Check Only)')
        self.stdout.write('  NOTE: is_active check happens in parent validate_auth_user_status()')

        user = self.create_test_user(
            username='testuser_9',
            user_email='test@example9.com',
            emailaddress_email='test@example9.com',
            verified=True,
            is_active=False  # Inactive user
        )
        self.print_user_details(user)
        # Our method should NOT check is_active (that's validate_auth_user_status's job)
        # Since email IS verified, our check should pass
        self.test_serializer(
            user,
            'Email verification check ignores is_active (handled elsewhere)',
            should_pass=True  # Should pass OUR check (email is verified)
        )

    def test_emailaddress_different_from_user_email(self):
        """Test: EmailAddress.email doesn't match User.email at all"""
        self.print_test_header('Test 10: EmailAddress != User.email (Should Fail)')

        user = self.create_test_user(
            username='testuser_10',
            user_email='primary@example10.com',
            emailaddress_email='different@example10.com',  # Completely different
            verified=True
        )
        self.print_user_details(user)
        # Should fail: we look for user.email in EmailAddress, won't find it
        self.test_serializer(
            user,
            'User.email != any EmailAddress.email',
            should_pass=False
        )
