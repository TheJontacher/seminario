from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from vehicles.models import Vehicle


class Mechanic(models.Model):
	nombre = models.CharField(max_length=150)
	telefono = models.CharField(max_length=30, blank=True)
	activo = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["nombre"]
		verbose_name = "mecánico"
		verbose_name_plural = "mecánicos"

	def __str__(self):
		return self.nombre


class ServiceOrder(models.Model):
	class Status(models.TextChoices):
		RECIBIDO = "RECIBIDO", "Recibido"
		EN_PROCESO = "EN_PROCESO", "En proceso"
		DETENIDO_REPUESTOS = "DETENIDO_REPUESTOS", "Detenido por repuestos"
		TERMINADO = "TERMINADO", "Terminado"
		ENTREGADO = "ENTREGADO", "Entregado"

	vehicle = models.ForeignKey(
		Vehicle,
		on_delete=models.PROTECT,
		related_name="service_orders",
	)
	mechanic = models.ForeignKey(
		Mechanic,
		on_delete=models.PROTECT,
		related_name="service_orders",
		null=True,
		blank=True,
	)
	fecha_ingreso = models.DateField(default=timezone.localdate)
	kilometraje_ingreso = models.PositiveIntegerField(
		validators=[MinValueValidator(0)]
	)
	motivo_ingreso = models.TextField()
	observaciones = models.TextField(blank=True)
	estado = models.CharField(
		max_length=25,
		choices=Status.choices,
		default=Status.RECIBIDO,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-fecha_ingreso", "-created_at"]
		verbose_name = "orden de servicio"
		verbose_name_plural = "órdenes de servicio"
		constraints = [
			models.UniqueConstraint(
				fields=["vehicle"],
				condition=~Q(estado="ENTREGADO"),
				name="unique_open_order_per_vehicle",
			)
		]

	def __str__(self):
		return f"Orden #{self.pk} - {self.vehicle.placa}"

	def clean(self):
		super().clean()
		if self.pk:
			current = type(self).objects.get(pk=self.pk)
			if current.estado == self.Status.ENTREGADO:
				raise ValidationError("Una orden entregada no puede modificarse.")

		if self.vehicle_id and self.kilometraje_ingreso is not None:
			current_mileage = Vehicle.objects.get(
				pk=self.vehicle_id
			).kilometraje_actual
			if self._state.adding and self.kilometraje_ingreso < current_mileage:
				raise ValidationError(
					"El kilometraje de ingreso no puede ser menor al actual."
				)

		if self.estado == self.Status.TERMINADO:
			has_service = self.pk and ServicePerformed.objects.filter(
				service_order=self
			).exists()
			if not has_service:
				raise ValidationError(
					"Una orden no puede terminarse sin servicios realizados."
				)

	def save(self, *args, **kwargs):
		with transaction.atomic():
			previous = None
			if self.pk:
				previous = type(self).objects.select_for_update().get(pk=self.pk)
				if previous.estado == self.Status.ENTREGADO:
					raise ValidationError("Una orden entregada no puede modificarse.")

			vehicle = Vehicle.objects.select_for_update().get(pk=self.vehicle_id)
			self.vehicle = vehicle
			self.full_clean()
			super().save(*args, **kwargs)

			if self.kilometraje_ingreso > vehicle.kilometraje_actual:
				vehicle.kilometraje_actual = self.kilometraje_ingreso
				vehicle.save(update_fields=["kilometraje_actual", "updated_at"])

			if previous and previous.estado != self.estado:
				OrderStatusHistory.objects.create(
					service_order=self,
					estado_anterior=previous.estado,
					estado_nuevo=self.estado,
				)

	def delete(self, *args, **kwargs):
		raise ValidationError("Las órdenes de servicio son históricas y no se eliminan.")


class ServicePerformed(models.Model):
	service_order = models.ForeignKey(
		ServiceOrder,
		on_delete=models.PROTECT,
		related_name="services_performed",
	)
	nombre = models.CharField(max_length=150)
	descripcion = models.TextField(blank=True)
	observaciones = models.TextField(blank=True)
	es_preventivo = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]
		verbose_name = "servicio realizado"
		verbose_name_plural = "servicios realizados"

	def __str__(self):
		return self.nombre

	def save(self, *args, **kwargs):
		if self.service_order_id and ServiceOrder.objects.filter(
			pk=self.service_order_id,
			estado=ServiceOrder.Status.ENTREGADO,
		).exists():
			raise ValidationError(
				"No se pueden modificar servicios de una orden entregada."
			)
		self.full_clean()
		super().save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		raise ValidationError("Los servicios realizados son históricos y no se eliminan.")


class OrderStatusHistory(models.Model):
	service_order = models.ForeignKey(
		ServiceOrder,
		on_delete=models.PROTECT,
		related_name="status_history",
	)
	estado_anterior = models.CharField(max_length=25, choices=ServiceOrder.Status.choices)
	estado_nuevo = models.CharField(max_length=25, choices=ServiceOrder.Status.choices)
	fecha_hora = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["fecha_hora"]
		verbose_name = "historial de estado"
		verbose_name_plural = "historial de estados"

	def __str__(self):
		return f"{self.estado_anterior} -> {self.estado_nuevo}"

	def delete(self, *args, **kwargs):
		raise ValidationError("El historial de estados no se elimina.")
