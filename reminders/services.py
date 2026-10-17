from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from maintenance.models import MaintenanceSchedule

from .models import Reminder


@dataclass
class GenerationResult:
    reviewed: int = 0
    created: int = 0
    existing: int = 0


def generate_reminders(*, current_date=None):
    """Generate one notice per type and due cycle, including closed history."""
    current_date = current_date or timezone.localdate()
    result = GenerationResult()
    schedule_ids = MaintenanceSchedule.objects.filter(activo=True).values_list(
        "pk", flat=True
    )
    for schedule_id in schedule_ids.iterator():
        with transaction.atomic():
            # Serialize concurrent generators and edits to this plan.
            schedule = (
                MaintenanceSchedule.objects.select_for_update(of=("self",))
                .select_related("vehicle", "vehicle__owner")
                .filter(pk=schedule_id, activo=True)
                .first()
            )
            if schedule is None:
                continue
            result.reviewed += 1
            status = schedule.get_status(current_date=current_date)
            reminder_type = {
                MaintenanceSchedule.MaintenanceStatus.PROXIMO: Reminder.Type.PREVIO_7_DIAS,
                MaintenanceSchedule.MaintenanceStatus.VENCIDO: Reminder.Type.VENCIDO,
            }.get(status)
            if reminder_type is None:
                continue
            # Due targets identify a cycle without relying on nullable unique fields.
            cycle = f"{schedule.proxima_fecha}:{schedule.proximo_kilometraje}"
            draft = Reminder(maintenance_schedule=schedule, tipo=reminder_type)
            _, created = Reminder.objects.get_or_create(
                maintenance_schedule=schedule,
                tipo=reminder_type,
                ciclo=cycle,
                defaults={
                    "fecha_programada": current_date,
                    "mensaje": draft.generated_message,
                },
            )
            if created:
                result.created += 1
            else:
                result.existing += 1
    return result
