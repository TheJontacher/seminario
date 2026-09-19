from datetime import date, timedelta
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from owners.models import Owner
from maintenance.models import MaintenanceSchedule
from vehicles.models import Vehicle

from .models import Reminder


class ReminderViewsTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="usuario_recordatorios",
			password="contrasena-segura",
		)
		self.client.force_login(self.user)
		owner = Owner.objects.create(
			tipo=Owner.OwnerType.PERSONA,
			nombre="Carlos Recordatorio",
			telefono="+57 300 123 4567",
		)
		self.vehicle = Vehicle.objects.create(
			owner=owner,
			tipo="MOTOCICLETA",
			marca="Honda",
			modelo="CB190R",
			anio=timezone.now().year,
			placa="REM123",
			kilometraje_actual=5000,
			estado="ACTIVO",
			perfil_uso=Vehicle.UsageProfile.NORMAL,
		)
		self.schedule = MaintenanceSchedule.objects.create(
			vehicle=self.vehicle,
			nombre_servicio="Cambio de aceite",
			intervalo_km=5000,
			ultimo_kilometraje=5000,
		)
		self.reminder_data = {
			"maintenance_schedule": self.schedule.pk,
			"fecha_programada": (timezone.localdate() + timedelta(days=2)).isoformat(),
			"mensaje": "Recordatorio personalizado",
		}

	def create_reminder(self, **overrides):
		data = {
			"maintenance_schedule": self.schedule,
			"fecha_programada": timezone.localdate(),
		}
		data.update(overrides)
		return Reminder.objects.create(**data)

	def test_reminder_list_requires_login(self):
		self.client.logout()

		response = self.client.get("/recordatorios/")

		self.assertRedirects(response, "/login/?next=/recordatorios/")

	def test_create_reminder(self):
		response = self.client.post("/recordatorios/nuevo/", self.reminder_data)

		reminder = Reminder.objects.get()
		self.assertRedirects(response, f"/recordatorios/{reminder.pk}/")
		self.assertEqual(reminder.estado, Reminder.Status.PENDIENTE)

	def test_initial_status_is_pending(self):
		reminder = self.create_reminder()

		self.assertEqual(reminder.estado, Reminder.Status.PENDIENTE)

	def test_reminder_detail_works(self):
		reminder = self.create_reminder()

		response = self.client.get(f"/recordatorios/{reminder.pk}/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Carlos Recordatorio")
		self.assertContains(response, "REM123")

	def test_edit_reminder(self):
		reminder = self.create_reminder()
		data = {**self.reminder_data, "mensaje": "Mensaje actualizado"}

		response = self.client.post(f"/recordatorios/{reminder.pk}/editar/", data)

		reminder.refresh_from_db()
		self.assertRedirects(response, f"/recordatorios/{reminder.pk}/")
		self.assertEqual(reminder.mensaje, "Mensaje actualizado")

	def test_mark_reminder_contacted(self):
		reminder = self.create_reminder()

		response = self.client.post(f"/recordatorios/{reminder.pk}/contactado/")

		reminder.refresh_from_db()
		self.assertRedirects(response, f"/recordatorios/{reminder.pk}/")
		self.assertEqual(reminder.estado, Reminder.Status.CONTACTADO)

	def test_contacted_saves_contacted_at(self):
		reminder = self.create_reminder()

		self.client.post(f"/recordatorios/{reminder.pk}/contactado/")

		reminder.refresh_from_db()
		self.assertIsNotNone(reminder.contactado_at)

	def test_contacted_endpoint_requires_post(self):
		reminder = self.create_reminder()

		response = self.client.get(f"/recordatorios/{reminder.pk}/contactado/")

		self.assertEqual(response.status_code, 405)

	def test_closed_reminder_cannot_be_marked_contacted(self):
		reminder = self.create_reminder(estado=Reminder.Status.COMPLETADO)

		response = self.client.post(f"/recordatorios/{reminder.pk}/contactado/")

		reminder.refresh_from_db()
		self.assertRedirects(response, f"/recordatorios/{reminder.pk}/")
		self.assertEqual(reminder.estado, Reminder.Status.COMPLETADO)

	def test_whatsapp_contains_normalized_phone(self):
		reminder = self.create_reminder()

		response = self.client.get(f"/recordatorios/{reminder.pk}/")

		self.assertContains(response, "wa.me/573001234567")

	def test_whatsapp_contains_encoded_message(self):
		reminder = self.create_reminder()

		response = self.client.get(f"/recordatorios/{reminder.pk}/")

		self.assertContains(response, quote(reminder.whatsapp_message))

	def test_missing_phone_has_no_whatsapp_link(self):
		self.vehicle.owner.telefono = ""
		self.vehicle.owner.save(update_fields=["telefono"])
		reminder = self.create_reminder()

		response = self.client.get(f"/recordatorios/{reminder.pk}/")

		self.assertEqual(reminder.whatsapp_url, "")
		self.assertContains(response, "No hay teléfono disponible")
		self.assertNotContains(response, "https://wa.me/")

	def test_dashboard_displays_pending_reminders(self):
		self.create_reminder()

		response = self.client.get("/")

		self.assertEqual(response.context["pending_reminders"], 1)

	def test_dashboard_displays_maintenance_alerts(self):
		schedule = MaintenanceSchedule.objects.create(
			vehicle=self.vehicle,
			nombre_servicio="Servicio vencido",
			intervalo_km=100,
			ultimo_kilometraje=4000,
		)

		response = self.client.get("/")

		self.assertContains(response, "Alertas de mantenimiento")
		self.assertContains(response, schedule.nombre_servicio)
