from django import forms

from .models import Mechanic, ServiceOrder, ServicePerformed


class MechanicForm(forms.ModelForm):
    class Meta:
        model = Mechanic
        fields = ["nombre", "telefono", "activo"]
        labels = {"nombre": "Nombre", "telefono": "Teléfono", "activo": "Activo"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ServicePerformedForm(forms.ModelForm):
    class Meta:
        model = ServicePerformed
        fields = ["nombre", "descripcion", "observaciones", "es_preventivo"]
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "observaciones": "Observaciones",
            "es_preventivo": "Es preventivo",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "es_preventivo": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class OrderStatusForm(forms.Form):
    nuevo_estado = forms.ChoiceField(
        choices=ServiceOrder.Status.choices,
        label="Nuevo estado",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, current_status=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_status = current_status

    def clean_nuevo_estado(self):
        new_status = self.cleaned_data["nuevo_estado"]
        if new_status == self.current_status:
            raise forms.ValidationError("La orden ya tiene ese estado.")
        return new_status


class ServiceOrderForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = [
            "vehicle",
            "mechanic",
            "fecha_ingreso",
            "kilometraje_ingreso",
            "motivo_ingreso",
            "observaciones",
        ]
        labels = {
            "vehicle": "Vehículo",
            "mechanic": "Mecánico",
            "fecha_ingreso": "Fecha de ingreso",
            "kilometraje_ingreso": "Kilometraje de ingreso",
            "motivo_ingreso": "Motivo de ingreso",
            "observaciones": "Observaciones",
        }
        widgets = {
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "mechanic": forms.Select(attrs={"class": "form-select"}),
            "fecha_ingreso": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "kilometraje_ingreso": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "motivo_ingreso": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }