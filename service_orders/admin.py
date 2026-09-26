from django.contrib import admin

from .models import Mechanic, OrderStatusHistory, ServiceOrder, ServicePerformed


@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
	list_display = ("nombre", "telefono", "activo")
	list_filter = ("activo",)
	search_fields = ("nombre", "telefono")


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
	list_display = ("id", "vehicle", "mechanic", "fecha_ingreso", "estado")
	list_filter = ("estado", "fecha_ingreso")
	search_fields = ("vehicle__placa", "vehicle__marca", "motivo_ingreso")

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(ServicePerformed)
class ServicePerformedAdmin(admin.ModelAdmin):
	list_display = ("nombre", "service_order", "es_preventivo", "created_at")
	list_filter = ("es_preventivo",)
	search_fields = ("nombre", "service_order__vehicle__placa")

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
	list_display = (
		"service_order",
		"estado_anterior",
		"estado_nuevo",
		"fecha_hora",
	)
	list_filter = ("estado_anterior", "estado_nuevo")
	search_fields = ("service_order__vehicle__placa",)

	def has_delete_permission(self, request, obj=None):
		return False
