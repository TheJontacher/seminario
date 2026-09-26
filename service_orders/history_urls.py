from django.urls import path

from .views import global_history


urlpatterns = [
    path("", global_history, name="history"),
]