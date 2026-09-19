from django import forms

from .models import MaintenanceSchedule


class MaintenanceScheduleForm(forms.ModelForm):
    class Meta:
        model = MaintenanceSchedule
        fields = [
            "vehicle",
            "nombre_servicio",
            "intervalo_km",
            "intervalo_dias",
            "ultimo_kilometraje",
            "ultima_fecha",
            "activo",
            "observaciones",
        ]
        labels = {
            "vehicle": "Vehículo",
            "nombre_servicio": "Nombre del servicio",
            "intervalo_km": "Intervalo en kilómetros",
            "intervalo_dias": "Intervalo en días",
            "ultimo_kilometraje": "Último kilometraje",
            "ultima_fecha": "Última fecha",
            "activo": "Activo",
            "observaciones": "Observaciones",
        }
        widgets = {
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "nombre_servicio": forms.TextInput(attrs={"class": "form-control"}),
            "intervalo_km": forms.NumberInput(attrs={"class": "form-control"}),
            "intervalo_dias": forms.NumberInput(attrs={"class": "form-control"}),
            "ultimo_kilometraje": forms.NumberInput(attrs={"class": "form-control"}),
            "ultima_fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }