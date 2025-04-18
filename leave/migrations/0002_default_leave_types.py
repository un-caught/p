from django.db import migrations

def create_default_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leave', 'LeaveType')
    
    # Create default leave types
    leave_types = [
        {
            'name': 'Annual Leave',
            'description': 'Regular annual leave entitlement',
            'max_days': 15
        },
        {
            'name': 'Sick Leave',
            'description': 'Leave due to illness or medical appointments',
            'max_days': 10
        },
        {
            'name': 'Casual Leave',
            'description': 'Short-term leave for personal matters',
            'max_days': 5
        },
        {
            'name': 'Exam/Study Leave',
            'description': 'Leave for educational purposes',
            'max_days': 5
        },
        {
            'name': 'Compassionate Leave',
            'description': 'Leave for bereavement or family emergencies',
            'max_days': 3
        },
        {
            'name': 'Maternity Leave',
            'description': 'Leave for childbirth and childcare',
            'max_days': 90
        }
    ]
    
    for leave_type in leave_types:
        LeaveType.objects.get_or_create(
            name=leave_type['name'],
            defaults={
                'description': leave_type['description'],
                'max_days': leave_type['max_days']
            }
        )

def reverse_default_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leave', 'LeaveType')
    LeaveType.objects.filter(
        name__in=[
            'Annual Leave',
            'Sick Leave',
            'Casual Leave',
            'Exam/Study Leave',
            'Compassionate Leave',
            'Maternity Leave'
        ]
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_leave_types, reverse_default_leave_types),
    ]
