from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from owners.models import Owner
from vehicles.models import Vehicle

from .models import MaintenanceSchedule


class MaintenanceThresholdTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        owner = Owner.objects.create(tipo="PERSONA", nombre="Ana", telefono="55551234")
        cls.vehicle = Vehicle.objects.create(
            owner=owner, tipo="Automóvil", marca="Toyota", modelo="Corolla",
            anio=2025, placa="P456ABC", kilometraje_actual=5000,
            estado="ACTIVO", perfil_uso="NORMAL",
        )

    def test_exact_date_and_mileage_boundaries(self):
        today = date(2026, 10, 17)
        for days, expected in [(8, "AL_DIA"), (7, "PROXIMO"), (1, "PROXIMO"), (0, "VENCIDO"), (-1, "VENCIDO")]:
            with self.subTest(days=days):
                plan = MaintenanceSchedule(vehicle=self.vehicle, proxima_fecha=today + timedelta(days=days))
                self.assertEqual(plan.get_status(current_date=today), expected)
        for km, expected in [(501, "AL_DIA"), (500, "PROXIMO"), (1, "PROXIMO"), (0, "VENCIDO"), (-1, "VENCIDO")]:
            with self.subTest(km=km):
                plan = MaintenanceSchedule(vehicle=self.vehicle, proximo_kilometraje=5000 + km)
                self.assertEqual(plan.get_status(current_mileage=5000), expected)

    def test_either_overdue_criterion_takes_precedence(self):
        today = date(2026, 10, 17)
        plan = MaintenanceSchedule(vehicle=self.vehicle, proxima_fecha=today, proximo_kilometraje=5500)
        self.assertEqual(plan.get_status(current_date=today), "VENCIDO")
        plan.proxima_fecha = today + timedelta(days=7)
        plan.proximo_kilometraje = 5000
        self.assertEqual(plan.get_status(current_date=today), "VENCIDO")

    def test_intervals_require_the_corresponding_last_service_data(self):
        for fields, error_field in [({"intervalo_dias": 30}, "ultima_fecha"), ({"intervalo_km": 5000}, "ultimo_kilometraje")]:
            with self.subTest(fields=fields):
                plan = MaintenanceSchedule(vehicle=self.vehicle, nombre_servicio="Aceite", **fields)
                with self.assertRaises(ValidationError) as error:
                    plan.full_clean()
                self.assertIn(error_field, error.exception.message_dict)
