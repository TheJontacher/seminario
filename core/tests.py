from django.contrib.auth import get_user_model
from django.test import TestCase


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="usuario_prueba",
            password="contrasena-segura",
        )

    def test_anonymous_user_is_redirected_from_home(self):
        response = self.client.get("/")

        self.assertRedirects(response, "/login/?next=/")

    def test_login_page_renders(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesión")

    def test_admin_login_redirects_to_public_login(self):
        response = self.client.get("/admin/login/?next=/admin/")

        self.assertRedirects(response, "/login/?next=%2Fadmin%2F")

    def test_authenticated_user_can_access_home(self):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")

    def test_valid_login_works(self):
        response = self.client.post(
            "/login/",
            {"username": "usuario_prueba", "password": "contrasena-segura"},
        )

        self.assertRedirects(response, "/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_works(self):
        self.client.force_login(self.user)

        response = self.client.post("/logout/")

        self.assertRedirects(response, "/login/")
        home_response = self.client.get("/")
        self.assertRedirects(home_response, "/login/?next=/")