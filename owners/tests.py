from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Owner


class OwnerViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="usuario_propietarios",
            password="contrasena-segura",
        )
        self.client.force_login(self.user)
        self.owner_data = {
            "tipo": Owner.OwnerType.PERSONA,
            "nombre": "Ana Propietaria",
            "telefono": "3000000000",
            "email": "ana@example.com",
            "direccion": "Calle 1",
            "activo": "on",
        }

    def test_owner_list_requires_login(self):
        self.client.logout()

        response = self.client.get("/propietarios/")

        self.assertRedirects(response, "/login/?next=/propietarios/")

    def test_create_valid_owner(self):
        response = self.client.post("/propietarios/nuevo/", self.owner_data)

        owner = Owner.objects.get()
        self.assertRedirects(response, f"/propietarios/{owner.pk}/")
        self.assertEqual(owner.nombre, "Ana Propietaria")

    def test_edit_owner(self):
        owner = Owner.objects.create(
            tipo=Owner.OwnerType.PERSONA,
            nombre="Nombre anterior",
            telefono="3000000000",
        )
        data = {**self.owner_data, "nombre": "Nombre actualizado"}

        response = self.client.post(f"/propietarios/{owner.pk}/editar/", data)

        owner.refresh_from_db()
        self.assertRedirects(response, f"/propietarios/{owner.pk}/")
        self.assertEqual(owner.nombre, "Nombre actualizado")

    def test_owner_detail_works(self):
        owner = Owner.objects.create(
            tipo=Owner.OwnerType.EMPRESA,
            nombre="Empresa de prueba",
            telefono="3000000000",
        )

        response = self.client.get(f"/propietarios/{owner.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa de prueba")

    def test_invalid_owner_form_does_not_save(self):
        invalid_data = {**self.owner_data, "nombre": ""}

        response = self.client.post("/propietarios/nuevo/", invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Owner.objects.count(), 0)
