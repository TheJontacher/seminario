from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from maintenance.models import MaintenanceSchedule
from owners.models import Owner
from reminders.models import Reminder
from service_orders.models import Mechanic, ServiceOrder, ServicePerformed
from vehicles.models import Vehicle


class Command(BaseCommand):
	help = "Crea datos ficticios idempotentes para una demostración académica."

	def handle(self, *args, **options):
		with transaction.atomic():
			owners = self.seed_owners()
			vehicles = self.seed_vehicles(owners)
			mechanics = self.seed_mechanics()
			orders = self.seed_orders(vehicles, mechanics)
			schedules = self.seed_maintenance(vehicles)
			reminders = self.seed_reminders(schedules)

		self.stdout.write(self.style.SUCCESS("Datos demo listos:"))
		self.stdout.write(f"- Propietarios demo: {len(owners)}")
		self.stdout.write(f"- Vehículos demo: {len(vehicles)}")
		self.stdout.write(f"- Mecánicos demo: {len(mechanics)}")
		self.stdout.write(f"- Órdenes demo: {len(orders)}")
		self.stdout.write(f"- Mantenimientos demo: {len(schedules)}")
		self.stdout.write(f"- Recordatorios demo: {len(reminders)}")

	def seed_owners(self):
		fixtures = [
			(Owner.OwnerType.PERSONA, "DEMO - Ana Ejemplo", "0000000001", "ana@example.com"),
			(Owner.OwnerType.PERSONA, "DEMO - Bruno Muestra", "0000000002", "bruno@example.com"),
			(Owner.OwnerType.PERSONA, "DEMO - Carla Ficticia", "0000000003", "carla@example.com"),
			(Owner.OwnerType.PERSONA, "DEMO - Diego Prueba", "0000000004", "diego@example.com"),
			(Owner.OwnerType.PERSONA, "DEMO - Elena Simulada", "0000000005", "elena@example.com"),
			(Owner.OwnerType.PERSONA, "DEMO - Fabio Inventado", "0000000006", "fabio@example.com"),
			(Owner.OwnerType.EMPRESA, "DEMO - Transporte Ejemplo SAS", "0000000007", "transporte@example.com"),
			(Owner.OwnerType.EMPRESA, "DEMO - Mensajería Muestra Ltda", "0000000008", "mensajeria@example.com"),
		]
		owners = []
		for owner_type, name, phone, email in fixtures:
			owner, _ = Owner.objects.get_or_create(
				nombre=name,
				defaults={
					"tipo": owner_type,
					"telefono": phone,
					"email": email,
					"direccion": "Dirección ficticia para demostración",
				},
			)
			owners.append(owner)
		return owners

	def seed_vehicles(self, owners):
		fixtures = [
			("DEMO001", 0, "MOTOCICLETA", "Honda", "CB190R", 2022, 16800, Vehicle.UsageProfile.ALTO),
			("DEMO002", 1, "MOTOCICLETA", "Yamaha", "FZ25", 2023, 7400, Vehicle.UsageProfile.NORMAL),
			("DEMO003", 2, "MOTOCICLETA", "Suzuki", "GN125", 2021, 2200, Vehicle.UsageProfile.BAJO),
			("DEMO004", 3, "AUTOMÓVIL", "Toyota", "Corolla", 2020, 5100, Vehicle.UsageProfile.NORMAL),
			("DEMO005", 4, "AUTOMÓVIL", "Chevrolet", "Onix", 2024, 9200, Vehicle.UsageProfile.ALTO),
			("DEMO006", 5, "CAMIONETA", "Nissan", "Frontier", 2019, 12400, Vehicle.UsageProfile.ALTO),
			("DEMO007", 6, "MOTOCICLETA", "Bajaj", "Pulsar NS200", 2022, 3300, Vehicle.UsageProfile.NORMAL),
			("DEMO008", 7, "AUTOMÓVIL", "Kia", "Rio", 2021, 17700, Vehicle.UsageProfile.ALTO),
			("DEMO009", 0, "MOTOCICLETA", "AKT", "NKD 125", 2020, 6500, Vehicle.UsageProfile.NORMAL),
			("DEMO010", 2, "CAMIONETA", "Renault", "Duster", 2023, 11500, Vehicle.UsageProfile.BAJO),
		]
		vehicles = []
		for plate, owner_index, kind, brand, model, year, mileage, profile in fixtures:
			vehicle, _ = Vehicle.objects.get_or_create(
				placa=plate,
				defaults={
					"owner": owners[owner_index],
					"tipo": kind,
					"marca": brand,
					"modelo": model,
					"anio": year,
					"kilometraje_actual": mileage,
					"estado": "ACTIVO",
					"perfil_uso": profile,
					"observaciones": "Registro ficticio de demostración.",
				},
			)
			vehicles.append(vehicle)
		return vehicles

	def seed_mechanics(self):
		fixtures = [
			("DEMO - Mecánico Alex", "0000000011", True),
			("DEMO - Mecánica Sam", "0000000012", True),
			("DEMO - Mecánico Cris", "0000000013", True),
			("DEMO - Mecánica Pat", "0000000014", False),
		]
		mechanics = []
		for name, phone, active in fixtures:
			mechanic, _ = Mechanic.objects.get_or_create(
				nombre=name,
				defaults={"telefono": phone, "activo": active},
			)
			mechanics.append(mechanic)
		return mechanics

	def seed_orders(self, vehicles, mechanics):
		today = timezone.localdate()
		fixtures = [
			(0, 0, ServiceOrder.Status.ENTREGADO, 36, "Cambio de aceite", "Revisión de frenos"),
			(1, 1, ServiceOrder.Status.ENTREGADO, 30, "Cambio de filtro"),
			(2, 2, ServiceOrder.Status.TERMINADO, 18, "Ajuste de cadena", "Cambio de aceite"),
			(3, 0, ServiceOrder.Status.TERMINADO, 14, "Revisión general"),
			(4, 1, ServiceOrder.Status.EN_PROCESO, 4, "Revisión de frenos"),
			(5, 2, ServiceOrder.Status.EN_PROCESO, 2, "Cambio de filtro"),
			(6, 0, ServiceOrder.Status.RECIBIDO, 1, "Revisión general"),
			(7, 2, ServiceOrder.Status.RECIBIDO, 0, "Ajuste de cadena"),
			(8, 1, ServiceOrder.Status.DETENIDO_REPUESTOS, 3, "Cambio de filtro"),
			(9, 0, ServiceOrder.Status.DETENIDO_REPUESTOS, 5, "Revisión de frenos"),
		]
		orders = []
		for vehicle_index, mechanic_index, target_status, days_ago, *service_names in fixtures:
			vehicle = vehicles[vehicle_index]
			marker = f"DEMO - Orden de {vehicle.placa}"
			order, _ = ServiceOrder.objects.get_or_create(
				vehicle=vehicle,
				motivo_ingreso=marker,
				defaults={
					"mechanic": mechanics[mechanic_index],
					"fecha_ingreso": today - timedelta(days=days_ago),
					"kilometraje_ingreso": vehicle.kilometraje_actual,
					"observaciones": "Orden y valores ficticios de demostración.",
				},
			)
			for service_name in service_names:
				ServicePerformed.objects.get_or_create(
					service_order=order,
					nombre=f"DEMO - {service_name}",
					defaults={
						"descripcion": f"Ejemplo demostrativo: {service_name.lower()}.",
						"observaciones": "Datos ficticios; no representa trabajo real.",
						"es_preventivo": service_name
						in {"Cambio de aceite", "Cambio de filtro", "Ajuste de cadena"},
					},
				)
			self.apply_order_status(order, target_status)
			orders.append(order)
		return orders

	def apply_order_status(self, order, target_status):
		if order.estado == ServiceOrder.Status.ENTREGADO:
			return
		if target_status == ServiceOrder.Status.ENTREGADO:
			if order.estado != ServiceOrder.Status.TERMINADO:
				order.estado = ServiceOrder.Status.TERMINADO
				order.save()
			order.estado = ServiceOrder.Status.ENTREGADO
			order.save()
		elif order.estado != target_status:
			order.estado = target_status
			order.save()

	def seed_maintenance(self, vehicles):
		today = timezone.localdate()
		fixtures = [
			(0, "Cambio de aceite por kilometraje", 1000, None, 15000, None),
			(1, "Revisión próxima por kilometraje", 5000, None, 2600, None),
			(2, "Plan al día por kilometraje", 5000, None, 1000, None),
			(3, "Revisión próxima por fecha", None, 180, None, today - timedelta(days=176)),
			(4, "Cambio de filtro vencido por fecha", None, 180, None, today - timedelta(days=210)),
			(5, "Revisión al día por fecha", None, 180, None, today - timedelta(days=30)),
		]
		schedules = []
		for vehicle_index, name, km_interval, day_interval, last_km, last_date in fixtures:
			schedule, _ = MaintenanceSchedule.objects.get_or_create(
				vehicle=vehicles[vehicle_index],
				nombre_servicio=f"DEMO - {name}",
				defaults={
					"intervalo_km": km_interval,
					"intervalo_dias": day_interval,
					"ultimo_kilometraje": last_km,
					"ultima_fecha": last_date,
					"activo": True,
					"observaciones": "Plan ficticio de demostración.",
				},
			)
			schedules.append(schedule)
		return schedules

	def seed_reminders(self, schedules):
		today = timezone.localdate()
		now = timezone.now()
		fixtures = [
			(1, today, Reminder.Status.PENDIENTE, None),
			(3, today - timedelta(days=1), Reminder.Status.CONTACTADO, now),
			(0, today - timedelta(days=7), Reminder.Status.COMPLETADO, now - timedelta(days=6)),
			(4, today + timedelta(days=2), Reminder.Status.CANCELADO, None),
		]
		reminders = []
		for schedule_index, scheduled_date, status, contacted_at in fixtures:
			marker = f"DEMO - Recordatorio {status.lower()} {schedule_index + 1}"
			reminder, _ = Reminder.objects.get_or_create(
				maintenance_schedule=schedules[schedule_index],
				mensaje=marker,
				defaults={
					"fecha_programada": scheduled_date,
					"estado": status,
					"contactado_at": contacted_at,
				},
			)
			reminders.append(reminder)
		return reminders