from django import forms

from .models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "owner",
            "tipo",
            "marca",
            "modelo",
            "anio",
            "placa",
            "kilometraje_actual",
            "fecha_ingreso",
            "estado",
            "perfil_uso",
            "observaciones",
        ]
        labels = {
            "owner": "Propietario",
            "anio": "Año",
            "kilometraje_actual": "Kilometraje actual",
            "fecha_ingreso": "Fecha de ingreso",
            "perfil_uso": "Perfil de uso",
            "observaciones": "Observaciones",
        }
        widgets = {
            "owner": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "anio": forms.NumberInput(attrs={"class": "form-control"}),
            "placa": forms.TextInput(attrs={"class": "form-control"}),
            "kilometraje_actual": forms.NumberInput(attrs={"class": "form-control"}),
            "fecha_ingreso": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "estado": forms.TextInput(attrs={"class": "form-control"}),
            "perfil_uso": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }