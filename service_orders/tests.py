from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from owners.models import Owner
from vehicles.models import Vehicle

from .models import Mechanic, OrderStatusHistory, ServiceOrder, ServicePerformed


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

	def test_admin_prevents_bulk_deletion_of_historical_records(self):
		for model in (ServiceOrder, ServicePerformed, OrderStatusHistory):
			with self.subTest(model=model.__name__):
				self.assertFalse(admin.site._registry[model].has_delete_permission(None))


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
		self.assertContains(response, f'href="/vehiculos/{order.vehicle_id}/"')

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


class MechanicAndGlobalHistoryTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="usuario_historial",
			password="contrasena-segura",
		)
		self.client.force_login(self.user)
		self.owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietaria Historial",
			telefono="3001112233",
		)
		self.mechanic = Mechanic.objects.create(
			nombre="Mecánico de prueba",
			telefono="3005556677",
		)
		self.vehicle_number = 0

	def create_vehicle(self, *, plate=None, owner=None):
		self.vehicle_number += 1
		return Vehicle.objects.create(
			owner=owner or self.owner,
			tipo="MOTOCICLETA",
			marca="Honda",
			modelo="CB190R",
			anio=timezone.now().year,
			placa=plate or f"HST{self.vehicle_number:03d}",
			kilometraje_actual=1000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)

	def create_order(self, *, plate=None, owner=None, status=ServiceOrder.Status.RECIBIDO, order_date=None, mechanic=None):
		vehicle = self.create_vehicle(plate=plate, owner=owner)
		return ServiceOrder.objects.create(
			vehicle=vehicle,
			mechanic=mechanic or self.mechanic,
			fecha_ingreso=order_date or timezone.localdate(),
			kilometraje_ingreso=1000,
			motivo_ingreso="Revisión de taller",
			estado=status,
		)

	def test_mechanic_list_requires_login(self):
		self.client.logout()

		response = self.client.get("/mecanicos/")

		self.assertRedirects(response, "/login/?next=/mecanicos/")

	def test_create_mechanic(self):
		response = self.client.post(
			"/mecanicos/nuevo/",
			{"nombre": "Nuevo mecánico", "telefono": "3001234567", "activo": "on"},
		)

		mechanic = Mechanic.objects.get(nombre="Nuevo mecánico")
		self.assertRedirects(response, f"/mecanicos/{mechanic.pk}/")

	def test_edit_mechanic(self):
		response = self.client.post(
			f"/mecanicos/{self.mechanic.pk}/editar/",
			{"nombre": "Nombre actualizado", "telefono": "", "activo": "on"},
		)

		self.mechanic.refresh_from_db()
		self.assertRedirects(response, f"/mecanicos/{self.mechanic.pk}/")
		self.assertEqual(self.mechanic.nombre, "Nombre actualizado")

	def test_mechanic_detail_displays_order_totals(self):
		self.create_order(status=ServiceOrder.Status.RECIBIDO)
		self.create_order(status=ServiceOrder.Status.ENTREGADO)

		response = self.client.get(f"/mecanicos/{self.mechanic.pk}/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["mechanic"].total_orders, 2)
		self.assertEqual(response.context["mechanic"].active_orders, 1)
		self.assertEqual(response.context["mechanic"].delivered_orders, 1)

	def test_mechanic_list_shows_assigned_order_count(self):
		self.create_order()
		self.create_order()

		response = self.client.get("/mecanicos/")

		listed_mechanic = response.context["mechanics"].get(pk=self.mechanic.pk)
		self.assertEqual(listed_mechanic.order_count, 2)

	def test_global_history_requires_login(self):
		self.client.logout()

		response = self.client.get("/historial/")

		self.assertRedirects(response, "/login/?next=/historial/")

	def test_global_history_displays_orders_including_delivered(self):
		self.create_order(status=ServiceOrder.Status.ENTREGADO, plate="DONE01")

		response = self.client.get("/historial/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "DONE01")
		self.assertContains(response, "Entregado")

	def test_global_history_filters_by_plate(self):
		self.create_order(plate="FIND01")
		self.create_order(plate="OTHER1")

		response = self.client.get("/historial/?placa=FIND")

		self.assertEqual(len(response.context["orders"]), 1)
		self.assertEqual(response.context["orders"][0].vehicle.placa, "FIND01")

	def test_global_history_filters_by_owner(self):
		other_owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Otra Persona",
			telefono="3003334444",
		)
		self.create_order(owner=other_owner, plate="OWNER1")
		self.create_order(plate="OWNER2")

		response = self.client.get("/historial/?propietario=Otra")

		self.assertEqual(len(response.context["orders"]), 1)
		self.assertEqual(response.context["orders"][0].vehicle.placa, "OWNER1")

	def test_global_history_filters_by_status(self):
		self.create_order(status=ServiceOrder.Status.ENTREGADO, plate="STATUS1")
		self.create_order(status=ServiceOrder.Status.RECIBIDO, plate="STATUS2")

		response = self.client.get("/historial/?estado=ENTREGADO")

		self.assertEqual(len(response.context["orders"]), 1)
		self.assertEqual(response.context["orders"][0].estado, ServiceOrder.Status.ENTREGADO)

	def test_global_history_orders_by_date_descending(self):
		older_date = timezone.localdate() - timedelta(days=4)
		newer_date = timezone.localdate() - timedelta(days=1)
		self.create_order(order_date=older_date, plate="OLDER1")
		self.create_order(order_date=newer_date, plate="NEWER1")

		response = self.client.get("/historial/")

		self.assertEqual(response.context["orders"][0].vehicle.placa, "NEWER1")
		self.assertEqual(response.context["orders"][1].vehicle.placa, "OLDER1")

	def test_global_history_pagination_advances_and_preserves_filters(self):
		for index in range(26):
			self.create_order(plate=f"PAGE{index:03d}")

		first_page = self.client.get("/historial/?estado=RECIBIDO")
		second_page = self.client.get("/historial/?estado=RECIBIDO&page=2")

		self.assertEqual(first_page.context["page_obj"].number, 1)
		self.assertContains(first_page, "?estado=RECIBIDO&amp;page=2")
		self.assertEqual(second_page.context["page_obj"].number, 2)
		self.assertEqual(len(second_page.context["orders"]), 1)

	def test_vehicle_order_history_includes_mechanic_services_and_detail_link(self):
		order = self.create_order(plate="VEHIST1")
		ServicePerformed.objects.create(service_order=order, nombre="Servicio visible")

		response = self.client.get(f"/vehiculos/{order.vehicle_id}/")

		self.assertContains(response, "Mecánico de prueba")
		self.assertContains(response, "Servicio visible")
		self.assertContains(response, f"/ordenes/{order.pk}/")

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

