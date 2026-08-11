from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Feedback, ProgressReport


class ProgressReportForm(forms.ModelForm):
    class Meta:
        model = ProgressReport
        fields = ("week_number", "summary", "achievements", "next_week_plan", "blockers")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save Report", css_class="btn btn-primary"))


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
