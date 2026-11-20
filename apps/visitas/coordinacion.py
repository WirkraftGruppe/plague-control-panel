"""Coordinación entre operarios: quién revisó o tiene asignado un punto hoy."""

from collections import defaultdict

from django.utils import timezone

from apps.visitas.models import ItemTurno, Revision, Visita


def nombre_de_empleado(usuario):
    """Nombre completo del usuario o, si no lo tiene, su nombre de usuario."""
    return usuario.get_full_name() or usuario.username


def revisiones_del_dia(empresa, punto_ids, fecha):
    """Revisiones de los puntos en el día local `fecha`, por punto.

    Devuelve `{punto_id: [(empleado_id, nombre, realizada_en), …]}` ordenado por
    `realizada_en`. Cuentan las revisiones de visitas que cuentan como servicio y no
    están canceladas (las mismas reglas que `contexto_de_puntos`). Una sola consulta.
    """
    revisiones = (
        Revision.objects.de_empresa(empresa)
        .filter(
            punto_id__in=punto_ids,
            realizada_en__date=fecha,
            visita__cuenta_como_servicio=True,
        )
        .exclude(visita__estado=Visita.Estado.CANCELADA)
        .select_related("visita__empleado")
        .order_by("realizada_en", "pk")
    )
    resultado = defaultdict(list)
    for revision in revisiones:
        empleado = revision.visita.empleado
        resultado[revision.punto_id].append(
            (empleado.pk, nombre_de_empleado(empleado), revision.realizada_en)
        )
    return dict(resultado)


def revisiones_de_hoy(empresa, punto_ids):
    """`revisiones_del_dia` con el día local de hoy."""
    return revisiones_del_dia(empresa, punto_ids, timezone.localdate())


def puntos_asignados_a_otros(empresa, punto_ids, empleado_id):
    """`{punto_id: nombre}` de los puntos en turnos pendientes o abiertos de otro.

    Con `empleado_id=None` cuenta a cualquier empleado. Una sola consulta.
    """
    items = (
        ItemTurno.objects.de_empresa(empresa)
        .filter(
            punto_id__in=punto_ids,
            visita__estado__in=[Visita.Estado.PENDIENTE, Visita.Estado.ABIERTA],
        )
        .select_related("visita__empleado")
        .order_by("visita_id", "pk")
    )
    if empleado_id is not None:
        items = items.exclude(visita__empleado_id=empleado_id)
    resultado = {}
    for item in items:
        resultado.setdefault(item.punto_id, nombre_de_empleado(item.visita.empleado))
    return resultado
