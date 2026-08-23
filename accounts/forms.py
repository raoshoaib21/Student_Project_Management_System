from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import StudentProfile, SupervisorProfile, User


class RememberMeAuthenticationForm(AuthenticationForm):
    remember = forms.BooleanField(required=False, label="Remember me")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Sign in", css_class="btn btn-primary w-100"))


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("registration_number", "department", "course", "level", "phone", "avatar")


class SupervisorProfileForm(forms.ModelForm):
    class Meta:
        model = SupervisorProfile
        fields = ("title", "department", "office", "phone", "avatar")
