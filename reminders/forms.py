from django import forms

from .models import Reminder


class ReminderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.tipo != Reminder.Type.MANUAL:
            self.fields["maintenance_schedule"].disabled = True

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
