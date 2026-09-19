from django.contrib import admin

from .models import Owner


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
	list_display = ("nombre", "tipo", "telefono", "activo")
	list_filter = ("tipo", "activo")
	search_fields = ("nombre", "telefono", "email")
