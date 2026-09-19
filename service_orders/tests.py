from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
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


class ServiceOrderViewsTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="usuario_ordenes",
			password="contrasena-segura",
		)
		self.client.force_login(self.user)
		owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario de orden",
			telefono="3000000000",
		)
		self.vehicle = Vehicle.objects.create(
			owner=owner,
			tipo="MOTOCICLETA",
			marca="Honda",
			modelo="CB190R",
			anio=timezone.now().year,
			placa="ORD123",
			kilometraje_actual=1000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)
		self.order_data = {
			"vehicle": self.vehicle.pk,
			"fecha_ingreso": timezone.localdate().isoformat(),
			"kilometraje_ingreso": 1000,
			"motivo_ingreso": "Revisión general",
			"observaciones": "Sin observaciones",
		}

	def create_order(self, **overrides):
		data = {"vehicle": self.vehicle, "kilometraje_ingreso": 1000, "motivo_ingreso": "Revisión general"}
		data.update(overrides)
		return ServiceOrder.objects.create(**data)

	def test_order_list_requires_login(self):
		self.client.logout()

		response = self.client.get("/ordenes/")

		self.assertRedirects(response, "/login/?next=/ordenes/")

	def test_create_valid_order(self):
		response = self.client.post("/ordenes/nueva/", self.order_data)

		order = ServiceOrder.objects.get()
		self.assertRedirects(response, f"/ordenes/{order.pk}/")
		self.assertEqual(order.estado, ServiceOrder.Status.RECIBIDO)

	def test_order_detail_renders(self):
		order = self.create_order()

		response = self.client.get(f"/ordenes/{order.pk}/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "ORD123")
		self.assertContains(response, "Propietario de orden")

	def test_edit_valid_order(self):
		order = self.create_order()
		data = {**self.order_data, "motivo_ingreso": "Motivo actualizado"}

		response = self.client.post(f"/ordenes/{order.pk}/editar/", data)

		order.refresh_from_db()
		self.assertRedirects(response, f"/ordenes/{order.pk}/")
		self.assertEqual(order.motivo_ingreso, "Motivo actualizado")

	def test_second_open_order_shows_error(self):
		self.create_order()

		response = self.client.post("/ordenes/nueva/", self.order_data)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "vehicle")
		self.assertEqual(ServiceOrder.objects.count(), 1)

	def test_lower_mileage_shows_error(self):
		data = {**self.order_data, "kilometraje_ingreso": 999}

		response = self.client.post("/ordenes/nueva/", data)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(ServiceOrder.objects.count(), 0)

	def test_delivered_order_cannot_be_edited(self):
		order = self.create_order()
		ServicePerformed.objects.create(
			service_order=order,
			nombre="Servicio completado",
		)
		order.estado = ServiceOrder.Status.TERMINADO
		order.save()
		order.estado = ServiceOrder.Status.ENTREGADO
		order.save()

		data = {**self.order_data, "motivo_ingreso": "Intento de cambio"}
		response = self.client.post(f"/ordenes/{order.pk}/editar/", data)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "no puede modificarse")

	def test_add_service_valid(self):
		order = self.create_order()
		data = {
			"nombre": "Cambio de aceite",
			"descripcion": "Se reemplazó el aceite del motor.",
			"observaciones": "Sin novedades",
			"es_preventivo": "on",
		}

		response = self.client.post(
			f"/ordenes/{order.pk}/servicios/nuevo/",
			data,
		)

		self.assertRedirects(response, f"/ordenes/{order.pk}/")
		self.assertTrue(ServicePerformed.objects.filter(service_order=order).exists())

	def test_anonymous_user_cannot_add_service(self):
		order = self.create_order()
		self.client.logout()

		response = self.client.get(f"/ordenes/{order.pk}/servicios/nuevo/")

		self.assertRedirects(
			response,
			f"/login/?next=/ordenes/{order.pk}/servicios/nuevo/",
		)

	def test_delivered_order_rejects_new_service(self):
		order = self.create_order()
		ServicePerformed.objects.create(service_order=order, nombre="Servicio inicial")
		order.estado = ServiceOrder.Status.TERMINADO
		order.save()
		order.estado = ServiceOrder.Status.ENTREGADO
		order.save()

		response = self.client.post(
			f"/ordenes/{order.pk}/servicios/nuevo/",
			{"nombre": "Servicio bloqueado"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "No se pueden modificar servicios")

	def test_change_status_valid(self):
		order = self.create_order()

		response = self.client.post(
			f"/ordenes/{order.pk}/estado/",
			{"nuevo_estado": ServiceOrder.Status.EN_PROCESO},
		)

		self.assertRedirects(response, f"/ordenes/{order.pk}/")
		order.refresh_from_db()
		self.assertEqual(order.estado, ServiceOrder.Status.EN_PROCESO)

	def test_terminated_without_service_fails(self):
		order = self.create_order()

		response = self.client.post(
			f"/ordenes/{order.pk}/estado/",
			{"nuevo_estado": ServiceOrder.Status.TERMINADO},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "sin servicios realizados")

	def test_terminated_with_service_works(self):
		order = self.create_order()
		ServicePerformed.objects.create(service_order=order, nombre="Servicio completo")

		response = self.client.post(
			f"/ordenes/{order.pk}/estado/",
			{"nuevo_estado": ServiceOrder.Status.TERMINADO},
		)

		self.assertRedirects(response, f"/ordenes/{order.pk}/")
		order.refresh_from_db()
		self.assertEqual(order.estado, ServiceOrder.Status.TERMINADO)

	def test_status_history_is_created_by_status_change(self):
		order = self.create_order()

		self.client.post(
			f"/ordenes/{order.pk}/estado/",
			{"nuevo_estado": ServiceOrder.Status.EN_PROCESO},
		)

		history = OrderStatusHistory.objects.get(service_order=order)
		self.assertEqual(history.estado_nuevo, ServiceOrder.Status.EN_PROCESO)

	def test_delivered_order_cannot_change_status(self):
		order = self.create_order()
		ServicePerformed.objects.create(service_order=order, nombre="Servicio completo")
		order.estado = ServiceOrder.Status.TERMINADO
		order.save()
		order.estado = ServiceOrder.Status.ENTREGADO
		order.save()

		response = self.client.post(
			f"/ordenes/{order.pk}/estado/",
			{"nuevo_estado": ServiceOrder.Status.RECIBIDO},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "no puede modificarse")

