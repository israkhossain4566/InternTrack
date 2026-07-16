from django.contrib import admin
from .models import Company, JobApplication

admin.site.register(Company)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'job_title',
        'company_name',
        'user',
        'status',
        'follow_up_due_date',
        'follow_up_interval_days',
    )
    list_filter = ('status', 'follow_up_due_date')
    search_fields = ('job_title', 'company_name', 'user__username')
