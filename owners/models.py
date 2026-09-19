from django.db import models


class Owner(models.Model):
	class OwnerType(models.TextChoices):
		PERSONA = "PERSONA", "Persona"
		EMPRESA = "EMPRESA", "Empresa"

	tipo = models.CharField(max_length=10, choices=OwnerType.choices)
	nombre = models.CharField(max_length=150)
	telefono = models.CharField(max_length=30)
	email = models.EmailField(blank=True)
	direccion = models.CharField(max_length=255, blank=True)
	activo = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["nombre"]
		verbose_name = "propietario"
		verbose_name_plural = "propietarios"

	def __str__(self):
		return self.nombre
