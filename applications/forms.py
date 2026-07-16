from django import forms
from .models import JobApplication, Company

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website', 'industry', 'location']

class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            'company_name', 'job_title', 'job_location',
            'internship_type', 'deadline', 'status',
            'salary', 'notes', 'interview_date', 'follow_up_interval_days'
        ]
        labels = {
            'follow_up_interval_days': 'Follow-up reminder interval (days)',
        }
        help_texts = {
            'follow_up_interval_days': 'Defaults to 7 days. Rejected applications do not create follow-up reminders.',
        }
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'interview_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'follow_up_interval_days': forms.NumberInput(attrs={'min': 1, 'max': 60, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_follow_up_interval_days(self):
        days = self.cleaned_data['follow_up_interval_days']
        if days < 1 or days > 60:
            raise forms.ValidationError('Choose a reminder interval between 1 and 60 days.')
        return days
