import re
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db import models

from maintenance.models import MaintenanceSchedule


class Reminder(models.Model):
	class Status(models.TextChoices):
		PENDIENTE = "PENDIENTE", "Pendiente"
		CONTACTADO = "CONTACTADO", "Contactado"
		COMPLETADO = "COMPLETADO", "Completado"
		CANCELADO = "CANCELADO", "Cancelado"

	maintenance_schedule = models.ForeignKey(
		MaintenanceSchedule,
		on_delete=models.PROTECT,
		related_name="reminders",
	)
	fecha_programada = models.DateField()
	estado = models.CharField(
		max_length=12,
		choices=Status.choices,
		default=Status.PENDIENTE,
	)
	mensaje = models.TextField(blank=True)
	contactado_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["fecha_programada", "created_at"]
		verbose_name = "recordatorio"
		verbose_name_plural = "recordatorios"

	def __str__(self):
		return f"{self.maintenance_schedule} - {self.fecha_programada}"

	def clean(self):
		super().clean()
		if self.estado == self.Status.CONTACTADO and not self.contactado_at:
			raise ValidationError(
				{"contactado_at": "Un recordatorio contactado debe registrar la fecha."}
			)

	def delete(self, *args, **kwargs):
		raise ValidationError("Los recordatorios históricos no se eliminan.")

	@property
	def whatsapp_message(self):
		vehicle = self.maintenance_schedule.vehicle
		owner = vehicle.owner
		message = (
			f"Hola {owner.nombre}, le recordamos que su vehículo "
			f"{vehicle.marca} {vehicle.modelo}, placa {vehicle.placa}, "
			f"tiene próximo el servicio de "
			f"{self.maintenance_schedule.nombre_servicio}."
		)
		schedule = self.maintenance_schedule
		if schedule.proxima_fecha:
			message += f" Próxima fecha: {schedule.proxima_fecha}."
		if schedule.proximo_kilometraje:
			message += f" Próximo kilometraje: {schedule.proximo_kilometraje} km."
		return message

	@property
	def whatsapp_url(self):
		phone = self.maintenance_schedule.vehicle.owner.telefono
		normalized_phone = re.sub(r"\D", "", phone or "")
		if normalized_phone.startswith("00"):
			normalized_phone = normalized_phone[2:]
		if not normalized_phone:
			return ""
		return f"https://wa.me/{normalized_phone}?text={quote(self.whatsapp_message)}"
