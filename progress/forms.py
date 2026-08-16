from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Feedback, ProgressReport


class ProgressReportForm(forms.ModelForm):
    class Meta:
        model = ProgressReport
        fields = ("week_number", "summary", "achievements", "next_week_plan", "blockers")

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save Report", css_class="btn btn-primary"))

    def clean_week_number(self):
        week = self.cleaned_data.get("week_number")
        if week is not None and self.project is not None:
            existing = ProgressReport.objects.filter(project=self.project, week_number=week)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    f"A report for Week {week} already exists in this project."
                )
        return week


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("content",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].label = "Feedback"
        self.fields["content"].widget = forms.Textarea(attrs={"rows": 3})
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Send Feedback", css_class="btn btn-primary"))
