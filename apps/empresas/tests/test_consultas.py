"""Guardia de consultas por empresa, con modelos de prueba aislados del registro."""

from asgiref.sync import async_to_sync
from django.db import connection, models
from django.test import TestCase
from django.test.utils import isolate_apps

from apps.empresas.consultas import (
    ConsultaSinEmpresa,
    sin_filtro_empresa,
)
from apps.empresas.models import ModeloDeEmpresa
from apps.empresas.pruebas import crear_empresa


def _definir_modelos():
    """Un modelo raíz y un hijo con FK, solo para estos tests (no se registran)."""

    class Raiz(ModeloDeEmpresa):
        nombre = models.CharField(max_length=20)
        codigo = models.CharField(max_length=10, unique=True, blank=True, null=True)

        class Meta:
            app_label = "empresas"
            constraints = [
                models.UniqueConstraint(
                    fields=["empresa", "nombre"], name="raiz_prueba_nombre_unico"
                )
            ]

    class Hijo(ModeloDeEmpresa):
        raiz = models.ForeignKey(Raiz, on_delete=models.CASCADE, related_name="hijos")

        class Meta:
            app_label = "empresas"

    return Raiz, Hijo


class GuardiaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # Las tablas se crean antes de abrir la transacción de la clase: el editor
        # de esquema de SQLite no funciona dentro de una.
        cls._aislado = isolate_apps("apps.empresas")
        cls._aislado.enable()
        cls.Raiz, cls.Hijo = _definir_modelos()
        with connection.schema_editor() as editor:
            editor.create_model(cls.Raiz)
            editor.create_model(cls.Hijo)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            editor.delete_model(cls.Hijo)
            editor.delete_model(cls.Raiz)
        cls._aislado.disable()

    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Una")
        raiz = cls.Raiz.todos.create(empresa=cls.empresa, nombre="r")
        cls.Hijo.todos.create(empresa=cls.empresa, raiz=raiz)
        # Una segunda empresa con filas: los casos seguros no deben traerlas.
        cls.otra = crear_empresa("Otra")
        ajena = cls.Raiz.todos.create(empresa=cls.otra, nombre="ajena")
        cls.Hijo.todos.create(empresa=cls.otra, raiz=ajena)
        # Solo la clave: copiar instancias de modelos aislados no funciona.
        cls.raiz_pk = raiz.pk

    @property
    def raiz(self):
        return self.Raiz.todos.get(pk=self.raiz_pk)

    def test_consulta_sin_empresa_lanza(self):
        consultas = {
            "lista": lambda: list(self.Raiz.objects.all()),
            "iterator": lambda: list(self.Raiz.objects.all().iterator()),
            "count": self.Raiz.objects.count,
            "exists": self.Raiz.objects.exists,
            "aggregate": lambda: self.Raiz.objects.aggregate(n=models.Count("id")),
            "update": lambda: self.Raiz.objects.update(nombre="x"),
            "delete": self.Raiz.objects.all().delete,
            "get": lambda: self.Raiz.objects.get(pk=self.raiz.pk),
        }
        for nombre, consulta in consultas.items():
            with self.subTest(nombre), self.assertRaises(ConsultaSinEmpresa):
                consulta()
        self.assertEqual(self.Raiz.objects.de_empresa(self.empresa).count(), 1)

    def test_de_empresa_none_lanza(self):
        with self.assertRaises(ConsultaSinEmpresa):
            self.Raiz.objects.de_empresa(None)

    def test_none_relacionados_y_sin_filtro_no_lanzan(self):
        self.assertEqual(list(self.Raiz.objects.none()), [])
        self.assertEqual(self.raiz.hijos.count(), 1)
        raices = self.Raiz.objects.de_empresa(self.empresa).prefetch_related("hijos")
        self.assertEqual(len(raices[0].hijos.all()), 1)
        with sin_filtro_empresa():
            self.assertEqual(self.Raiz.objects.count(), 2)
        self.assertEqual(self.Raiz.todos.count(), 2)
        # La validación de unicidad consulta sin filtro por empresa.
        repetida = self.Raiz(empresa=self.empresa, nombre="r")
        repetida.validate_unique()
        with self.assertRaises(Exception):
            repetida.validate_constraints()

    def test_or_con_un_queryset_sin_filtrar_lanza(self):
        propia = self.Raiz.objects.de_empresa(self.empresa)
        with self.assertRaises(ConsultaSinEmpresa):
            list(propia | self.Raiz.objects.all())
        with self.assertRaises(ConsultaSinEmpresa):
            list(self.raiz.hijos.all() | self.Hijo.objects.all())
        # Combinar dos consultas acotadas sigue siendo seguro.
        self.assertEqual(len(propia | propia), 1)

    def test_union_con_un_queryset_sin_filtrar_lanza(self):
        propia = self.Raiz.objects.de_empresa(self.empresa)
        with self.assertRaises(ConsultaSinEmpresa):
            list(propia.union(self.Raiz.objects.all()))
        self.assertEqual(len(propia.union(propia)), 1)
        self.assertEqual(len(propia | self.Raiz.objects.none()), 1)

    def test_or_con_slice_a_la_izquierda_lanza(self):
        propia = self.Raiz.objects.de_empresa(self.empresa)
        with self.assertRaises(ConsultaSinEmpresa):
            list(propia[:5] | self.Raiz.objects.all())
        with self.assertRaises(ConsultaSinEmpresa):
            list(self.Raiz.objects.all()[:5] | self.Raiz.objects.all())
        self.assertEqual(len(propia[:5] | propia), 1)

    def test_aiterator_sin_empresa_lanza(self):
        async def consumir(consulta):
            return [objeto async for objeto in consulta.aiterator()]

        with self.assertRaises(ConsultaSinEmpresa):
            async_to_sync(consumir)(self.Raiz.objects.all())

    def test_instancia_armada_a_mano_no_exime_a_su_manager_relacionado(self):
        ajena = self.Raiz(pk=self.raiz_pk)
        with self.assertRaises(ConsultaSinEmpresa):
            list(ajena.hijos.all())
        with self.assertRaises(ConsultaSinEmpresa):
            list(self.Hijo.objects.db_manager(hints={"instance": ajena}).all())

    def test_xor_orden_inverso_cadenas_y_slice_lanzan(self):
        propia = self.Raiz.objects.de_empresa(self.empresa)
        todas = self.Raiz.objects.all()
        peligrosas = {
            "xor": lambda: propia ^ todas,
            "xor inverso": lambda: todas ^ propia,
            "or inverso": lambda: todas | propia,
            "cadena or": lambda: propia | propia | todas,
            "cadena or con la sin filtrar al medio": lambda: propia | todas | propia,
            "union inversa": lambda: todas.union(propia),
            "intersection": lambda: todas.intersection(propia),
            "difference": lambda: todas.difference(propia),
            "slice a la izquierda": lambda: todas[:5] | propia,
            "slice a la izquierda con xor": lambda: todas[:5] ^ propia,
            "slice de la propia con la sin filtrar": lambda: propia[:5] | todas,
        }
        for nombre, armar in peligrosas.items():
            with self.subTest(nombre), self.assertRaises(ConsultaSinEmpresa):
                list(armar())

    def test_combinaciones_seguras_no_traen_datos_de_otra_empresa(self):
        propia = self.Raiz.objects.de_empresa(self.empresa)
        nombres = lambda consulta: [r.nombre for r in consulta]  # noqa: E731
        seguras = {
            "or": propia | propia,
            "cadena or": propia | propia | propia,
            "xor con vacía": propia ^ self.Raiz.objects.none(),
            "or con vacía a la izquierda": self.Raiz.objects.none() | propia,
            "slice a la izquierda": propia[:5] | propia,
            "union": propia.union(propia),
            "intersection": propia.intersection(propia),
        }
        for nombre, consulta in seguras.items():
            with self.subTest(nombre):
                self.assertEqual(nombres(consulta), ["r"])
        self.assertEqual(nombres(propia.difference(propia)), [])
        # Sin la guardia, la sin filtrar sí trae la de la otra empresa.
        self.assertEqual(self.Raiz.todos.count(), 2)

    def test_el_re_envoltorio_conserva_los_objetos_relacionados_conocidos(self):
        raiz = self.Raiz.objects.de_empresa(self.empresa).get()
        hijos = raiz.hijos.all()
        combinada = hijos[:5] | hijos
        with self.assertNumQueries(1):
            lista = list(combinada)
            self.assertEqual(lista[0].raiz.pk, raiz.pk)

    def test_vacia_con_otra_sin_filtrar_se_respeta_la_parte_devuelta(self):
        # La identidad se comprueba antes del re-envoltorio: la parte de `todos`
        # vuelve tal cual (como dicts, aquí) y no pasa por la guardia.
        resultado = self.Raiz.objects.none() | self.Raiz.todos.values("nombre")
        self.assertCountEqual([f["nombre"] for f in resultado], ["r", "ajena"])

    def test_el_manager_por_defecto_es_objects(self):
        self.assertEqual(self.Raiz._default_manager.name, "objects")
