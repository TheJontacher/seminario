from django.urls import path

from . import views


app_name = "maintenance"

urlpatterns = [
    path("", views.schedule_list, name="list"),
    path("nuevo/", views.schedule_create, name="create"),
    path("<int:pk>/", views.schedule_detail, name="detail"),
    path("<int:pk>/editar/", views.schedule_update, name="update"),
]