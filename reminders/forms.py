from django import forms

from .models import Reminder


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ["maintenance_schedule", "fecha_programada", "mensaje"]
        labels = {
            "maintenance_schedule": "Mantenimiento",
            "fecha_programada": "Fecha programada",
            "mensaje": "Mensaje",
        }
        widgets = {
            "maintenance_schedule": forms.Select(attrs={"class": "form-select"}),
            "fecha_programada": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }