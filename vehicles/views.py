from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VehicleForm
from .models import Vehicle


@login_required
def vehicle_list(request):
	search = request.GET.get("q", "").strip()
	vehicles = Vehicle.objects.select_related("owner")
	if search:
		vehicles = vehicles.filter(
			Q(placa__icontains=search)
			| Q(marca__icontains=search)
			| Q(modelo__icontains=search)
			| Q(owner__nombre__icontains=search)
		)
	return render(
		request,
		"vehicles/vehicle_list.html",
		{"vehicles": vehicles, "search": search},
	)


@login_required
def vehicle_create(request):
	if request.method == "POST":
		form = VehicleForm(request.POST)
		if form.is_valid():
			vehicle = form.save()
			messages.success(request, f"Vehículo {vehicle.placa} creado correctamente.")
			return redirect("vehicles:detail", pk=vehicle.pk)
	else:
		form = VehicleForm()
	return render(
		request,
		"vehicles/vehicle_form.html",
		{"form": form, "form_title": "Nuevo vehículo"},
	)


@login_required
def vehicle_detail(request, pk):
	vehicle = get_object_or_404(
		Vehicle.objects.select_related("owner").prefetch_related("service_orders"),
		pk=pk,
	)
	return render(request, "vehicles/vehicle_detail.html", {"vehicle": vehicle})


@login_required
def vehicle_update(request, pk):
	vehicle = get_object_or_404(Vehicle, pk=pk)
	if request.method == "POST":
		form = VehicleForm(request.POST, instance=vehicle)
		if form.is_valid():
			vehicle = form.save()
			messages.success(request, f"Vehículo {vehicle.placa} actualizado correctamente.")
			return redirect("vehicles:detail", pk=vehicle.pk)
	else:
		form = VehicleForm(instance=vehicle)
	return render(
		request,
		"vehicles/vehicle_form.html",
		{"form": form, "form_title": "Editar vehículo", "vehicle": vehicle},
	)
