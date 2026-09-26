from django.contrib import admin

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
	list_display = (
		"fecha_programada",
		"maintenance_schedule",
		"estado",
		"contactado_at",
	)
	list_filter = ("estado", "fecha_programada")
	search_fields = (
		"maintenance_schedule__nombre_servicio",
		"maintenance_schedule__vehicle__placa",
		"maintenance_schedule__vehicle__owner__nombre",
	)

	def has_delete_permission(self, request, obj=None):
		return False
