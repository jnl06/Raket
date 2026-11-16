from datetime import date

from django import forms

from .models import Job


class JobForm(forms.ModelForm):
    confirm = forms.BooleanField(
        label="I confirm the job details are accurate",
        error_messages={"required": "Please confirm the job details are accurate."},
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "category",
            "description",
            "location",
            "work_date",
            "work_schedule",
            "estimated_payment",
            "number_of_workers",
            "requirements",
        ]
        labels = {
            "title": "Job Title",
            "category": "Job Category",
            "description": "Job Description",
            "location": "Location",
            "work_date": "Work Date",
            "work_schedule": "Work Schedule",
            "estimated_payment": "Estimated Payment (Pesos)",
            "number_of_workers": "Number of Workers",
            "requirements": "Requirements / Skills",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. House Cleaning"}),
            "description": forms.Textarea(
                attrs={
                    "class": "tall",
                    "placeholder": "Describe the job, duties, and any additional information...",
                }
            ),
            "location": forms.TextInput(attrs={"placeholder": "City / Barangay"}),
            "work_date": forms.DateInput(attrs={"type": "date"}),
            "estimated_payment": forms.NumberInput(
                attrs={"placeholder": "e.g. 500", "min": "1", "step": "any"}
            ),
            "number_of_workers": forms.NumberInput(
                attrs={"class": "short", "placeholder": "e.g. 1", "min": "1"}
            ),
            "requirements": forms.Textarea(
                attrs={
                    "class": "medium",
                    "placeholder": "e.g. Must be 18+, with cleaning experience",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        # Placeholder option for the two dropdowns (empty value => "required" error).
        self.fields["category"].choices = [("", "Select category")] + list(
            Job.Category.choices
        )
        self.fields["work_schedule"].choices = [("", "Select schedule")] + list(
            Job.Schedule.choices
        )
        self.fields["work_date"].widget.attrs["min"] = date.today().isoformat()
        self.fields["requirements"].required = False

    def clean_work_date(self):
        work_date = self.cleaned_data["work_date"]
        if work_date < date.today():
            raise forms.ValidationError("Work date can't be in the past.")
        return work_date

    def clean_estimated_payment(self):
        payment = self.cleaned_data["estimated_payment"]
        if payment <= 0:
            raise forms.ValidationError("Payment must be greater than zero.")
        return payment

    def clean_number_of_workers(self):
        workers = self.cleaned_data["number_of_workers"]
        if workers < 1:
            raise forms.ValidationError("At least 1 worker is needed.")
        return workers
