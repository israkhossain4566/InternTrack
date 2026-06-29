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
            'salary', 'notes', 'interview_date'
        ]
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'interview_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'