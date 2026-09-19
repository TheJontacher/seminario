from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OwnerForm
from .models import Owner


@login_required
def owner_list(request):
	owners = Owner.objects.all()
	return render(request, "owners/owner_list.html", {"owners": owners})


@login_required
def owner_create(request):
	if request.method == "POST":
		form = OwnerForm(request.POST)
		if form.is_valid():
			owner = form.save()
			messages.success(request, f"Propietario {owner.nombre} creado correctamente.")
			return redirect("owners:detail", pk=owner.pk)
	else:
		form = OwnerForm()
	return render(
		request,
		"owners/owner_form.html",
		{"form": form, "form_title": "Nuevo propietario"},
	)


@login_required
def owner_detail(request, pk):
	owner = get_object_or_404(
		Owner.objects.prefetch_related("vehicles"),
		pk=pk,
	)
	return render(request, "owners/owner_detail.html", {"owner": owner})


@login_required
def owner_update(request, pk):
	owner = get_object_or_404(Owner, pk=pk)
	if request.method == "POST":
		form = OwnerForm(request.POST, instance=owner)
		if form.is_valid():
			owner = form.save()
			messages.success(request, f"Propietario {owner.nombre} actualizado correctamente.")
			return redirect("owners:detail", pk=owner.pk)
	else:
		form = OwnerForm(instance=owner)
	return render(
		request,
		"owners/owner_form.html",
		{"form": form, "form_title": "Editar propietario", "owner": owner},
	)
