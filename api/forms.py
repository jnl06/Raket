from django import forms
from django.forms.models import model_to_dict

from jobs.forms import JOB_FIELDS, JobRulesMixin
from jobs.models import Job


class JobWriteForm(JobRulesMixin, forms.ModelForm):
    """Validates job create/edit payloads (same rules as the Post a Job page)."""

    class Meta:
        model = Job
        fields = JOB_FIELDS

    @classmethod
    def for_payload(cls, payload, instance=None):
        """Build a form; on edit, missing keys keep their current values (PATCH semantics)."""
        data = dict(payload)
        if instance is not None:
            data = {**model_to_dict(instance, fields=JOB_FIELDS), **data}
        return cls(data=data, instance=instance)
