from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from owners.models import Owner

from .models import Vehicle


class VehicleModelTests(TestCase):
	def setUp(self):
		self.owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario de prueba",
			telefono="3000000000",
		)

	def vehicle_data(self):
		return {
			"owner": self.owner,
			"tipo": "MOTOCICLETA",
			"marca": "Marca de prueba",
			"modelo": "Modelo de prueba",
			"anio": timezone.now().year,
			"placa": "ABC123",
			"kilometraje_actual": 0,
			"estado": "ACTIVO",
			"perfil_uso": Vehicle.UsageProfile.NORMAL,
		}

	def test_duplicate_plate_is_invalid(self):
		Vehicle.objects.create(**self.vehicle_data())
		duplicate = Vehicle(**self.vehicle_data())

		with self.assertRaises(ValidationError):
			duplicate.full_clean()

	def test_vehicle_requires_owner(self):
		data = self.vehicle_data()
		data["owner"] = None
		vehicle = Vehicle(**data)

		with self.assertRaises(ValidationError):
			vehicle.full_clean()

	def test_negative_mileage_is_invalid(self):
		data = self.vehicle_data()
		data["kilometraje_actual"] = -1
		vehicle = Vehicle(**data)

		with self.assertRaises(ValidationError):
			vehicle.full_clean()

	def test_year_above_next_year_is_invalid(self):
		data = self.vehicle_data()
		data["anio"] = timezone.now().year + 2
		vehicle = Vehicle(**data)

		with self.assertRaises(ValidationError):
			vehicle.full_clean()


class VehicleViewsTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="usuario_vehiculos",
			password="contrasena-segura",
		)
		self.client.force_login(self.user)
		self.owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Propietario de prueba",
			telefono="3000000000",
		)
		self.vehicle_data = {
			"owner": self.owner.pk,
			"tipo": "MOTOCICLETA",
			"marca": "Honda",
			"modelo": "CB190R",
			"anio": timezone.now().year,
			"placa": "ABC123",
			"kilometraje_actual": 1200,
			"fecha_ingreso": date.today().isoformat(),
			"estado": "ACTIVO",
			"perfil_uso": Vehicle.UsageProfile.NORMAL,
			"observaciones": "Uso urbano",
		}

	def create_vehicle(self, **overrides):
		data = {
			"tipo": "MOTOCICLETA",
			"marca": "Honda",
			"modelo": "CB190R",
			"anio": timezone.now().year,
			"placa": "ABC123",
			"kilometraje_actual": 1200,
			"estado": "ACTIVO",
			"perfil_uso": Vehicle.UsageProfile.NORMAL,
		}
		data.update(overrides)
		return Vehicle.objects.create(owner=self.owner, **data)

	def test_vehicle_list_works(self):
		self.create_vehicle()

		response = self.client.get("/vehiculos/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "ABC123")

	def test_create_valid_vehicle(self):
		response = self.client.post("/vehiculos/nuevo/", self.vehicle_data)

		vehicle = Vehicle.objects.get()
		self.assertRedirects(response, f"/vehiculos/{vehicle.pk}/")
		self.assertEqual(vehicle.placa, "ABC123")

	def test_edit_vehicle(self):
		vehicle = self.create_vehicle()
		data = {**self.vehicle_data, "marca": "Yamaha", "placa": "ABC124"}

		response = self.client.post(f"/vehiculos/{vehicle.pk}/editar/", data)

		vehicle.refresh_from_db()
		self.assertRedirects(response, f"/vehiculos/{vehicle.pk}/")
		self.assertEqual(vehicle.marca, "Yamaha")

	def test_vehicle_detail_works(self):
		vehicle = self.create_vehicle()

		response = self.client.get(f"/vehiculos/{vehicle.pk}/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Propietario de prueba")
		self.assertContains(response, "CB190R")

	def test_invalid_vehicle_form_does_not_save(self):
		invalid_data = {**self.vehicle_data, "anio": timezone.now().year + 2}

		response = self.client.post("/vehiculos/nuevo/", invalid_data)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Vehicle.objects.count(), 0)

