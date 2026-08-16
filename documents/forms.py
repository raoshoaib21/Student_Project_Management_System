from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Document

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "md",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "csv",
    "zip",
    "png",
    "jpg",
    "jpeg",
    "gif",
}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("file", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].label = "Description (optional)"
        if self.instance.pk:
            self.fields["file"].required = False
            submit_label = "Update Document"
        else:
            submit_label = "Upload Document"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.add_input(Submit("submit", submit_label, css_class="btn btn-primary"))

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            return file
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(f"File type '.{ext}' is not allowed.")
        if file.size > MAX_SIZE:
            raise forms.ValidationError("File size must be 10 MB or less.")
        return file
