from django.contrib import admin
from django.db import models
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from ckeditor.widgets import CKEditorWidget

from .models import ImmunizationSchedule, ImmunizationMaster


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}


@admin.register(ImmunizationMaster)
class ImmunizationMasterAdmin(RichTextAdmin):
    list_display = ('name', 'interval_value', 'interval_unit', 'is_active')
    list_filter = ('interval_unit', 'is_active')
    search_fields = ('name',)
    change_list_template = 'admin/immunizationmaster_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('import/', self.admin_site.admin_view(self.import_view), name='immunization_master_import'),
        ]
        return custom + urls

    def import_view(self, request):
        if request.method == 'POST':
            file = request.FILES.get('file')
            if not file:
                messages.error(request, 'Please choose an Excel (.xlsx) file to upload.')
                return redirect('admin:immunization_master_import')

            created, updated, skipped = 0, 0, 0
            try:
                # Try to read via openpyxl
                from openpyxl import load_workbook
                wb = load_workbook(filename=file, data_only=True)
                ws = wb.active
                # Expect headers similar to: Minimum Target Age of Child, Type of Vaccine, Dosage, Route of Administration
                # We'll use Age and Vaccine columns
                headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
                # Find column indexes robustly
                def find_idx(names):
                    for i, h in enumerate(headers):
                        if h and str(h).strip().lower() in names:
                            return i
                    return None
                age_idx = find_idx({'minimum target age of child', 'age', 'recommended age'})
                vaccine_idx = find_idx({'type of vaccine', 'vaccine', 'vaccine name'})
                desc_idx = find_idx({'description', 'notes'})

                if age_idx is None or vaccine_idx is None:
                    messages.error(request, 'Could not detect required columns (Age, Vaccine) in the uploaded sheet.')
                    return redirect('admin:immunization_master_import')

                def parse_interval(text: str):
                    if not text:
                        return 0, 'days'
                    t = str(text).strip().lower()
                    if t in {'at birth', 'birth', 'newborn'}:
                        return 0, 'days'
                    # e.g. "6 weeks", "10 weeks"
                    import re
                    m = re.match(r"^(\d+)\s*week", t)
                    if m:
                        return int(m.group(1)), 'weeks'
                    m = re.match(r"^(\d+)\s*month", t)
                    if m:
                        return int(m.group(1)), 'months'
                    m = re.match(r"^(\d+)\s*day", t)
                    if m:
                        return int(m.group(1)), 'days'
                    # some entries like '9 years' (HPV) — keep but convert to months to avoid huge days
                    m = re.match(r"^(\d+)\s*year", t)
                    if m:
                        # represent years as months to fit our unit choices
                        return int(m.group(1)) * 12, 'months'
                    # default fallback
                    return 0, 'days'

                for row in ws.iter_rows(min_row=2):
                    age_text = row[age_idx].value if age_idx is not None else ''
                    vaccine_name = row[vaccine_idx].value if vaccine_idx is not None else ''
                    description = row[desc_idx].value if desc_idx is not None else ''
                    if not vaccine_name:
                        skipped += 1
                        continue
                    interval_value, interval_unit = parse_interval(age_text)
                    obj, created_flag = ImmunizationMaster.objects.update_or_create(
                        name=str(vaccine_name).strip(),
                        defaults={
                            'description': description or '',
                            'interval_value': max(0, int(interval_value)),
                            'interval_unit': interval_unit,
                            'is_active': True,
                        }
                    )
                    if created_flag:
                        created += 1
                    else:
                        updated += 1

                messages.success(request, f'Import completed: {created} created, {updated} updated, {skipped} skipped.')
                return redirect('admin:immunization_immunizationmaster_changelist')
            except ImportError:
                messages.error(request, 'openpyxl is required to import .xlsx files. Please install it on the server.')
                return redirect('admin:immunization_master_import')
            except Exception as e:
                messages.error(request, f'Import failed: {e}')
                return redirect('admin:immunization_master_import')

        # GET: show upload form
        return render(request, 'admin/immunization_import.html', {
            'title': 'Import Immunization Schedule (Excel)',
        })


@admin.register(ImmunizationSchedule)
class ImmunizationScheduleAdmin(RichTextAdmin):
    list_display = ('baby', 'vaccine_name', 'scheduled_date', 'status', 'date_completed')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('baby__name', 'vaccine_name')
