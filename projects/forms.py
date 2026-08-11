from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Project, ProjectMember, Task

User = get_user_model()


class DateInput(forms.DateInput):
    input_type = "date"


def project_user_queryset(project):
    """Users who may work on a project: members, owner and supervisor."""
    user_ids = set(project.members.values_list("user_id", flat=True))
    user_ids.add(project.owner_id)
    user_ids.add(project.supervisor_id)
    return User.objects.filter(id__in=user_ids)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("title", "description", "supervisor", "status", "start_date", "due_date")
        widgets = {
            "start_date": DateInput(),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supervisor"].queryset = User.objects.filter(role=User.Role.SUPERVISOR)
        self.fields["status"].required = False
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save Project", css_class="btn btn-primary"))


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "description", "assignee", "priority", "status", "due_date")
        widgets = {
            "due_date": DateInput(),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["assignee"].queryset = project_user_queryset(project)
        self.fields["priority"].required = False
        self.fields["status"].required = False
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Save Task", css_class="btn btn-primary"))


class ProjectMemberForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ("user", "role")

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            member_ids = project.members.values_list("user_id", flat=True)
            self.fields["user"].queryset = User.objects.filter(role=User.Role.STUDENT).exclude(id__in=member_ids)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", "Add Member", css_class="btn btn-primary"))
