from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import StudentProfile, SupervisorProfile, User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    registration_number = forms.CharField(max_length=50, required=False, label="Registration number")
    department = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "registration_number",
            "department",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Create Account", css_class="btn btn-primary w-100"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = True
        user.is_email_verified = True
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                registration_number=self.cleaned_data.get("registration_number", ""),
                department=self.cleaned_data.get("department", ""),
            )
        return user


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
