from django.core.management.base import BaseCommand
from django.db import transaction

from audit.models import ActivityLog


class Command(BaseCommand):
    help = "Backfill domain snapshot fields (mother/baby/vaccine/dates) into ActivityLog entries."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
        parser.add_argument('--limit', type=int, default=1000, help='Max logs to process')

    def handle(self, *args, **options):
        dry = options.get('dry_run', False)
        limit = options.get('limit', 1000)
        qs = ActivityLog.objects.order_by('id')
        processed = 0
        updated = 0
        with transaction.atomic():
            for log in qs.iterator():
                if processed >= limit:
                    break
                processed += 1
                snap = {}
                obj = log.content_object
                try:
                    if obj is None:
                        continue
                    # VaccinationEventLog → schedule
                    if obj.__class__.__name__ == 'VaccinationEventLog' and hasattr(obj, 'schedule') and obj.schedule:
                        obj = obj.schedule
                    if obj.__class__.__name__ == 'ImmunizationSchedule':
                        baby = getattr(obj, 'baby', None)
                        if baby:
                            snap['baby_name'] = getattr(baby, 'name', None)
                            snap['baby_hospital_id'] = getattr(baby, 'hospital_id', None)
                            mother = getattr(baby, 'mother', None)
                            if mother:
                                snap['mother_name'] = getattr(mother, 'full_name', None)
                                snap['mother_member_id'] = getattr(mother, 'member_id', None)
                        snap['vaccine_name'] = getattr(obj, 'vaccine_name', None)
                        snap['scheduled_date'] = getattr(obj, 'scheduled_date', None)
                        snap['completed_date'] = getattr(obj, 'date_completed', None)
                    elif obj.__class__.__name__ == 'BabyProfile':
                        snap['baby_name'] = getattr(obj, 'name', None)
                        snap['baby_hospital_id'] = getattr(obj, 'hospital_id', None)
                        mother = getattr(obj, 'mother', None)
                        if mother:
                            snap['mother_name'] = getattr(mother, 'full_name', None)
                            snap['mother_member_id'] = getattr(mother, 'member_id', None)
                    elif obj.__class__.__name__ == 'MotherProfile':
                        snap['mother_name'] = getattr(obj, 'full_name', None)
                        snap['mother_member_id'] = getattr(obj, 'member_id', None)
                except Exception:
                    continue

                # Apply if any snapshot data
                if snap:
                    dirty = False
                    for k, v in snap.items():
                        if getattr(log, k, None) != v and v is not None:
                            setattr(log, k, v)
                            dirty = True
                    if dirty:
                        updated += 1
                        if not dry:
                            log.save(update_fields=list(snap.keys()))

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} logs; updated {updated} with snapshots"))