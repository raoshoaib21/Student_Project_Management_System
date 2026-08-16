from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].widget = forms.Textarea(attrs={"rows": 5})
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Send Message", css_class="btn btn-primary btn-lg w-100"))
