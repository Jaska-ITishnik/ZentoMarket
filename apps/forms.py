import re
import uuid

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import models
from django.utils.text import slugify

from .models import Address, DeliveryPoint, Order, User


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


class AddressChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, address):
        parts = [address.city, address.street, address.house_number]
        return f"{address.title}: {', '.join(part for part in parts if part)}"


class DeliveryPointChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, point):
        return f"{point.name} — {point.address}"


class CheckoutForm(forms.Form):
    class AddressMode(models.TextChoices):
        EXISTING = "existing", "Mavjud manzil"
        NEW = "new", "Yangi manzil"

    checkout_token = forms.UUIDField(widget=forms.HiddenInput)
    delivery_type = forms.ChoiceField(
        choices=Order.DeliveryType.choices,
        widget=forms.RadioSelect,
        label="Yetkazib berish usuli",
    )
    address_mode = forms.ChoiceField(
        choices=AddressMode.choices,
        widget=forms.RadioSelect,
        label="Manzil turi",
        required=False,
    )
    address = AddressChoiceField(
        queryset=Address.objects.none(),
        empty_label="Manzilni tanlang",
        required=False,
        label="Saqlangan manzil",
    )
    new_address_title = forms.CharField(max_length=50, required=False, label="Manzil nomi")
    new_city = forms.CharField(max_length=100, required=False, label="Shahar / hudud")
    new_street = forms.CharField(max_length=255, required=False, label="Ko‘cha")
    new_house_number = forms.CharField(max_length=30, required=False, label="Uy / xonadon")
    delivery_point = DeliveryPointChoiceField(
        queryset=DeliveryPoint.objects.none(),
        empty_label="Topshirish punktini tanlang",
        required=False,
        label="Topshirish punkti",
    )
    payment_type = forms.ChoiceField(
        choices=Order.PaymentType.choices,
        widget=forms.RadioSelect,
        label="To‘lov turi",
    )
    phone = forms.CharField(max_length=30, label="Telefon")
    notes = forms.CharField(
        max_length=1000,
        required=False,
        label="Buyurtmaga izoh",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["checkout_token"].initial = uuid.uuid4()
        self.fields["address"].queryset = Address.objects.filter(user=user).order_by("-is_default", "id")
        self.fields["delivery_point"].queryset = DeliveryPoint.objects.filter(is_active=True).order_by("name")

        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "field")
        self.fields["phone"].widget.attrs.update({
            "placeholder": "+998 90 123 45 67",
            "autocomplete": "tel",
        })
        self.fields["new_address_title"].widget.attrs["placeholder"] = "Masalan, Uy"
        self.fields["new_city"].widget.attrs["autocomplete"] = "address-level1"
        self.fields["new_street"].widget.attrs["autocomplete"] = "street-address"

    def clean_phone(self):
        phone = re.sub(r"[\s()\-]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"\+998\d{9}", phone):
            raise forms.ValidationError("Telefonni +998 90 123 45 67 formatida kiriting.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get("delivery_type")

        if delivery_type == Order.DeliveryType.ADDRESS:
            address_mode = cleaned_data.get("address_mode")
            if address_mode == self.AddressMode.EXISTING:
                if not cleaned_data.get("address"):
                    self.add_error("address", "Saqlangan manzilni tanlang.")
            elif address_mode == self.AddressMode.NEW:
                required_fields = {
                    "new_address_title": "Manzil nomini kiriting.",
                    "new_city": "Shahar yoki hududni kiriting.",
                    "new_street": "Ko‘chani kiriting.",
                }
                for field_name, message in required_fields.items():
                    if not cleaned_data.get(field_name):
                        self.add_error(field_name, message)
            else:
                self.add_error("address_mode", "Mavjud yoki yangi manzilni tanlang.")
        elif delivery_type == Order.DeliveryType.PICKUP:
            if not cleaned_data.get("delivery_point"):
                self.add_error("delivery_point", "Topshirish punktini tanlang.")

        return cleaned_data
