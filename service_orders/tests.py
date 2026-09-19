from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from owners.models import Owner
from vehicles.models import Vehicle

from .models import OrderStatusHistory, ServiceOrder, ServicePerformed


class ServiceOrderModelTests(TestCase):
	def setUp(self):
		owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario de prueba",
			telefono="3000000000",
		)
		self.vehicle = Vehicle.objects.create(
			owner=owner,
			tipo="MOTOCICLETA",
			marca="Marca de prueba",
			modelo="Modelo de prueba",
			anio=timezone.now().year,
			placa="ABC123",
			kilometraje_actual=1000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)

	def order_data(self):
		return {
			"vehicle": self.vehicle,
			"kilometraje_ingreso": 1000,
			"motivo_ingreso": "Mantenimiento general",
		}

	def add_service(self, order):
		return ServicePerformed.objects.create(
			service_order=order,
			nombre="Cambio de aceite",
		)

	def test_create_valid_order(self):
		order = ServiceOrder.objects.create(**self.order_data())

		self.assertEqual(order.vehicle, self.vehicle)
		self.assertEqual(order.estado, ServiceOrder.Status.RECIBIDO)

	def test_reject_second_open_order_for_vehicle(self):
		ServiceOrder.objects.create(**self.order_data())

		with self.assertRaises(ValidationError):
			ServiceOrder.objects.create(**self.order_data())

	def test_reject_lower_entry_mileage(self):
		data = self.order_data()
		data["kilometraje_ingreso"] = 999

		with self.assertRaises(ValidationError):
			ServiceOrder.objects.create(**data)

	def test_update_vehicle_mileage_when_entry_is_higher(self):
		data = self.order_data()
		data["kilometraje_ingreso"] = 1200

		ServiceOrder.objects.create(**data)

		self.vehicle.refresh_from_db()
		self.assertEqual(self.vehicle.kilometraje_actual, 1200)

	def test_reject_finished_order_without_service(self):
		order = ServiceOrder.objects.create(**self.order_data())
		order.estado = ServiceOrder.Status.TERMINADO

		with self.assertRaises(ValidationError):
			order.save()

	def test_allow_finished_order_with_service(self):
		order = ServiceOrder.objects.create(**self.order_data())
		self.add_service(order)
		order.estado = ServiceOrder.Status.TERMINADO

		order.save()

		self.assertEqual(order.estado, ServiceOrder.Status.TERMINADO)

	def test_create_history_when_status_changes(self):
		order = ServiceOrder.objects.create(**self.order_data())
		order.estado = ServiceOrder.Status.EN_PROCESO
		order.save()

		history = OrderStatusHistory.objects.get(service_order=order)
		self.assertEqual(history.estado_anterior, ServiceOrder.Status.RECIBIDO)
		self.assertEqual(history.estado_nuevo, ServiceOrder.Status.EN_PROCESO)

	def test_reject_modification_of_delivered_order(self):
		order = ServiceOrder.objects.create(**self.order_data())
		self.add_service(order)
		order.estado = ServiceOrder.Status.TERMINADO
		order.save()
		order.estado = ServiceOrder.Status.ENTREGADO
		order.save()

		order.motivo_ingreso = "Intento de modificación"
		with self.assertRaises(ValidationError):
			order.save()
from django.test import TestCase

# Create your tests here.
