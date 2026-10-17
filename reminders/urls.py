from django.urls import path

from . import views


app_name = "reminders"

urlpatterns = [
    path("", views.reminder_list, name="list"),
    path("nuevo/", views.reminder_create, name="create"),
    path("<int:pk>/", views.reminder_detail, name="detail"),
    path("<int:pk>/editar/", views.reminder_update, name="update"),
    path("<int:pk>/contactado/", views.reminder_contacted, name="contacted"),
    path("<int:pk>/completado/", views.reminder_completed, name="completed"),
    path("<int:pk>/cancelado/", views.reminder_cancelled, name="cancelled"),
]
