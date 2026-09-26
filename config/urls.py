from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path(
        "admin/login/",
        RedirectView.as_view(url="/login/", query_string=True),
        name="admin-login-redirect",
    ),
    path("admin/", admin.site.urls),
    path(
        "login/",
        LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("propietarios/", include("owners.urls")),
    path("vehiculos/", include("vehicles.urls")),
    path("ordenes/", include("service_orders.urls")),
    path("mantenimiento/", include("maintenance.urls")),
    path("recordatorios/", include("reminders.urls")),
    path("mecanicos/", include("service_orders.mechanic_urls")),
    path("historial/", include("service_orders.history_urls")),
    path("", include("core.urls")),
]