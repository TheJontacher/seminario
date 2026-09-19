from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from vehicles.models import Vehicle


class MaintenanceSchedule(models.Model):
	class MaintenanceStatus(models.TextChoices):
		VENCIDO = "VENCIDO", "Vencido"
		PROXIMO = "PROXIMO", "Próximo"
		AL_DIA = "AL_DIA", "Al día"

	vehicle = models.ForeignKey(
		Vehicle,
		on_delete=models.PROTECT,
		related_name="maintenance_schedules",
	)
	nombre_servicio = models.CharField(max_length=150)
	intervalo_km = models.PositiveIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1)],
	)
	intervalo_dias = models.PositiveIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1)],
	)
	ultimo_kilometraje = models.PositiveIntegerField(null=True, blank=True)
	ultima_fecha = models.DateField(null=True, blank=True)
	proximo_kilometraje = models.PositiveIntegerField(null=True, blank=True)
	proxima_fecha = models.DateField(null=True, blank=True)
	activo = models.BooleanField(default=True)
	observaciones = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["vehicle", "nombre_servicio"]
		verbose_name = "plan de mantenimiento"
		verbose_name_plural = "planes de mantenimiento"

	def __str__(self):
		return f"{self.vehicle.placa} - {self.nombre_servicio}"

	def clean(self):
		super().clean()
		if not self.intervalo_km and not self.intervalo_dias:
			raise ValidationError(
				"Debe existir al menos un intervalo de kilometraje o días."
			)

		if self.ultimo_kilometraje is not None and self.ultimo_kilometraje < 0:
			raise ValidationError({"ultimo_kilometraje": "No puede ser negativo."})

	def save(self, *args, **kwargs):
		self.full_clean()
		if self.ultimo_kilometraje is not None and self.intervalo_km:
			self.proximo_kilometraje = self.ultimo_kilometraje + self.intervalo_km
		else:
			self.proximo_kilometraje = None

		if self.ultima_fecha is not None and self.intervalo_dias:
			self.proxima_fecha = self.ultima_fecha + timedelta(days=self.intervalo_dias)
		else:
			self.proxima_fecha = None

		super().save(*args, **kwargs)

	@property
	def status(self):
		return self.get_status()

	def get_status(self, *, current_date=None, current_mileage=None):
		current_date = current_date or timezone.localdate()
		if current_mileage is None:
			current_mileage = self.vehicle.kilometraje_actual

		uses_km = self.proximo_kilometraje is not None
		uses_date = self.proxima_fecha is not None
		if uses_km and current_mileage >= self.proximo_kilometraje:
			return self.MaintenanceStatus.VENCIDO
		if uses_date and current_date >= self.proxima_fecha:
			return self.MaintenanceStatus.VENCIDO

		km_due_soon = uses_km and (
			self.proximo_kilometraje - current_mileage <= 500
		)
		date_due_soon = uses_date and (
			self.proxima_fecha - current_date <= timedelta(days=7)
		)
		if km_due_soon or date_due_soon:
			return self.MaintenanceStatus.PROXIMO
		return self.MaintenanceStatus.AL_DIA
