from .consultas import empresa_de


class EmpresaMiddleware:
    """Fija `request.empresa`: la del usuario autenticado, o `None`.

    Va después de `AuthenticationMiddleware`. La API fija el valor en
    `JWTAutenticacionEmpresa`, porque el JWT se resuelve dentro de la vista.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = empresa_de(request)
        return self.get_response(request)
