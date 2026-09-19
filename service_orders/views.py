from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrderStatusForm, ServiceOrderForm, ServicePerformedForm
from .models import ServiceOrder


def order_queryset():
	return ServiceOrder.objects.select_related(
		"vehicle",
		"vehicle__owner",
		"mechanic",
	)


@login_required
def order_list(request):
	status = request.GET.get("estado", "")
	plate = request.GET.get("placa", "").strip()
	owner = request.GET.get("propietario", "").strip()
	orders = order_queryset()
	if status:
		orders = orders.filter(estado=status)
	if plate:
		orders = orders.filter(vehicle__placa__icontains=plate)
	if owner:
		orders = orders.filter(vehicle__owner__nombre__icontains=owner)
	return render(
		request,
		"service_orders/order_list.html",
		{
			"orders": orders,
			"status": status,
			"plate": plate,
			"owner_search": owner,
			"status_choices": ServiceOrder.Status.choices,
		},
	)


@login_required
def order_create(request):
	if request.method == "POST":
		form = ServiceOrderForm(request.POST)
		if form.is_valid():
			order = form.save(commit=False)
			order.estado = ServiceOrder.Status.RECIBIDO
			try:
				order.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, f"Orden #{order.pk} creada correctamente.")
				return redirect("service_orders:detail", pk=order.pk)
	else:
		form = ServiceOrderForm()
	return render(
		request,
		"service_orders/order_form.html",
		{"form": form, "form_title": "Nueva orden de servicio", "is_create": True},
	)


@login_required
def order_detail(request, pk):
	order = get_object_or_404(
		order_queryset().prefetch_related("services_performed", "status_history"),
		pk=pk,
	)
	return render(request, "service_orders/order_detail.html", {"order": order})


@login_required
def order_update(request, pk):
	order = get_object_or_404(order_queryset(), pk=pk)
	if request.method == "POST":
		form = ServiceOrderForm(request.POST, instance=order)
		if form.is_valid():
			try:
				order = form.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, f"Orden #{order.pk} actualizada correctamente.")
				return redirect("service_orders:detail", pk=order.pk)
	else:
		form = ServiceOrderForm(instance=order)
	return render(
		request,
		"service_orders/order_form.html",
		{"form": form, "form_title": "Editar orden de servicio", "order": order},
	)


@login_required
def service_create(request, pk):
	order = get_object_or_404(order_queryset(), pk=pk)
	if request.method == "POST":
		form = ServicePerformedForm(request.POST)
		if form.is_valid():
			service = form.save(commit=False)
			service.service_order = order
			try:
				service.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, "Servicio realizado agregado correctamente.")
				return redirect("service_orders:detail", pk=order.pk)
	else:
		form = ServicePerformedForm()
	return render(
		request,
		"service_orders/service_form.html",
		{"form": form, "order": order},
	)


@login_required
def order_status_update(request, pk):
	order = get_object_or_404(order_queryset(), pk=pk)
	if request.method == "POST":
		form = OrderStatusForm(
			request.POST,
			current_status=order.estado,
		)
		if form.is_valid():
			order.estado = form.cleaned_data["nuevo_estado"]
			try:
				order.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, "Estado de la orden actualizado correctamente.")
				return redirect("service_orders:detail", pk=order.pk)
	else:
		form = OrderStatusForm(current_status=order.estado)
	return render(
		request,
		"service_orders/status_form.html",
		{"form": form, "order": order},
	)
