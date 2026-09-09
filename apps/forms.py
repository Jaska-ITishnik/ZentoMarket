import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.text import slugify

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Eslab qolish")

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget = forms.EmailInput(attrs={
            "class": "field",
            "placeholder": "siz@example.com",
            "autocomplete": "email",
            "autofocus": True,
        })
        self.fields["password"].label = "Parol"
        self.fields["password"].widget.attrs.update({
            "class": "field",
            "placeholder": "Parolingiz",
            "autocomplete": "current-password",
        })

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Ism")
    last_name = forms.CharField(max_length=150, label="Familiya")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=30, label="Telefon")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_options = {
            "first_name": ("Aziza", "given-name"),
            "last_name": ("Karimova", "family-name"),
            "email": ("siz@example.com", "email"),
            "phone": ("+998 90 123 45 67", "tel"),
            "password1": ("Kamida 8 ta belgi", "new-password"),
            "password2": ("Parolni qayta kiriting", "new-password"),
        }
        for name, (placeholder, autocomplete) in field_options.items():
            self.fields[name].widget.attrs.update({
                "class": "field",
                "placeholder": placeholder,
                "autocomplete": autocomplete,
            })
        self.fields["password1"].label = "Parol"
        self.fields["password2"].label = "Parolni tasdiqlang"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email bilan hisob allaqachon mavjud.")
        return email

    def clean_phone(self):
        phone = re.sub(r"[\s()\-]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"\+998\d{9}", phone):
            raise forms.ValidationError("Telefonni +998 90 123 45 67 formatida kiriting.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data["phone"]
        user.role = User.Role.CUSTOMER
        user.username = self._unique_username(user.email)
        if commit:
            user.save()
        return user

    @staticmethod
    def _unique_username(email):
        base = slugify(email.split("@", 1)[0])[:140] or "user"
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base[:140 - len(str(suffix))]}{suffix}"
        return username
