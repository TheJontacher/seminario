from django.urls import path

from . import views


app_name = "mechanics"

urlpatterns = [
    path("", views.mechanic_list, name="list"),
    path("nuevo/", views.mechanic_create, name="create"),
    path("<int:pk>/", views.mechanic_detail, name="detail"),
    path("<int:pk>/editar/", views.mechanic_update, name="update"),
]