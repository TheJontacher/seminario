from django.core.management.base import BaseCommand

from reminders.services import generate_reminders


class Command(BaseCommand):
    help = "Genera recordatorios de mantenimientos activos próximos o vencidos sin duplicarlos."

    def handle(self, *args, **options):
        result = generate_reminders()
        self.stdout.write(f"Mantenimientos revisados: {result.reviewed}")
        self.stdout.write(f"Recordatorios creados: {result.created}")
        self.stdout.write(f"Recordatorios existentes: {result.existing}")
