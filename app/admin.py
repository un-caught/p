from django.contrib import admin
from .models import Member, SafetyPrecaution, WorkLocationIsolation, PersonalSafety, Hazards, PTWForm, NHISForm # Import Member

# Custom Admin for Member model
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'email', 'phone', 'is_hod_manager', 'is_relief_eligible')
    list_filter = ('is_hod_manager', 'is_relief_eligible')
    list_editable = ('is_hod_manager', 'is_relief_eligible') # Allow editing directly in the list view
    search_fields = ('name', 'email', 'user__username') # Search by related User fields too

# Register your models here.
admin.site.register(Member, MemberAdmin) # Register Member with custom admin
admin.site.register(SafetyPrecaution)
admin.site.register(WorkLocationIsolation)
admin.site.register(PersonalSafety)
admin.site.register(Hazards)
admin.site.register(PTWForm)
admin.site.register(NHISForm)
