from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from owners.models import Owner
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
    context = {
        "total_owners": Owner.objects.count(),
        "total_vehicles": Vehicle.objects.count(),
        "order_metrics": order_metrics,
    }
    return render(request, "home.html", context)