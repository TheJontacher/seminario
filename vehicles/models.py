from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validate_vehicle_year(value):
	current_year = timezone.now().year
	if value > current_year + 1:
		from django.core.exceptions import ValidationError

		raise ValidationError(
			"El año del vehículo no puede superar el año actual más uno."
		)


class Vehicle(models.Model):
	class UsageProfile(models.TextChoices):
		BAJO = "BAJO", "Bajo"
		NORMAL = "NORMAL", "Normal"
		ALTO = "ALTO", "Alto"

	owner = models.ForeignKey(
		"owners.Owner",
		on_delete=models.PROTECT,
		related_name="vehicles",
	)
	tipo = models.CharField(max_length=50)
	marca = models.CharField(max_length=100)
	modelo = models.CharField(max_length=100)
	anio = models.PositiveIntegerField(validators=[validate_vehicle_year])
	placa = models.CharField(max_length=20, unique=True)
	kilometraje_actual = models.PositiveIntegerField(
		validators=[MinValueValidator(0)]
	)
	fecha_ingreso = models.DateField(default=timezone.localdate)
	estado = models.CharField(max_length=50)
	observaciones = models.TextField(blank=True)
	perfil_uso = models.CharField(max_length=10, choices=UsageProfile.choices)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["placa"]
		verbose_name = "vehículo"
		verbose_name_plural = "vehículos"

	def __str__(self):
		return f"{self.placa} - {self.marca} {self.modelo}"
