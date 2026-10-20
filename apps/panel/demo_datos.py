"""Datos fijos de la demostración: marca, clientes de la Carta, sitios y productos."""

from decimal import Decimal

CLAVE_DEMO = "demo1234"

# Marca de los datos de demo. Va al comienzo de `notas` de clientes y sitios.
MARCA_DEMO = "[demo] Datos de demostración generados por cargar_demo."
SUFIJO_PRODUCTO = " (demo)"
# Formato anterior de `cargar_demo`: también se considera demo para limpiarlo.
PATRON_CLIENTE_VIEJO = r"^Cliente Demo \d+$"
SLUG_TIPO_VIEJO = "demo-control-de-plagas"

TELEFONO_FICTICIO = "0000-000000"
# Tipos reales (slug y nombre del fixture); si faltan se crean sin pisar nada.
TIPOS = {
    "control-plagas-urbanas": "Control de plagas urbanas",
    "servicio-mipu": "Servicio MIPU (Manejo Integral de Plagas Urbanas)",
}

# Razones sociales de clientes reales de la empresa, usadas como nombres de demo.
CLIENTES = ("Nutrisur", "Villa del Sur", "Super Beef", "Howard Johnson")

# Coordenadas reales de las localidades; los sitios se corren unos metros.
CASTELLI = (Decimal("-36.087000"), Decimal("-57.793000"))
CHASCOMUS = (Decimal("-35.573600"), Decimal("-58.009700"))

# cliente, nombre, dirección, localidad, sector, puntos además de "General".
# El primer sitio lleva el plano: sus puntos se reparten en las salas dibujadas.
SITIOS = (
    (
        "Nutrisur",
        "Planta Castelli",
        "Ruta 2 km 112",
        "Castelli",
        "industria",
        [
            "Recepción de materia prima",
            "Cámara de frío",
            "Depósito de insumos",
            "Sala de envasado",
            "Muelle de carga",
            "Comedor",
        ],
    ),
    (
        "Nutrisur",
        "Depósito Chascomús",
        "Ruta 2 km 121",
        "Chascomús",
        "industria",
        ["Playa de maniobras", "Nave principal", "Oficina"],
    ),
    (
        "Villa del Sur",
        "Planta de elaboración",
        "Calle 9 s/n",
        "Castelli",
        "industria",
        ["Ingreso", "Sala de proceso", "Depósito", "Patio"],
    ),
    (
        "Villa del Sur",
        "Centro de distribución",
        "Calle 14 s/n",
        "Chascomús",
        "industria",
        ["Andén", "Cámara"],
    ),
    (
        "Super Beef",
        "Frigorífico",
        "Ruta 2 km 109",
        "Castelli",
        "industria",
        ["Corrales", "Faena", "Cámara de frío"],
    ),
    (
        "Howard Johnson",
        "Hotel Chascomús",
        "Calle 6 s/n",
        "Chascomús",
        "hoteleria",
        ["Cocina", "Subsuelo"],
    ),
)

# (nombre comercial sin sufijo, principio activo, presentación, unidad de dosis,
# registro, unidad base, contenido por envase, modo de unidad, envases del ingreso
# inicial): masa, conteo y volumen, con unidades equivalentes o solo la base.
PRODUCTOS = (
    (
        "Gel cucarachicida",
        "Fipronil",
        "Jeringa 30 g",
        "g",
        "DEMO-001",
        "g",
        Decimal("30"),
        "equivalentes",
        Decimal("400"),
    ),
    (
        "Cebo rodenticida en bloque",
        "Brodifacoum",
        "Caja de 50 bloques",
        "g",
        "DEMO-002",
        "unidad",
        Decimal("50"),
        "unica",
        Decimal("100"),
    ),
    (
        "Insecticida residual",
        "Cipermetrina",
        "Concentrado 1 l",
        "ml/l",
        "DEMO-003",
        "l",
        Decimal("1"),
        "equivalentes",
        Decimal("200"),
    ),
)

# Planilla de punto que se usa si el tipo de servicio no declara campos.
ESQUEMA_PUNTO = [
    {
        "clave": "actividad",
        "etiqueta": "Nivel de actividad",
        "tipo": "opcion",
        "opciones": ["Sin actividad", "Baja", "Media", "Alta"],
        "obligatorio": True,
        "ayuda": "",
        "orden": 1,
    },
    {
        "clave": "cebos_repuestos",
        "etiqueta": "Cebos repuestos",
        "tipo": "numero",
        "opciones": [],
        "obligatorio": False,
        "ayuda": "",
        "orden": 2,
    },
    {
        "clave": "estacion_en_buen_estado",
        "etiqueta": "Estación en buen estado",
        "tipo": "booleano",
        "opciones": [],
        "obligatorio": False,
        "ayuda": "",
        "orden": 3,
    },
]

# Días desde la última jornada de cada sitio hasta hoy; el sitio de `PENDIENTE`
# tiene un turno por delante y el de `ABIERTO`, uno abierto.
DESFASES = (1, 3, 5, 8, 12, 16)
SITIO_CON_PENDIENTE = 3
SITIO_CON_ABIERTO = 1
CADENCIA_HISTORIA_DIAS = 14
DIAS_DE_HISTORIA = 92

# Frecuencia (días) de los puntos, por turnos, y días hasta su próximo vencimiento
# (negativo: vencido; `None`: sin programar y sin frecuencia).
FRECUENCIAS = (7, 14, 30)
VENCIMIENTOS = (-3, 4, 20, None, 45, -1)

# (sitio, jornada, punto): revisiones hechas lejos del punto. La jornada 0 es
# la más reciente.
INCIDENCIAS_UBICACION = {(0, 1): {2}, (2, 2): {1}, (4, 1): {3}}
