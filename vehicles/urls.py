from django.urls import path

from . import views


app_name = "vehicles"

urlpatterns = [
    path("", views.vehicle_list, name="list"),
    path("nuevo/", views.vehicle_create, name="create"),
    path("<int:pk>/", views.vehicle_detail, name="detail"),
    path("<int:pk>/editar/", views.vehicle_update, name="update"),
]