# Audit System Documentation

## Overview

The audit system provides comprehensive activity logging for all major system actions, capturing full traceability with date, time, and user stamps. All logs are accessible only through the Django Admin Panel, not in staff dashboards.

## What Gets Logged Automatically

The system automatically captures the following for every create, update, or delete action:

- **Date & Time**: Server local time when the action occurred
- **User Information**: Staff name, Staff ID, and Hospital/Clinic ID
- **Action Details**: Type (create/update/delete/complete), affected module/model, and description
- **Object Reference**: Link to the specific record that was modified

### Monitored Apps & Models

The following modules are automatically monitored:
- **Immunization**: All immunization records and schedules
- **Patients**: Patient registration, profile updates, and health records
- **Casefiles**: Case file creation, updates, and status changes
- **Appointments**: Appointment scheduling, updates, and completions

## Completion Event Detection

The system automatically detects completion events by monitoring status field changes:
- When a status changes to values like 'completed', 'done', 'finished', 'administered'
- When boolean completion flags change from False to True

## Manual Completion Logging

For explicit completion events (e.g., "immunization administered", "test completed"), use the utility function:

```python
from audit.utils import log_completion

# Example: Log immunization completion
log_completion(
    action_type='complete',
    module='immunization',
    model='ImmunizationRecord',
    description='Immunization administered successfully',
    object_id=immunization_record.id
)

# Example: Log lab test completion
log_completion(
    action_type='complete',
    module='laboratory',
    model='LabTest',
    description='Lab test results recorded',
    object_id=lab_test.id
)
```

## Admin Panel Access

### Viewing Activity Logs

1. Navigate to Django Admin Panel
2. Look for "Activity Logs" under the "Audit" section
3. Use filters to search by:
   - Action type (create/update/delete/complete)
   - Module (immunization, patients, etc.)
   - Staff ID or Hospital/Clinic ID
   - Date range

### Permissions

- Only superusers can view activity logs by default
- Additional users can be granted `audit.view_activitylog` permission
- Regular staff users cannot access audit logs

## Data Captured

Each activity log entry includes:

| Field | Description |
|-------|-------------|
| Action Type | create, update, delete, complete |
| Module | App name (immunization, patients, etc.) |
| Model | Specific model name |
| Action Description | Human-readable description of the action |
| Staff Name | Full name of the staff member |
| Staff ID | Unique staff identifier |
| Hospital/Clinic ID | Facility identifier |
| Action Date | Date when action occurred |
| Action Time | Time when action occurred |
| Object ID | ID of the affected record |
| Content Type | Django content type of the affected model |

## Security & Privacy

- Audit logs are stored securely in the database
- No sensitive patient data is logged directly
- Only metadata and action descriptions are captured
- Logs are never displayed in staff-facing interfaces
- Access is restricted to authorized admin users only

## Technical Implementation

The audit system uses:
- **Django Signals**: Automatic capture of model changes
- **Middleware**: User context capture for each request
- **Thread-local Storage**: Secure user context passing
- **Generic Foreign Keys**: Flexible object references
- **Admin Integration**: Seamless admin panel integration

## Troubleshooting

If logs are not appearing:
1. Ensure the audit app is in INSTALLED_APPS
2. Verify AuditMiddleware is in MIDDLEWARE settings
3. Check that migrations have been applied: `python manage.py migrate audit`
4. Confirm the user performing actions is authenticated

For manual completion logging issues:
- Ensure the utility function is imported correctly
- Verify the user context is available (authenticated request)
- Check that the object_id exists and is valid