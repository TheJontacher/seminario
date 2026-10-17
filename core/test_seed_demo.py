from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from maintenance.models import MaintenanceSchedule
from owners.models import Owner
from reminders.models import Reminder
from service_orders.models import Mechanic, OrderStatusHistory, ServiceOrder, ServicePerformed
from vehicles.models import Vehicle


class SeedDemoCommandTests(TestCase):
	def demo_counts(self):
		return (
			Owner.objects.filter(nombre__startswith="DEMO - ").count(),
			Vehicle.objects.filter(placa__startswith="DEMO").count(),
			Mechanic.objects.filter(nombre__startswith="DEMO - ").count(),
			ServiceOrder.objects.filter(motivo_ingreso__startswith="DEMO - ").count(),
			MaintenanceSchedule.objects.filter(nombre_servicio__startswith="DEMO - ").count(),
			Reminder.objects.filter(mensaje__startswith="DEMO - ").count(),
		)

	def test_command_runs_and_prints_demo_summary(self):
		output = StringIO()

		call_command("seed_demo", stdout=output)

		self.assertIn("Propietarios demo: 8", output.getvalue())
		self.assertIn("Vehículos demo: 10", output.getvalue())
		self.assertIn("Mecánicos demo: 4", output.getvalue())
		self.assertIn("Órdenes demo: 10", output.getvalue())
		self.assertIn("Mantenimientos demo: 6", output.getvalue())
		self.assertIn("Recordatorios demo: 4", output.getvalue())

	def test_running_command_twice_does_not_duplicate_demo_data(self):
		call_command("seed_demo", stdout=StringIO())
		first_counts = self.demo_counts()

		call_command("seed_demo", stdout=StringIO())

		self.assertEqual(self.demo_counts(), first_counts)
		self.assertEqual(first_counts, (8, 10, 4, 10, 6, 4))

	def test_demo_records_respect_main_business_rules(self):
		call_command("seed_demo", stdout=StringIO())
		orders = ServiceOrder.objects.filter(motivo_ingreso__startswith="DEMO - ")
		self.assertEqual(
			set(orders.values_list("estado", flat=True)),
			{
				ServiceOrder.Status.RECIBIDO,
				ServiceOrder.Status.EN_PROCESO,
				ServiceOrder.Status.DETENIDO_REPUESTOS,
				ServiceOrder.Status.TERMINADO,
				ServiceOrder.Status.ENTREGADO,
			},
		)
		for order in orders.filter(
			estado__in=[ServiceOrder.Status.TERMINADO, ServiceOrder.Status.ENTREGADO]
		):
			self.assertTrue(ServicePerformed.objects.filter(service_order=order).exists())
		self.assertTrue(
			OrderStatusHistory.objects.filter(
				service_order__in=orders,
				estado_nuevo=ServiceOrder.Status.ENTREGADO,
			).exists()
		)

		schedules = MaintenanceSchedule.objects.filter(
			nombre_servicio__startswith="DEMO - "
		).select_related("vehicle")
		self.assertEqual(
			{schedule.get_status() for schedule in schedules},
			{
				MaintenanceSchedule.MaintenanceStatus.AL_DIA,
				MaintenanceSchedule.MaintenanceStatus.PROXIMO,
				MaintenanceSchedule.MaintenanceStatus.VENCIDO,
			},
		)
		self.assertEqual(
			set(
				Reminder.objects.filter(mensaje__startswith="DEMO - ").values_list(
					"estado", flat=True
				)
			),
			set(Reminder.Status.values),
		)
		self.assertTrue(
			Reminder.objects.filter(
				mensaje__startswith="DEMO - ",
				estado=Reminder.Status.CONTACTADO,
				contactado_at__isnull=False,
			).exists()
		)