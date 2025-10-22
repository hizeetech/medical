from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from patients.models import MotherProfile


class Command(BaseCommand):
    help = "Backfill MotherProfile fields into related User fields (first_name, last_name, phone_number, avatar)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        updated_users = 0
        processed_profiles = 0

        qs = MotherProfile.objects.select_related('user')
        self.stdout.write(self.style.NOTICE(f"Found {qs.count()} MotherProfile records to process"))

        with transaction.atomic():
            for profile in qs.iterator():
                processed_profiles += 1
                user = profile.user
                if not isinstance(user, User):
                    continue

                fields_to_update = []

                # Phone number
                if profile.phone_number and profile.phone_number != user.phone_number:
                    user.phone_number = profile.phone_number
                    fields_to_update.append('phone_number')

                # Name splitting: first token as first_name, remainder as last_name
                if profile.full_name:
                    parts = profile.full_name.strip().split(' ', 1)
                    first = parts[0] if parts else ''
                    last = parts[1] if len(parts) > 1 else ''
                    if first != user.first_name:
                        user.first_name = first
                        fields_to_update.append('first_name')
                    if last != user.last_name:
                        user.last_name = last
                        fields_to_update.append('last_name')

                # Avatar from profile_picture if user has no avatar yet
                if profile.profile_picture and not user.avatar:
                    user.avatar = profile.profile_picture
                    fields_to_update.append('avatar')

                if fields_to_update:
                    updated_users += 1
                    if dry_run:
                        self.stdout.write(
                            f"[DRY] Would update user {user.id} ({user.email}): {', '.join(fields_to_update)}"
                        )
                    else:
                        user.save(update_fields=fields_to_update)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated user {user.id} ({user.email}): {', '.join(fields_to_update)}"
                            )
                        )

            if dry_run:
                self.stdout.write(self.style.NOTICE("Dry run complete; no changes were saved."))
            else:
                # If anything fails, the atomic block will roll back all changes
                pass

        self.stdout.write(self.style.SUCCESS(
            f"Processed {processed_profiles} profiles; updated {updated_users} users"
        ))