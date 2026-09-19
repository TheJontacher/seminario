from django import forms

from .models import Owner


class OwnerForm(forms.ModelForm):
    class Meta:
        model = Owner
        fields = [
            "tipo",
            "nombre",
            "telefono",
            "email",
            "direccion",
            "activo",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }