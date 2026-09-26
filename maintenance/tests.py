from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from owners.models import Owner
from vehicles.models import Vehicle

from .models import MaintenanceSchedule


class MaintenanceScheduleTests(TestCase):
	def setUp(self):
		owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario de prueba",
			telefono="3000000000",
		)
		self.vehicle = Vehicle.objects.create(
			owner=owner,
			tipo="MOTOCICLETA",
			marca="Honda",
			modelo="CB190R",
			anio=timezone.now().year,
			placa="MNT123",
			kilometraje_actual=5000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)

	def schedule_data(self, **overrides):
		data = {
			"vehicle": self.vehicle,
			"nombre_servicio": "Cambio de aceite",
			"intervalo_km": 5000,
			"ultimo_kilometraje": 5000,
		}
		data.update(overrides)
		return data

	def test_requires_at_least_one_interval(self):
		schedule = MaintenanceSchedule(**self.schedule_data(intervalo_km=None))
		schedule.intervalo_dias = None

		with self.assertRaises(ValidationError):
			schedule.full_clean()

	def test_rejects_non_positive_intervals(self):
		schedule = MaintenanceSchedule(**self.schedule_data(intervalo_km=0))

		with self.assertRaises(ValidationError):
			schedule.full_clean()

	def test_calculates_next_mileage(self):
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(intervalo_km=3000)
		)

		self.assertEqual(schedule.proximo_kilometraje, 8000)

	def test_calculates_next_date(self):
		start_date = date(2026, 1, 10)
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(
				intervalo_km=None,
				intervalo_dias=30,
				ultimo_kilometraje=None,
				ultima_fecha=start_date,
			)
		)

		self.assertEqual(schedule.proxima_fecha, date(2026, 2, 9))

	def test_detects_al_dia(self):
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(intervalo_km=5000)
		)

		self.assertEqual(
			schedule.get_status(current_mileage=6000),
			MaintenanceSchedule.MaintenanceStatus.AL_DIA,
		)

	def test_detects_proximo_by_mileage(self):
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(intervalo_km=5000)
		)

		self.assertEqual(
			schedule.get_status(current_mileage=9500),
			MaintenanceSchedule.MaintenanceStatus.PROXIMO,
		)

	def test_detects_proximo_by_date(self):
		current_date = date(2026, 3, 1)
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(
				intervalo_km=None,
				intervalo_dias=30,
				ultimo_kilometraje=None,
				ultima_fecha=current_date - timedelta(days=23),
			)
		)

		self.assertEqual(
			schedule.get_status(current_date=current_date),
			MaintenanceSchedule.MaintenanceStatus.PROXIMO,
		)

	def test_detects_vencido_by_mileage(self):
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(intervalo_km=5000)
		)

		self.assertEqual(
			schedule.get_status(current_mileage=10000),
			MaintenanceSchedule.MaintenanceStatus.VENCIDO,
		)

	def test_detects_vencido_by_date(self):
		current_date = date(2026, 3, 1)
		schedule = MaintenanceSchedule.objects.create(
			**self.schedule_data(
				intervalo_km=None,
				intervalo_dias=30,
				ultimo_kilometraje=None,
				ultima_fecha=current_date - timedelta(days=30),
			)
		)

		self.assertEqual(
			schedule.get_status(current_date=current_date),
			MaintenanceSchedule.MaintenanceStatus.VENCIDO,
		)


class MaintenanceScheduleViewsTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="usuario_mantenimiento",
			password="contrasena-segura",
		)
		self.client.force_login(self.user)
		owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario mantenimiento",
			telefono="3000000000",
		)
		self.vehicle = Vehicle.objects.create(
			owner=owner,
			tipo="MOTOCICLETA",
			marca="Honda",
			modelo="CB190R",
			anio=timezone.now().year,
			placa="WEB123",
			kilometraje_actual=5000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)
		self.schedule_data = {
			"vehicle": self.vehicle.pk,
			"nombre_servicio": "Cambio de aceite",
			"intervalo_km": 5000,
			"intervalo_dias": "",
			"ultimo_kilometraje": 5000,
			"ultima_fecha": "",
			"activo": "on",
			"observaciones": "Revisión periódica",
		}

	def test_schedule_list_requires_login(self):
		self.client.logout()

		response = self.client.get("/mantenimiento/")

		self.assertRedirects(response, "/login/?next=/mantenimiento/")

	def test_create_valid_schedule(self):
		response = self.client.post("/mantenimiento/nuevo/", self.schedule_data)

		schedule = MaintenanceSchedule.objects.get()
		self.assertRedirects(response, f"/mantenimiento/{schedule.pk}/")

	def test_edit_schedule(self):
		schedule = MaintenanceSchedule.objects.create(**self.schedule_data_for_model())
		data = {**self.schedule_data, "nombre_servicio": "Cambio de filtro"}

		response = self.client.post(f"/mantenimiento/{schedule.pk}/editar/", data)

		schedule.refresh_from_db()
		self.assertRedirects(response, f"/mantenimiento/{schedule.pk}/")
		self.assertEqual(schedule.nombre_servicio, "Cambio de filtro")

	def schedule_data_for_model(self):
		return {
			"vehicle": self.vehicle,
			"nombre_servicio": "Cambio de aceite",
			"intervalo_km": 5000,
			"ultimo_kilometraje": 5000,
		}

	def test_schedule_detail_works(self):
		schedule = MaintenanceSchedule.objects.create(**self.schedule_data_for_model())

		response = self.client.get(f"/mantenimiento/{schedule.pk}/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "WEB123")
		self.assertContains(response, "Cambio de aceite")
		self.assertContains(response, f'href="/vehiculos/{self.vehicle.pk}/"')

	def test_invalid_schedule_form_does_not_save(self):
		data = {**self.schedule_data, "intervalo_km": "", "intervalo_dias": ""}

		response = self.client.post("/mantenimiento/nuevo/", data)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(MaintenanceSchedule.objects.count(), 0)

	def test_list_displays_calculated_status(self):
		MaintenanceSchedule.objects.create(**self.schedule_data_for_model())

		response = self.client.get("/mantenimiento/")

		self.assertContains(response, "PROXIMO")

	def test_vehicle_detail_displays_maintenance(self):
		MaintenanceSchedule.objects.create(**self.schedule_data_for_model())

		response = self.client.get(f"/vehiculos/{self.vehicle.pk}/")

		self.assertContains(response, "Mantenimiento preventivo")
		self.assertContains(response, "Cambio de aceite")

	def test_dashboard_displays_overdue_count(self):
		data = self.schedule_data_for_model()
		data["intervalo_km"] = 100
		data["ultimo_kilometraje"] = 4000
		MaintenanceSchedule.objects.create(**data)

		response = self.client.get("/")

		self.assertContains(response, "Mantenimientos vencidos")
		self.assertEqual(response.context["overdue_maintenance"], 1)

	def test_dashboard_displays_upcoming_count(self):
		MaintenanceSchedule.objects.create(**self.schedule_data_for_model())

		response = self.client.get("/")

		self.assertContains(response, "Mantenimientos próximos")

	def test_inactive_maintenance_is_excluded_from_dashboard_alert_counts(self):
		data = self.schedule_data_for_model()
		data.update(
			nombre_servicio="Plan inactivo vencido",
			intervalo_km=100,
			ultimo_kilometraje=4000,
			activo=False,
		)
		MaintenanceSchedule.objects.create(**data)

		response = self.client.get("/")

		self.assertEqual(response.context["overdue_maintenance"], 0)
		self.assertNotContains(response, "Plan inactivo vencido")
