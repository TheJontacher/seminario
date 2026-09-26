from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from owners.models import Owner
from maintenance.models import MaintenanceSchedule
from reminders.models import Reminder
from service_orders.models import ServiceOrder
from vehicles.models import Vehicle


@login_required
def home(request):
    order_metrics = ServiceOrder.objects.aggregate(
        received=Count("id", filter=Q(estado=ServiceOrder.Status.RECIBIDO)),
        in_progress=Count("id", filter=Q(estado=ServiceOrder.Status.EN_PROCESO)),
        stopped=Count(
            "id",
            filter=Q(estado=ServiceOrder.Status.DETENIDO_REPUESTOS),
        ),
        finished=Count("id", filter=Q(estado=ServiceOrder.Status.TERMINADO)),
    )
    schedules = list(
        MaintenanceSchedule.objects.filter(activo=True).select_related(
            "vehicle", "vehicle__owner"
        )
    )
    status_priority = {
        MaintenanceSchedule.MaintenanceStatus.VENCIDO: 0,
        MaintenanceSchedule.MaintenanceStatus.PROXIMO: 1,
        MaintenanceSchedule.MaintenanceStatus.AL_DIA: 2,
    }
    for schedule in schedules:
        schedule.calculated_status = schedule.get_status()
    schedules = [
        schedule
        for schedule in schedules
        if schedule.calculated_status
        in {
            MaintenanceSchedule.MaintenanceStatus.VENCIDO,
            MaintenanceSchedule.MaintenanceStatus.PROXIMO,
        }
    ]
    schedules.sort(key=lambda item: status_priority[item.calculated_status])
    context = {
        "total_owners": Owner.objects.count(),
        "total_vehicles": Vehicle.objects.count(),
        "order_metrics": order_metrics,
        "overdue_maintenance": sum(
            schedule.calculated_status == MaintenanceSchedule.MaintenanceStatus.VENCIDO
            for schedule in schedules
        ),
        "upcoming_maintenance": sum(
            schedule.calculated_status == MaintenanceSchedule.MaintenanceStatus.PROXIMO
            for schedule in schedules
        ),
        "priority_maintenance": schedules[:5],
        "pending_reminders": Reminder.objects.filter(
            estado=Reminder.Status.PENDIENTE
        ).count(),
    }
    return render(request, "home.html", context)