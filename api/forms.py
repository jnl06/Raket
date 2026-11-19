from datetime import date

from django import forms
from django.forms.models import model_to_dict

from jobs.models import Job

JOB_FIELDS = [
    "title",
    "category",
    "description",
    "location",
    "work_date",
    "work_schedule",
    "estimated_payment",
    "max_payment",
    "pay_period",
    "number_of_workers",
    "requirements",
    "employment_type",
    "duration",
    "experience",
    "industry",
    "how_to_apply",
]

OPTIONAL_JOB_FIELDS = [
    "max_payment",
    "pay_period",
    "requirements",
    "employment_type",
    "duration",
    "experience",
    "industry",
    "how_to_apply",
]


class JobWriteForm(forms.ModelForm):
    """Validates job create/edit payloads (same rules as the Post a Job form)."""

    class Meta:
        model = Job
        fields = JOB_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in OPTIONAL_JOB_FIELDS:
            self.fields[name].required = False

    @classmethod
    def for_payload(cls, payload, instance=None):
        """Build a form; on edit, missing keys keep their current values (PATCH semantics)."""
        data = dict(payload)
        if instance is not None:
            data = {**model_to_dict(instance, fields=JOB_FIELDS), **data}
        return cls(data=data, instance=instance)

    def clean_work_date(self):
        work_date = self.cleaned_data["work_date"]
        unchanged = self.instance.pk and work_date == self.instance.work_date
        if work_date < date.today() and not unchanged:
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
            self.add_error("max_payment", "Max payment can't be lower than the estimated payment.")
        return cleaned
