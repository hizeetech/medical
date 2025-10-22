from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from datetime import timedelta

from patients.models import BabyProfile
from immunization.models import ImmunizationMaster, ImmunizationSchedule


class Command(BaseCommand):
    help = (
        "Backfill or regenerate ImmunizationSchedule entries for existing babies "
        "based on active ImmunizationMaster records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--baby-id",
            type=int,
            default=None,
            help="Only process a single BabyProfile by its ID.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help=(
                "Delete existing DUE schedules for processed babies and recreate "
                "from the master list. DONE/MISSED schedules are preserved."
            ),
        )

    def _due_date(self, dob, master: ImmunizationMaster):
        if master.interval_unit == "days":
            return dob + timedelta(days=master.interval_value)
        elif master.interval_unit == "weeks":
            return dob + timedelta(weeks=master.interval_value)
        elif master.interval_unit == "months":
            # Approximate months as 30 days to match signals implementation
            return dob + timedelta(days=master.interval_value * 30)
        # Fallback
        return dob

    def handle(self, *args, **options):
        baby_id = options.get("baby_id")
        dry_run = options.get("dry_run")
        recreate = options.get("recreate")

        masters = list(ImmunizationMaster.objects.filter(is_active=True))
        if not masters:
            raise CommandError("No active ImmunizationMaster entries found.")

        babies_qs = BabyProfile.objects.all()
        if baby_id:
            babies_qs = babies_qs.filter(id=baby_id)
            if not babies_qs.exists():
                raise CommandError(f"BabyProfile with id={baby_id} not found.")

        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_deleted = 0

        self.stdout.write(self.style.NOTICE(
            f"Processing {babies_qs.count()} baby(ies) • masters={len(masters)} • "
            f"dry_run={dry_run} • recreate={recreate}"
        ))

        with transaction.atomic():
            for baby in babies_qs.iterator():
                if recreate:
                    # Delete only DUE schedules; retain actual history
                    qs_due = ImmunizationSchedule.objects.filter(baby=baby, status="DUE")
                    deleted_count = qs_due.count()
                    total_deleted += deleted_count
                    if not dry_run:
                        qs_due.delete()

                # Build per-baby index of existing schedules by vaccine name
                existing = (
                    ImmunizationSchedule.objects.filter(baby=baby)
                    .values("id", "vaccine_name", "status", "scheduled_date", "notes")
                )
                by_vaccine = {}
                for item in existing:
                    by_vaccine.setdefault(item["vaccine_name"], []).append(item)

                for master in masters:
                    due_date = self._due_date(baby.date_of_birth, master)
                    vaccine_name = master.name
                    description = master.description or ""

                    candidates = by_vaccine.get(vaccine_name, [])
                    # Prefer a single updatable DUE schedule if present
                    target = None
                    for c in candidates:
                        if c["status"] == "DUE":
                            target = c
                            break
                    if target is None and candidates:
                        # If only DONE/MISSED exist, we do not create another schedule
                        total_skipped += 1
                        continue

                    if target is None:
                        # Create new schedule
                        if not dry_run:
                            ImmunizationSchedule.objects.create(
                                baby=baby,
                                vaccine_name=vaccine_name,
                                scheduled_date=due_date,
                                status="DUE",
                                notes=description,
                            )
                        total_created += 1
                    else:
                        # Update the existing DUE schedule if details changed
                        needs_update = False
                        if target["scheduled_date"] != due_date:
                            needs_update = True
                        if (target["notes"] or "") != description:
                            needs_update = True

                        if needs_update:
                            if not dry_run:
                                ImmunizationSchedule.objects.filter(id=target["id"]).update(
                                    scheduled_date=due_date,
                                    notes=description,
                                )
                            total_updated += 1
                        else:
                            total_skipped += 1

            if dry_run:
                # Roll back the transaction for dry-run so DB remains unchanged
                raise CommandError(
                    f"Dry-run complete. Created={total_created}, Updated={total_updated}, "
                    f"Deleted={total_deleted}, Skipped={total_skipped}. No changes applied."
                )

        self.stdout.write(self.style.SUCCESS(
            f"Backfill finished. Created={total_created}, Updated={total_updated}, "
            f"Deleted={total_deleted}, Skipped={total_skipped}."
        ))