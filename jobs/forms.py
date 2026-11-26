from django import forms
from django.utils import timezone

from .models import Job

JOB_FIELDS = [
    "title",
    "category",
    "description",
    "location",
    "work_date",
    "work_schedule",
    "employment_type",
    "duration",
    "estimated_payment",
    "max_payment",
    "pay_period",
    "number_of_workers",
    "requirements",
    "experience",
    "industry",
    "how_to_apply",
]


class JobRulesMixin:
    """Validation shared by the Post a Job page and the JSON API.

    Required vs optional comes straight from the model: nothing is filled in on the
    poster's behalf, so every non-blank field has to be provided.
    """

    def clean_work_date(self):
        work_date = self.cleaned_data["work_date"]
        # Editing an old post must not force a new date; a new/reposted job may not be in the past.
        unchanged = self.instance.pk and work_date == self.instance.work_date
        if work_date < timezone.localdate() and not unchanged:
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

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("estimated_payment"), cleaned.get("max_payment")
        if low is not None and high is not None and high < low:
            self.add_error(
                "max_payment", "Max payment can't be lower than the estimated payment."
            )
        return cleaned


class JobForm(JobRulesMixin, forms.ModelForm):
    """The server-rendered Post a Job form."""

    confirm = forms.BooleanField(
        label="I confirm the job details are accurate",
        error_messages={"required": "Please confirm the job details are accurate."},
    )

    class Meta:
        model = Job
        fields = JOB_FIELDS
        labels = {
            "title": "Job title",
            "category": "Kind of work",
            "description": "What needs to be done",
            "location": "Location",
            "work_date": "Work date",
            "work_schedule": "Time of day",
            "employment_type": "Employment type",
            "duration": "How long",
            "estimated_payment": "Pay (pesos)",
            "max_payment": "Highest pay (pesos)",
            "pay_period": "Paid per",
            "number_of_workers": "Workers needed",
            "requirements": "Requirements",
            "experience": "Experience",
            "industry": "Industry",
            "how_to_apply": "How to apply",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Weekend house cleaning"}),
            "description": forms.Textarea(
                attrs={
                    "class": "tall", "rows": 5,
                    "placeholder": "Describe the duties, the size of the home or task, and anything else workers should know.",
                }
            ),
            "location": forms.TextInput(attrs={"placeholder": "Barangay and city, e.g. Ilayang Dupay, Lucena"}),
            "work_date": forms.DateInput(attrs={"type": "date"}),
            "estimated_payment": forms.NumberInput(
                attrs={"placeholder": "e.g. 500", "min": "1", "step": "any"}
            ),
            "max_payment": forms.NumberInput(
                attrs={"placeholder": "e.g. 900", "min": "1", "step": "any"}
            ),
            "number_of_workers": forms.NumberInput(
                attrs={"class": "short", "placeholder": "e.g. 1", "min": "1"}
            ),
            "requirements": forms.Textarea(
                attrs={
                    "class": "medium", "rows": 4,
                    "placeholder": "One per line, e.g. Must be 18+",
                }
            ),
            "experience": forms.TextInput(
                attrs={"placeholder": "e.g. No formal experience"}
            ),
            "industry": forms.TextInput(attrs={"placeholder": "e.g. Cleaning, Household"}),
            "how_to_apply": forms.Textarea(
                attrs={
                    "class": "medium", "rows": 4,
                    "placeholder": "Tell applicants what to prepare or who to contact",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        # A "Select ..." placeholder for each dropdown (empty value => "required" error).
        for name, text in (
            ("category", "Select category"),
            ("work_schedule", "Select schedule"),
            ("employment_type", "Select employment type"),
            ("duration", "Select duration"),
            ("pay_period", "Select pay period"),
        ):
            field = self.fields[name]
            field.choices = [("", text)] + [c for c in field.choices if c[0] != ""]
        # Shared control styles (see static/css/base.css).
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            base = "select" if isinstance(widget, forms.Select) else (
                "textarea" if isinstance(widget, forms.Textarea) else "input"
            )
            widget.attrs["class"] = f'{base} {widget.attrs.get("class", "")}'.strip()
        self.fields["work_date"].widget.attrs["min"] = timezone.localdate().isoformat()
