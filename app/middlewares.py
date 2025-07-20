from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

def add_middlewares(app: FastAPI) -> None:
    # Solo HTTPS en producción
    origins = ["https://software-seguro-grupo-4-front.vercel.app"]

    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["software-seguro-grupo-4-back.onrender.com", "*.onrender.com"]
    )

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
        response = await call_next(request)
        
        # Headers de seguridad HTTPS
        response.headers.update({
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block", 
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' data: https://cdn.jsdelivr.net; connect-src 'self' https://software-seguro-grupo-4-front.vercel.app; frame-ancestors 'none';",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        })
        
        return response