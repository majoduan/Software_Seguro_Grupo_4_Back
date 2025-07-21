from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

def add_middlewares(app: FastAPI) -> None:
     # Middleware de hosts confiables
    """
    Middleware: TrustedHostMiddleware

    Objetivo:
        Restringir el acceso a la aplicación únicamente a dominios específicos, 
        mitigando ataques.

    Parámetros:
        - allowed_hosts: Lista de nombres de host autorizados. 

    Operación:
        - Inspecciona el encabezado 'Host' de cada solicitud HTTP.
        - Rechaza solicitudes cuyo dominio no esté en la lista permitida.

    Retorna:
        No retorna directamente. Aplica restricciones al tráfico HTTP entrante.
    """
    # Solo HTTPS en producción
    origins = ["https://software-seguro-grupo-4-front.vercel.app"]

    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["software-seguro-grupo-4-back.onrender.com", "*.onrender.com"]
    )

# Middleware CORS
    """
    Middleware: CORSMiddleware

    Objetivo:
        Controlar el intercambio de recursos entre diferentes orígenes 
        (Cross-Origin Resource Sharing), permitiendo únicamente 
        solicitudes desde fuentes de confianza.

    Parámetros:
        - allow_origins: Orígenes permitidos para consumir la API.
        - allow_credentials: Permite uso de cookies y encabezados de autorización.
        - allow_methods: Métodos HTTP autorizados.
        - allow_headers: Lista explícita de encabezados que se pueden enviar.
        - expose_headers: Cabeceras visibles para el cliente.

    Operación:
        - Evalúa cada solicitud según políticas CORS configuradas.
        - Permite o rechaza el acceso según origen, método y encabezados.

    Retorna:
        No retorna directamente. Actúa como middleware en las solicitudes HTTP.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # OPTIONS necesario
        allow_headers=[                    # Solo headers esenciales
            "Accept",
            "Content-Type", 
            "Authorization",
            "Cookie",
            "X-Requested-With"
        ],
        expose_headers=["Set-Cookie"]
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        
        """
        Middleware: add_security_headers

        Objetivo:
            Incluir cabeceras HTTP de seguridad en todas las respuestas, fortaleciendo la
            protección contra ataques comunes como XSS, clickjacking y fuga de información 
            referencial.

        Parámetros:
            - request: Objeto de solicitud HTTP entrante.
            - call_next: Función que pasa el control al siguiente componente del pipeline.

        Operación:
            - Procesa la solicitud HTTP y obtiene la respuesta.
            - Añade múltiples cabeceras de seguridad, entre ellas:
                - X-Frame-Options: Impide uso en iframes (clickjacking).
                - X-Content-Type-Options: Bloquea detección MIME automática.
                - X-XSS-Protection: Activa protección contra XSS en navegadores antiguos.
                - Referrer-Policy: Limita información de referencia enviada.
                - Strict-Transport-Security: Exige uso de HTTPS durante un año.
                - Content-Security-Policy: Define políticas estrictas para recursos permitidos.
                - Permissions-Policy: Desactiva funciones sensibles del navegador.

        Retorna:
            - response: Respuesta HTTP original con cabeceras de seguridad añadidas.
        """
        response = await call_next(request)
        
        # Headers de seguridad HTTPS
        response.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block", 
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' data: https://cdn.jsdelivr.net; connect-src 'self' https://software-seguro-grupo-4-front.vercel.app; frame-ancestors 'none';",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        })
        
        return response