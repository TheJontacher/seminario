from django.contrib import admin

from .models import MaintenanceSchedule


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
	list_display = (
		"nombre_servicio",
		"vehicle",
		"intervalo_km",
		"intervalo_dias",
		"activo",
	)
	list_filter = ("activo",)
	search_fields = ("nombre_servicio", "vehicle__placa", "vehicle__marca")
