from django.urls import path

from . import views


app_name = "service_orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("nueva/", views.order_create, name="create"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/editar/", views.order_update, name="update"),
    path("<int:pk>/servicios/nuevo/", views.service_create, name="service_create"),
    path("<int:pk>/estado/", views.order_status_update, name="status_update"),
]