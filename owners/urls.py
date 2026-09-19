from django.urls import path

from . import views


app_name = "owners"

urlpatterns = [
    path("", views.owner_list, name="list"),
    path("nuevo/", views.owner_create, name="create"),
    path("<int:pk>/", views.owner_detail, name="detail"),
    path("<int:pk>/editar/", views.owner_update, name="update"),
]