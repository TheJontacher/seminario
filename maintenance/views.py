from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MaintenanceScheduleForm
from .models import MaintenanceSchedule


STATUS_PRIORITY = {
	MaintenanceSchedule.MaintenanceStatus.VENCIDO: 0,
	MaintenanceSchedule.MaintenanceStatus.PROXIMO: 1,
	MaintenanceSchedule.MaintenanceStatus.AL_DIA: 2,
}


def schedule_queryset():
	return MaintenanceSchedule.objects.select_related("vehicle", "vehicle__owner")


def schedules_with_status(queryset):
	schedules = list(queryset)
	for schedule in schedules:
		schedule.calculated_status = schedule.get_status()
	return sorted(schedules, key=lambda item: STATUS_PRIORITY[item.calculated_status])


@login_required
def schedule_list(request):
	status = request.GET.get("estado", "")
	plate = request.GET.get("placa", "").strip()
	owner = request.GET.get("propietario", "").strip()
	schedules = schedule_queryset()
	if plate:
		schedules = schedules.filter(vehicle__placa__icontains=plate)
	if owner:
		schedules = schedules.filter(vehicle__owner__nombre__icontains=owner)
	schedules = schedules_with_status(schedules)
	if status:
		schedules = [schedule for schedule in schedules if schedule.calculated_status == status]
	return render(
		request,
		"maintenance/schedule_list.html",
		{
			"schedules": schedules,
			"status": status,
			"plate": plate,
			"owner_search": owner,
			"status_choices": MaintenanceSchedule.MaintenanceStatus.choices,
		},
	)


@login_required
def schedule_create(request):
	initial = {}
	vehicle_id = request.GET.get("vehicle")
	if vehicle_id and not request.POST:
		initial["vehicle"] = vehicle_id
	if request.method == "POST":
		form = MaintenanceScheduleForm(request.POST)
		if form.is_valid():
			try:
				schedule = form.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, "Mantenimiento creado correctamente.")
				return redirect("maintenance:detail", pk=schedule.pk)
	else:
		form = MaintenanceScheduleForm(initial=initial)
	return render(
		request,
		"maintenance/schedule_form.html",
		{"form": form, "form_title": "Nuevo mantenimiento"},
	)


@login_required
def schedule_detail(request, pk):
	schedule = get_object_or_404(schedule_queryset(), pk=pk)
	schedule.calculated_status = schedule.get_status()
	return render(request, "maintenance/schedule_detail.html", {"schedule": schedule})


@login_required
def schedule_update(request, pk):
	schedule = get_object_or_404(schedule_queryset(), pk=pk)
	if request.method == "POST":
		form = MaintenanceScheduleForm(request.POST, instance=schedule)
		if form.is_valid():
			try:
				schedule = form.save()
			except ValidationError as error:
				form.add_error(None, error)
			else:
				messages.success(request, "Mantenimiento actualizado correctamente.")
				return redirect("maintenance:detail", pk=schedule.pk)
	else:
		form = MaintenanceScheduleForm(instance=schedule)
	return render(
		request,
		"maintenance/schedule_form.html",
		{"form": form, "form_title": "Editar mantenimiento", "schedule": schedule},
	)

# Create your views here.
