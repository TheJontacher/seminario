from datetime import date, timedelta
from io import StringIO
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.utils import timezone

from maintenance.models import MaintenanceSchedule
from owners.models import Owner
from vehicles.models import Vehicle

from .forms import ReminderForm
from .models import Reminder
from .services import generate_reminders


class ReminderGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = date(2026, 10, 17)

        cls.owner = Owner.objects.create(
            tipo=Owner.OwnerType.PERSONA,
            nombre="Ana Pérez",
            telefono="00502 5555-1234",
        )

        cls.vehicle = Vehicle.objects.create(
            owner=cls.owner,
            tipo="Automóvil",
            marca="Toyota",
            modelo="Corolla",
            anio=2025,
            placa="P123ABC",
            kilometraje_actual=10000,
            estado="ACTIVO",
            perfil_uso=Vehicle.UsageProfile.NORMAL,
        )

        cls.schedule = MaintenanceSchedule.objects.create(
            vehicle=cls.vehicle,
            nombre_servicio="Cambio de aceite",
            intervalo_dias=30,
            ultima_fecha=cls.today - timedelta(days=23),
        )

    def generate(self):
        return generate_reminders(current_date=self.today)

    def test_generates_upcoming_notice_and_stores_message(self):
        result = self.generate()
        reminder = Reminder.objects.get()

        self.assertEqual(
            (result.reviewed, result.created, result.existing),
            (1, 1, 0),
        )

        self.assertEqual(
            reminder.tipo,
            Reminder.Type.PREVIO_7_DIAS,
        )

        self.assertEqual(
            reminder.estado,
            Reminder.Status.PENDIENTE,
        )

        self.assertEqual(
            reminder.fecha_programada,
            self.today,
        )

        self.assertIn(
            "Estimado Ana Pérez",
            reminder.mensaje,
        )

        self.assertIn(
            "Toyota Corolla, placa P123ABC",
            reminder.mensaje,
        )

        self.assertIn(
            "tiene próximo el servicio de Cambio de aceite",
            reminder.mensaje,
        )

        self.assertIn(
            "Próxima fecha: 2026-10-24",
            reminder.mensaje,
        )

        self.assertEqual(
            reminder.whatsapp_message,
            reminder.mensaje,
        )

    def test_repeated_generation_and_closed_history_do_not_duplicate(self):
        self.generate()

        for status in Reminder.Status.values:
            with self.subTest(status=status):
                Reminder.objects.update(
                    estado=status
                )

                result = self.generate()

                self.assertEqual(
                    (result.created, result.existing),
                    (0, 1),
                )

                self.assertEqual(
                    Reminder.objects.count(),
                    1,
                )

    def test_upcoming_then_overdue_has_one_notice_of_each_type(self):
        self.generate()

        due_date = self.schedule.proxima_fecha

        result = generate_reminders(
            current_date=due_date
        )

        self.assertEqual(
            result.created,
            1,
        )

        overdue = Reminder.objects.get(
            tipo=Reminder.Type.VENCIDO
        )

        self.assertIn(
            "se encuentra vencido",
            overdue.mensaje,
        )

        self.assertIn(
            "Cambio de aceite",
            overdue.mensaje,
        )

        self.assertEqual(
            overdue.fecha_programada,
            due_date,
        )

        repeated = generate_reminders(
            current_date=due_date + timedelta(days=1)
        )

        self.assertEqual(
            (repeated.created, repeated.existing),
            (0, 1),
        )

        self.assertEqual(
            Reminder.objects.count(),
            2,
        )

    def test_skips_upcoming_when_first_run_is_already_overdue(self):
        result = generate_reminders(
            current_date=self.schedule.proxima_fecha
        )

        self.assertEqual(
            result.created,
            1,
        )

        self.assertEqual(
            Reminder.objects.get().tipo,
            Reminder.Type.VENCIDO,
        )

    def test_kilometre_only_plan_generates_and_includes_target(self):
        self.schedule.intervalo_dias = None
        self.schedule.ultima_fecha = None
        self.schedule.intervalo_km = 5000
        self.schedule.ultimo_kilometraje = 5500
        self.schedule.save()

        self.assertEqual(
            self.generate().created,
            1,
        )

        reminder = Reminder.objects.get()

        self.assertEqual(
            reminder.tipo,
            Reminder.Type.PREVIO_7_DIAS,
        )

        self.assertIn(
            "10500 km",
            reminder.mensaje,
        )

        self.assertNotIn(
            "Próxima fecha:",
            reminder.mensaje,
        )

        self.vehicle.kilometraje_actual = 10500
        self.vehicle.save()

        self.assertEqual(
            self.generate().created,
            1,
        )

        self.assertEqual(
            Reminder.objects.filter(
                tipo=Reminder.Type.VENCIDO
            ).count(),
            1,
        )

    def test_both_targets_in_message_and_first_due_criterion_wins(self):
        self.schedule.intervalo_km = 5000
        self.schedule.ultimo_kilometraje = 5000
        self.schedule.save()

        self.generate()

        reminder = Reminder.objects.get()

        self.assertEqual(
            reminder.tipo,
            Reminder.Type.VENCIDO,
        )

        self.assertIn(
            "Próxima fecha: 2026-10-24",
            reminder.mensaje,
        )

        self.assertIn(
            "Próximo kilometraje: 10000 km",
            reminder.mensaje,
        )

    def test_ignores_inactive_and_not_due_plans(self):
        self.schedule.activo = False
        self.schedule.save()

        MaintenanceSchedule.objects.create(
            vehicle=self.vehicle,
            nombre_servicio="Filtro",
            intervalo_dias=90,
            ultima_fecha=self.today,
        )

        result = self.generate()

        self.assertEqual(
            (result.reviewed, result.created, result.existing),
            (1, 0, 0),
        )

        self.assertFalse(
            Reminder.objects.exists()
        )

    def test_next_cycle_can_generate_without_rewriting_previous_message(self):
        self.generate()

        original = Reminder.objects.get()
        message = original.mensaje

        self.schedule.ultima_fecha += timedelta(days=30)
        self.schedule.save()

        result = generate_reminders(
            current_date=self.today + timedelta(days=30)
        )

        self.assertEqual(
            result.created,
            1,
        )

        self.assertEqual(
            Reminder.objects.values(
                "ciclo"
            ).distinct().count(),
            2,
        )

        original.refresh_from_db()

        self.assertEqual(
            original.whatsapp_message,
            message,
        )

    def test_database_rejects_duplicate_automatic_notice(self):
        self.generate()

        reminder = Reminder.objects.get()

        with self.assertRaises(ValidationError):
            Reminder.objects.create(
                maintenance_schedule=self.schedule,
                tipo=reminder.tipo,
                ciclo=reminder.ciclo,
                fecha_programada=self.today,
            )

    def test_existing_manual_records_remain_unchanged(self):
        manual = Reminder.objects.create(
            maintenance_schedule=self.schedule,
            fecha_programada=self.today,
            mensaje="Seguimiento anterior",
            estado=Reminder.Status.COMPLETADO,
        )

        self.generate()

        manual.refresh_from_db()

        self.assertEqual(
            manual.tipo,
            Reminder.Type.MANUAL,
        )

        self.assertEqual(
            manual.mensaje,
            "Seguimiento anterior",
        )

        self.assertEqual(
            manual.estado,
            Reminder.Status.COMPLETADO,
        )

    def test_command_reports_counts_and_is_idempotent(self):
        for created, existing in [
            (1, 0),
            (0, 1),
        ]:
            output = StringIO()

            with patch(
                "reminders.services.timezone.localdate",
                return_value=self.today,
            ):
                call_command(
                    "generar_recordatorios",
                    stdout=output,
                )

            self.assertIn(
                "Mantenimientos revisados: 1",
                output.getvalue(),
            )

            self.assertIn(
                f"Recordatorios creados: {created}",
                output.getvalue(),
            )

            self.assertIn(
                f"Recordatorios existentes: {existing}",
                output.getvalue(),
            )

    def test_whatsapp_encodes_saved_or_custom_message_and_normalizes_phone(self):
        self.generate()

        reminder = Reminder.objects.get()

        reminder.mensaje = (
            "Atención Ana: aceite & filtro / revisión + motor."
        )
        reminder.save()

        parsed = urlparse(
            reminder.whatsapp_url
        )

        self.assertEqual(
            parsed.netloc,
            "wa.me",
        )

        self.assertEqual(
            parsed.path,
            "/50255551234",
        )

        self.assertEqual(
            parse_qs(parsed.query)["text"],
            [reminder.mensaje],
        )

    def test_instance_and_bulk_deletion_are_blocked(self):
        self.generate()

        reminder = Reminder.objects.get()

        with self.assertRaises(ValidationError):
            reminder.delete()

        with self.assertRaises(ValidationError):
            Reminder.objects.filter(
                pk=reminder.pk
            ).delete()

        self.assertTrue(
            Reminder.objects.filter(
                pk=reminder.pk
            ).exists()
        )

    def test_automatic_notice_cannot_be_reassigned_in_form(self):
        self.generate()

        reminder = Reminder.objects.get()

        other = MaintenanceSchedule.objects.create(
            vehicle=self.vehicle,
            nombre_servicio="Otro servicio",
            intervalo_dias=30,
            ultima_fecha=self.today,
        )

        form = ReminderForm(
            {
                "maintenance_schedule": other.pk,
                "fecha_programada": self.today,
                "mensaje": reminder.mensaje,
            },
            instance=reminder,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.save().maintenance_schedule_id,
            self.schedule.pk,
        )


class PhaseIVViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="fase_iv",
            password="contrasena-segura",
            is_staff=True,
            is_superuser=True,
        )

        owner = Owner.objects.create(
            tipo=Owner.OwnerType.PERSONA,
            nombre="Ana Pérez",
            telefono="+502 5555-1234",
        )

        cls.vehicle = Vehicle.objects.create(
            owner=owner,
            tipo="Automóvil",
            marca="Toyota",
            modelo="Corolla",
            anio=2025,
            placa="P123ABC",
            kilometraje_actual=10000,
            estado="ACTIVO",
            perfil_uso=Vehicle.UsageProfile.NORMAL,
        )

        cls.schedule = MaintenanceSchedule.objects.create(
            vehicle=cls.vehicle,
            nombre_servicio="Cambio de aceite",
            intervalo_dias=30,
            ultima_fecha=timezone.localdate() - timedelta(days=23),
            intervalo_km=5000,
            ultimo_kilometraje=5500,
        )

    def setUp(self):
        self.client.force_login(
            self.user
        )

        generate_reminders()

        self.reminder = Reminder.objects.get()

    def test_contact_and_complete_keep_contact_timestamp_and_history(self):
        self.client.post(
            f"/recordatorios/{self.reminder.pk}/contactado/"
        )

        self.reminder.refresh_from_db()

        self.assertEqual(
            self.reminder.estado,
            Reminder.Status.CONTACTADO,
        )

        contacted_at = self.reminder.contactado_at

        self.assertIsNotNone(
            contacted_at
        )

        self.client.post(
            f"/recordatorios/{self.reminder.pk}/contactado/"
        )

        self.reminder.refresh_from_db()

        self.assertEqual(
            self.reminder.contactado_at,
            contacted_at,
        )

        response = self.client.post(
            f"/recordatorios/{self.reminder.pk}/completado/"
        )

        self.assertRedirects(
            response,
            f"/recordatorios/{self.reminder.pk}/",
        )

        self.reminder.refresh_from_db()

        self.assertEqual(
            self.reminder.estado,
            Reminder.Status.COMPLETADO,
        )

        self.assertEqual(
            self.reminder.contactado_at,
            contacted_at,
        )

        self.assertEqual(
            generate_reminders().created,
            0,
        )

    def test_cancelled_followup_cannot_reopen_or_complete(self):
        self.client.post(
            f"/recordatorios/{self.reminder.pk}/cancelado/"
        )

        for action in [
            "contactado",
            "completado",
        ]:
            self.client.post(
                f"/recordatorios/{self.reminder.pk}/{action}/"
            )

            self.reminder.refresh_from_db()

            self.assertEqual(
                self.reminder.estado,
                Reminder.Status.CANCELADO,
            )

        self.assertEqual(
            generate_reminders().created,
            0,
        )

    def test_state_actions_require_post_and_authentication(self):
        for action in [
            "contactado",
            "completado",
            "cancelado",
        ]:
            url = (
                f"/recordatorios/"
                f"{self.reminder.pk}/"
                f"{action}/"
            )

            self.assertEqual(
                self.client.get(url).status_code,
                405,
            )

            self.client.logout()

            response = self.client.post(
                url
            )

            self.assertRedirects(
                response,
                f"/login/?next={url}",
            )

            self.client.force_login(
                self.user
            )

    def test_dashboard_shows_both_due_targets_and_only_active_alerts(self):
        MaintenanceSchedule.objects.create(
            vehicle=self.vehicle,
            nombre_servicio="Inactivo vencido",
            activo=False,
            intervalo_dias=1,
            ultima_fecha=(
                timezone.localdate()
                - timedelta(days=2)
            ),
        )

        response = self.client.get("/")

        self.assertEqual(
            response.context["upcoming_maintenance"],
            1,
        )

        self.assertEqual(
            response.context["overdue_maintenance"],
            0,
        )

        self.assertEqual(
            response.context["pending_reminders"],
            1,
        )

        for text in [
            "Ana Pérez",
            "Toyota Corolla",
            "P123ABC",
            "10500",
            "Próxima fecha",
            "Próximo kilometraje",
        ]:
            self.assertContains(
                response,
                text,
            )

        self.assertNotContains(
            response,
            "Inactivo vencido",
        )

    def test_dashboard_prioritizes_overdue_before_upcoming(self):
        overdue = MaintenanceSchedule.objects.create(
            vehicle=self.vehicle,
            nombre_servicio="Filtro vencido",
            intervalo_dias=1,
            ultima_fecha=(
                timezone.localdate()
                - timedelta(days=2)
            ),
        )

        response = self.client.get("/")

        self.assertEqual(
            response.context["priority_maintenance"][0],
            overdue,
        )

        self.assertEqual(
            response.context["overdue_maintenance"],
            1,
        )

    def test_list_filters_badges_and_whatsapp(self):
        response = self.client.get(
            "/recordatorios/",
            {
                "placa": "123",
                "propietario": "Pérez",
                "estado": "PENDIENTE",
            },
        )

        self.assertEqual(
            list(response.context["reminders"]),
            [self.reminder],
        )

        for text in [
            "Pendiente de hoy",
            "Mantenimiento próximo",
            "Toyota Corolla",
            "Enviar por WhatsApp",
            "wa.me/50255551234",
        ]:
            self.assertContains(
                response,
                text,
            )

        self.assertEqual(
            len(
                self.client.get(
                    "/recordatorios/?placa=OTRA"
                ).context["reminders"]
            ),
            0,
        )

        self.assertEqual(
            len(
                self.client.get(
                    "/recordatorios/?estado=COMPLETADO"
                ).context["reminders"]
            ),
            0,
        )

        self.assertEqual(
            len(
                self.client.get(
                    "/recordatorios/?propietario=OTRO"
                ).context["reminders"]
            ),
            0,
        )

    def test_list_marks_overdue_maintenance_and_late_followup(self):
        self.schedule.ultima_fecha -= timedelta(
            days=8
        )
        self.schedule.save()

        self.reminder.fecha_programada -= timedelta(
            days=1
        )
        self.reminder.save()

        response = self.client.get(
            "/recordatorios/"
        )

        self.assertContains(
            response,
            "Mantenimiento vencido",
        )

        self.assertContains(
            response,
            "Seguimiento atrasado",
        )

    def test_loading_pages_never_generates_reminders(self):
        self.schedule.ultima_fecha -= timedelta(
            days=8
        )
        self.schedule.save()

        for _ in range(2):
            self.client.get("/")
            self.client.get("/mantenimiento/")
            self.client.get("/recordatorios/")

        self.assertEqual(
            Reminder.objects.count(),
            1,
        )

    def test_admin_cannot_delete_history(self):
        model_admin = admin.site._registry[
            Reminder
        ]

        request = RequestFactory().get(
            "/admin/"
        )

        request.user = self.user

        self.assertFalse(
            model_admin.has_delete_permission(
                request,
                self.reminder,
            )
        )

        self.assertNotIn(
            "delete_selected",
            model_admin.get_actions(request),
        )

        response = self.client.post(
            f"/admin/reminders/reminder/"
            f"{self.reminder.pk}/delete/",
            {
                "post": "yes",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            Reminder.objects.filter(
                pk=self.reminder.pk
            ).exists()
        )