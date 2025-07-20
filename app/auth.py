import os
import base64
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, Cookie, status
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Usuario
from cryptography.fernet import Fernet
import secrets

load_dotenv()

"""
Configuración y variables de seguridad

- SECRET_KEY: Clave secreta utilizada para firmar los tokens JWT.
- ALGORITHM: Algoritmo criptográfico usado para firmar y verificar JWT (por defecto HS256).
- ACCESS_TOKEN_EXPIRE_MINUTES: Tiempo de expiración en minutos para los tokens de acceso.

"""

# Variables de seguridad leídas desde .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

"""
Funciones para generar y verificar tokens JWT
Configuración de cookies para seguridad en el cliente:
- COOKIE_SECURE: Indica si la cookie solo se envía por HTTPS.
- COOKIE_HTTPONLY: Impide acceso a la cookie desde JavaScript para evitar ataques XSS.
- COOKIE_SAMESITE: Controla el envío de cookies en solicitudes cross-site para mitigar CSRF.
"""
# Configuración segura de cookies
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_HTTPONLY = os.getenv("COOKIE_HTTPONLY", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

"""
Clave y objetos para cifrado y autenticación:
- ENCRYPTION_KEY: Clave para cifrar y descifrar tokens JWT almacenados en cookies.
- cipher_suite: Objeto Fernet que realiza operaciones de cifrado simétrico con ENCRYPTION_KEY.
- oauth2_scheme: Esquema OAuth2 para obtener tokens mediante flujo "password".
- pwd_context: Contexto de PassLib para hashing y verificación segura de contraseñas usando bcrypt.
"""

# Inicializar cipher con la clave
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY no está configurada en las variables de entorno")

# Ahora podemos usar la clave con seguridad
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def verificar_password(hash_sha256: str, hash_guardado_bcrypt: str):
    """
    Verifica que una contraseña en hash SHA256 coincida con un hash almacenado bcrypt.

    Parámetros:
    - hash_sha256 (str): Contraseña hasheada con SHA256 (entrada).
    - hash_guardado_bcrypt (str): Hash bcrypt almacenado.
    
    Operación:
        Usa passlib con bcrypt para verificar la contraseña de forma segura.

    Retorna:
    - bool: True si coinciden, False en caso contrario.
    """
    return pwd_context.verify(hash_sha256, hash_guardado_bcrypt)

def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None):
    """Crear JWT normal (sin cifrar) - para uso interno
    Objetivo:
        Generar un token JWT firmado para autenticación de usuarios.Esta función asegura
        la autenticidad del usuario permitiendo su acceso a rutas protegidas.

    Parámetros:
        data (dict): Información del usuario que se desea codificar en el token.
        expires_delta (timedelta, opcional): Duración personalizada de validez del token. 
                                             Si no se especifica, se usa el tiempo definido en ACCESS_TOKEN_EXPIRE_MINUTES.

    Operación:
        - Clona el diccionario de datos.
        - Calcula la fecha de expiración del token.
        - Agrega la expiración al payload.
        - Genera el JWT usando la clave secreta y el algoritmo definido.
        - Devuelve el token como cadena codificada.
        
    Retorna:
         - str: Token JWT firmado y codificado.
    """
        
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def cifrar_token(token: str) -> str:
    """
    Cifrar JWT para almacenamiento en cookie.
    Objetivo:
        Cifrar un token JWT para protegerlo antes de almacenarlo o enviarlo en una cookie.

    Parámetros:
        token (str): Token JWT en texto plano que se desea cifrar.

    Operación:
        - Convierte el token a bytes.
        - Lo cifra usando la clave Fernet configurada.
        - Devuelve el token cifrado como cadena.
    
    Retorna:
        str: Token cifrado listo para almacenamiento o envío.
    """
    
    try:
        # Convertir token a bytes y cifrar
        token_bytes = token.encode('utf-8')
        encrypted_token = cipher_suite.encrypt(token_bytes)
        # Convertir a string para cookie
        return base64.urlsafe_b64encode(encrypted_token).decode('utf-8')
    except Exception as e:
        print(f"Error cifrando token: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

def descifrar_token(encrypted_token: str) -> str:
    """Descifrar JWT desde cookie
    Objetivo:
        Descifrar un token previamente cifrado para obtener el JWT original.
    Parámetros:
        token_cifrado (str): Cadena cifrada que contiene el token JWT.
    Operación:
        - Convierte la cadena a bytes.
        - Usa Fernet para descifrarla.
        - Devuelve el token JWT original en texto plano.
    Retorna:
        str o None: Token JWT original si la operación fue exitosa; None si falló.
    """
    try:
        # Decodificar desde base64
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
        # Descifrar
        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
        # Convertir de vuelta a string
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error descifrando token: {e}")
        return None

def crear_token_cifrado(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT firmado y lo cifra para almacenamiento seguro en cookies.

    Parámetros:
    - data (dict): Información a incluir en el token.
    - expires_delta (timedelta, opcional): Tiempo de expiración.
    
    Operación:
        - Genera un token JWT usando crear_token_acceso.
        - Cifra el token resultante usando cifrar_token.

    Retorna:
    - str: Token cifrado listo para enviar o almacenar.
    """
    # Crear JWT normal
    jwt_token = crear_token_acceso(data, expires_delta)
    # Cifrar JWT
    encrypted_token = cifrar_token(jwt_token)
    return encrypted_token

def validar_token_cifrado(encrypted_token: str) -> dict:
    """Descifrar y validar JWT desde cookie
    Descifra un token cifrado, valida su firma y extrae el payload.

    Parámetros:
    - encrypted_token (str): Token JWT cifrado.

    Operación:
        - Descifra el token con descifrar_token.
        - Decodifica y valida el JWT con la clave secreta y algoritmo.
        - Maneja errores de validación.
        
    Retorna:
    - dict: Payload del token si es válido, None si no.
    """
    if not encrypted_token:
        return None
    
    # Descifrar token
    jwt_token = descifrar_token(encrypted_token)
    if not jwt_token:
        return None
    
    try:
        # Validar JWT descifrado
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        print(f"Error validando JWT: {e}")
        return None

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_token: Optional[str] = Cookie(None)
):
    """Obtiene el usuario actual del token JWT almacenado en la cookie.
    Objetivo:
        Obtener y validar el usuario actual autenticado a partir de un token JWT,
        que puede provenir de una cookie cifrada o del encabezado Authorization.

    Parámetros:
        request (Request): Objeto de la solicitud HTTP.
        db (AsyncSession): Sesión asíncrona de la base de datos.
        auth_token (str, opcional): Token cifrado recibido en cookie.

    Operación:
        - Intenta validar token desde cookie descifrándolo y decodificándolo.
        - Si no está disponible o inválido, intenta validar token sin cifrar del header Authorization.
        - Extrae el ID de usuario del payload.
        - Consulta en base de datos el usuario correspondiente.
        - Verifica que el usuario exista y esté activo.
        - Lanza HTTPException en caso de fallo en validación.

    Retorna:
        Usuario: Instancia del usuario autenticado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
   
    # Intentar obtener token de cookie primero, luego del header Authorization
    token = auth_token
    jwt_payload = None
    
    if token:
        # Intentar descifrar token de cookie
        jwt_payload = validar_token_cifrado(token)
    
    if not jwt_payload:
        # Fallback: Intentar obtener JWT sin cifrar del header Authorization
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            plain_jwt = authorization.split(" ")[1]
            try:
                jwt_payload = jwt.decode(plain_jwt, SECRET_KEY, algorithms=[ALGORITHM])
            except JWTError:
                pass
    
    if not jwt_payload:
        raise credentials_exception
    
    # Extraer user_id del payload
    user_id = jwt_payload.get("sub")
    if user_id is None:
        raise credentials_exception
   
    # Buscar el usuario por ID y verificar que existe
    result = await db.execute(select(Usuario).filter(Usuario.id_usuario == user_id))
    user = result.scalars().first()
   
    # Validar que el usuario existe y está activo
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )
   
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
   
    return user