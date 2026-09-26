from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from .forms import MechanicForm, OrderStatusForm, ServiceOrderForm, ServicePerformedForm
from .models import Mechanic, ServiceOrder


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


@login_required
def mechanic_list(request):
	search = request.GET.get("q", "").strip()
	mechanics = Mechanic.objects.annotate(order_count=Count("service_orders"))
	if search:
		mechanics = mechanics.filter(nombre__icontains=search)
	return render(
		request,
		"service_orders/mechanic_list.html",
		{"mechanics": mechanics, "search": search},
	)


@login_required
def mechanic_create(request):
	if request.method == "POST":
		form = MechanicForm(request.POST)
		if form.is_valid():
			mechanic = form.save()
			messages.success(request, f"Mecánico {mechanic.nombre} creado correctamente.")
			return redirect("mechanics:detail", pk=mechanic.pk)
	else:
		form = MechanicForm()
	return render(
		request,
		"service_orders/mechanic_form.html",
		{"form": form, "form_title": "Nuevo mecánico"},
	)


@login_required
def mechanic_detail(request, pk):
	mechanic = get_object_or_404(
		Mechanic.objects.annotate(
			total_orders=Count("service_orders"),
			delivered_orders=Count(
				"service_orders",
				filter=Q(service_orders__estado=ServiceOrder.Status.ENTREGADO),
			),
			active_orders=Count(
				"service_orders",
				filter=~Q(service_orders__estado=ServiceOrder.Status.ENTREGADO),
			),
		),
		pk=pk,
	)
	orders = (
		ServiceOrder.objects.filter(mechanic=mechanic)
		.select_related("vehicle", "vehicle__owner")
		.annotate(service_count=Count("services_performed"))
		.order_by("-fecha_ingreso", "-created_at")[:10]
	)
	return render(
		request,
		"service_orders/mechanic_detail.html",
		{"mechanic": mechanic, "orders": orders},
	)


@login_required
def mechanic_update(request, pk):
	mechanic = get_object_or_404(Mechanic, pk=pk)
	if request.method == "POST":
		form = MechanicForm(request.POST, instance=mechanic)
		if form.is_valid():
			mechanic = form.save()
			messages.success(request, f"Mecánico {mechanic.nombre} actualizado correctamente.")
			return redirect("mechanics:detail", pk=mechanic.pk)
	else:
		form = MechanicForm(instance=mechanic)
	return render(
		request,
		"service_orders/mechanic_form.html",
		{"form": form, "form_title": "Editar mecánico", "mechanic": mechanic},
	)


@login_required
def global_history(request):
	orders = ServiceOrder.objects.select_related(
		"vehicle", "vehicle__owner", "mechanic"
	).annotate(service_count=Count("services_performed"))
	plate = request.GET.get("placa", "").strip()
	owner = request.GET.get("propietario", "").strip()
	mechanic_id = request.GET.get("mecanico", "").strip()
	status = request.GET.get("estado", "").strip()
	date_from_value = request.GET.get("desde", "").strip()
	date_to_value = request.GET.get("hasta", "").strip()
	date_from = parse_date(date_from_value)
	date_to = parse_date(date_to_value)
	if plate:
		orders = orders.filter(vehicle__placa__icontains=plate)
	if owner:
		orders = orders.filter(vehicle__owner__nombre__icontains=owner)
	if mechanic_id.isdigit():
		orders = orders.filter(mechanic_id=mechanic_id)
	if status in dict(ServiceOrder.Status.choices):
		orders = orders.filter(estado=status)
	if date_from:
		orders = orders.filter(fecha_ingreso__gte=date_from)
	if date_to:
		orders = orders.filter(fecha_ingreso__lte=date_to)
	orders = orders.order_by("-fecha_ingreso", "-created_at")
	page_obj = Paginator(orders, 25).get_page(request.GET.get("page"))
	return render(
		request,
		"service_orders/global_history.html",
		{
			"page_obj": page_obj,
			"orders": page_obj.object_list,
			"plate": plate,
			"owner_search": owner,
			"mechanic_id": mechanic_id,
			"status": status,
			"date_from": date_from_value,
			"date_to": date_to_value,
			"mechanics": Mechanic.objects.all(),
			"status_choices": ServiceOrder.Status.choices,
		},
	)
