from django.contrib import admin

from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ("placa", "marca", "modelo", "owner", "estado")
	list_filter = ("tipo", "estado", "perfil_uso")
	search_fields = ("placa", "marca", "modelo", "owner__nombre")
