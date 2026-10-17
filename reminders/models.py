import re
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from maintenance.models import MaintenanceSchedule


class ReminderQuerySet(models.QuerySet):
	def delete(self):
		raise ValidationError("Los recordatorios históricos no se eliminan.")


class Reminder(models.Model):
	class Type(models.TextChoices):
		MANUAL = "MANUAL", "Manual"
		PREVIO_7_DIAS = "PREVIO_7_DIAS", "Próximo (7 días / 500 km)"
		VENCIDO = "VENCIDO", "Vencido"

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
	tipo = models.CharField(max_length=15, choices=Type.choices, default=Type.MANUAL)
	ciclo = models.CharField(max_length=64, blank=True, default="", editable=False)
	estado = models.CharField(
		max_length=12,
		choices=Status.choices,
		default=Status.PENDIENTE,
	)
	mensaje = models.TextField(blank=True)
	contactado_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	objects = ReminderQuerySet.as_manager()

	class Meta:
		ordering = ["fecha_programada", "created_at"]
		verbose_name = "recordatorio"
		verbose_name_plural = "recordatorios"
		constraints = [
			models.UniqueConstraint(
				fields=["maintenance_schedule", "tipo", "ciclo"],
				condition=models.Q(tipo__in=["PREVIO_7_DIAS", "VENCIDO"]),
				name="unique_automatic_reminder_per_cycle",
			)
		]

	def __str__(self):
		return f"{self.maintenance_schedule} - {self.fecha_programada}"

	def clean(self):
		super().clean()
		if self.estado == self.Status.CONTACTADO and not self.contactado_at:
			raise ValidationError(
				{"contactado_at": "Un recordatorio contactado debe registrar la fecha."}
			)

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		raise ValidationError("Los recordatorios históricos no se eliminan.")

	def change_status(self, new_status):
		if new_status not in {self.Status.CONTACTADO, self.Status.COMPLETADO, self.Status.CANCELADO}:
			raise ValidationError("Estado de seguimiento no válido.")
		with transaction.atomic():
			current = type(self).objects.select_for_update().get(pk=self.pk)
			if current.estado in {self.Status.COMPLETADO, self.Status.CANCELADO}:
				raise ValidationError("Un recordatorio cerrado no puede cambiar de estado.")
			current.estado = new_status
			if new_status == self.Status.CONTACTADO and not current.contactado_at:
				current.contactado_at = timezone.now()
			current.full_clean()
			current.save(update_fields=["estado", "contactado_at", "updated_at"])
			self.estado = current.estado
			self.contactado_at = current.contactado_at

	@property
	def generated_message(self):
		vehicle = self.maintenance_schedule.vehicle
		owner = vehicle.owner
		schedule = self.maintenance_schedule
		is_overdue = self.tipo == self.Type.VENCIDO or (
			self.tipo == self.Type.MANUAL
			and schedule.get_status() == MaintenanceSchedule.MaintenanceStatus.VENCIDO
		)
		if is_overdue:
			message = (
				f"Estimado {owner.nombre}, el mantenimiento de {schedule.nombre_servicio} "
				f"de su vehículo {vehicle.marca} {vehicle.modelo}, placa {vehicle.placa}, "
				"se encuentra vencido. Le recomendamos comunicarse con el taller "
				"para programar su atención."
			)
		else:
			message = (
				f"Estimado {owner.nombre}, le recordamos que su vehículo "
				f"{vehicle.marca} {vehicle.modelo}, placa {vehicle.placa}, "
				f"tiene próximo el servicio de {schedule.nombre_servicio}. "
				"Comuníquese con el taller para programar su atención."
			)
		if schedule.proxima_fecha:
			message += f" Próxima fecha: {schedule.proxima_fecha}."
		if schedule.proximo_kilometraje is not None:
			message += f" Próximo kilometraje: {schedule.proximo_kilometraje} km."
		return message

	@property
	def whatsapp_message(self):
		return self.mensaje or self.generated_message

	@property
	def whatsapp_url(self):
		phone = self.maintenance_schedule.vehicle.owner.telefono
		normalized_phone = re.sub(r"\D", "", phone or "")
		if normalized_phone.startswith("00"):
			normalized_phone = normalized_phone[2:]
		if not normalized_phone:
			return ""
		return f"https://wa.me/{normalized_phone}?text={quote(self.whatsapp_message)}"
