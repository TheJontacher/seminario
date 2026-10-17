from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ReminderForm
from .models import Reminder


def reminder_queryset():
    return Reminder.objects.select_related(
        "maintenance_schedule",
        "maintenance_schedule__vehicle",
        "maintenance_schedule__vehicle__owner",
    )


def reminder_priority(reminder, today=None):
    if today is None:
        today = timezone.localdate()

    if reminder.estado != Reminder.Status.PENDIENTE:
        return 3

    if reminder.fecha_programada < today:
        return 0

    if reminder.fecha_programada == today:
        return 1

    return 2


@login_required
def reminder_list(request):
    status = request.GET.get("estado", "")
    plate = request.GET.get("placa", "").strip()
    owner = request.GET.get("propietario", "").strip()

    reminders = reminder_queryset()

    if status:
        reminders = reminders.filter(estado=status)

    if plate:
        reminders = reminders.filter(
            maintenance_schedule__vehicle__placa__icontains=plate
        )

    if owner:
        reminders = reminders.filter(
            maintenance_schedule__vehicle__owner__nombre__icontains=owner
        )

    today = timezone.localdate()

    reminders = sorted(
        reminders,
        key=lambda reminder: reminder_priority(reminder, today)
    )

    for reminder in reminders:
        reminder.maintenance_status = (
            reminder.maintenance_schedule.get_status(current_date=today)
        )

    return render(
        request,
        "reminders/reminder_list.html",
        {
            "reminders": reminders,
            "status": status,
            "plate": plate,
            "owner_search": owner,
            "status_choices": Reminder.Status.choices,
            "today": today,
        },
    )


@login_required
def reminder_create(request):
    if request.method == "POST":
        form = ReminderForm(request.POST)

        if form.is_valid():
            try:
                reminder = form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(
                    request,
                    "Recordatorio creado correctamente."
                )
                return redirect("reminders:detail", pk=reminder.pk)

    else:
        form = ReminderForm()

    return render(
        request,
        "reminders/reminder_form.html",
        {
            "form": form,
            "form_title": "Nuevo recordatorio",
        },
    )


@login_required
def reminder_detail(request, pk):
    reminder = get_object_or_404(
        reminder_queryset(),
        pk=pk
    )

    return render(
        request,
        "reminders/reminder_detail.html",
        {
            "reminder": reminder,
            "maintenance_status": reminder.maintenance_schedule.get_status(),
        },
    )


@login_required
def reminder_update(request, pk):
    reminder = get_object_or_404(
        reminder_queryset(),
        pk=pk
    )

    if request.method == "POST":
        form = ReminderForm(
            request.POST,
            instance=reminder
        )

        if form.is_valid():
            try:
                reminder = form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(
                    request,
                    "Recordatorio actualizado correctamente."
                )
                return redirect(
                    "reminders:detail",
                    pk=reminder.pk
                )

    else:
        form = ReminderForm(instance=reminder)

    return render(
        request,
        "reminders/reminder_form.html",
        {
            "form": form,
            "form_title": "Editar recordatorio",
            "reminder": reminder,
        },
    )


@login_required
@require_POST
def reminder_contacted(request, pk):
    return change_reminder_status(
        request,
        pk,
        Reminder.Status.CONTACTADO
    )


@login_required
@require_POST
def reminder_completed(request, pk):
    return change_reminder_status(
        request,
        pk,
        Reminder.Status.COMPLETADO
    )


@login_required
@require_POST
def reminder_cancelled(request, pk):
    return change_reminder_status(
        request,
        pk,
        Reminder.Status.CANCELADO
    )


def change_reminder_status(request, pk, new_status):
    reminder = get_object_or_404(
        Reminder,
        pk=pk
    )

    try:
        reminder.change_status(new_status)
    except ValidationError as error:
        messages.error(
            request,
            " ".join(error.messages)
        )
    else:
        messages.success(
            request,
            f"Recordatorio marcado como "
            f"{reminder.get_estado_display().lower()}."
        )

    return redirect(
        "reminders:detail",
        pk=reminder.pk
    )