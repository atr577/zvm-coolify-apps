"""
Django management command to create a user for testing.
Since PAM doesn't work in Docker, use this to create Django users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a Django user (useful when PAM is not available)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username')
        parser.add_argument('password', type=str, help='Password')
        parser.add_argument('--superuser', action='store_true', help='Create as superuser')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        is_superuser = options.get('superuser', False)

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists.'))
            user = User.objects.get(username=username)
            user.set_password(password)
            if is_superuser:
                user.is_superuser = True
                user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated user "{username}" password.'))
        else:
            if is_superuser:
                user = User.objects.create_superuser(username=username, password=password)
            else:
                user = User.objects.create_user(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))
