from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import BloodRequest, Donor


def add_bootstrap(form):
    """Adds Bootstrap's CSS class to every field so the forms look styled."""
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "form-check-input"
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs["class"] = "form-select"
        else:
            field.widget.attrs["class"] = "form-control"


class SignupForm(UserCreationForm):
    """Login account: username, email and password (Django hashes the password)."""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Letters, numbers and @ . + - _"
        self.fields["password1"].help_text = "At least 6 characters."
        self.fields["password2"].help_text = ""
        self.fields["password2"].label = "Confirm password"
        add_bootstrap(self)


class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = ["full_name", "blood_group", "gender", "date_of_birth", "weight_kg",
                  "phone", "city", "last_donation", "is_available"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "last_donation": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "weight_kg": "Weight (kg)",
            "is_available": "I am available to donate right now",
            "last_donation": "Last donation (leave blank if never)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)

    # Django calls clean_<fieldname>() automatically to check that field

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        age = (date.today() - dob).days // 365
        if age < 18:
            raise forms.ValidationError("Donors must be at least 18 years old.")
        if age > 65:
            raise forms.ValidationError("Donors must be 65 or younger.")
        return dob

    def clean_last_donation(self):
        last = self.cleaned_data["last_donation"]
        if last and last > date.today():
            raise forms.ValidationError("Last donation can't be in the future.")
        return last

    def clean_city(self):
        return self.cleaned_data["city"].strip().title()   # "jaipur " -> "Jaipur"


class BloodRequestForm(forms.ModelForm):
    class Meta:
        model = BloodRequest
        fields = ["patient_name", "blood_group", "units_needed", "hospital", "city",
                  "contact_phone", "urgency", "needed_by", "note"]
        widgets = {
            "needed_by": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Ward number, who to ask for, any details"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)

    def clean_needed_by(self):
        needed_by = self.cleaned_data["needed_by"]
        if needed_by < date.today():
            raise forms.ValidationError("The date can't be in the past.")
        return needed_by

    def clean_city(self):
        return self.cleaned_data["city"].strip().title()
