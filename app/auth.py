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


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# 🔧 AGREGAR ESTAS LÍNEAS:
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_HTTPONLY = os.getenv("COOKIE_HTTPONLY", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

#🔧 NUEVO: Clave de cifrado para tokens


# Inicializar cipher con la clave
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY no está configurada en las variables de entorno")

# Ahora podemos usar la clave con seguridad
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bcrypt__rounds=12

def verificar_password(hash_sha256: str, hash_guardado_bcrypt: str):
    return pwd_context.verify(hash_sha256, hash_guardado_bcrypt)

def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None):
    """Crear JWT normal (sin cifrar) - para uso interno"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def cifrar_token(token: str) -> str:
    """Cifrar JWT para almacenamiento en cookie"""
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
    """Descifrar JWT desde cookie"""
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
    """Crear JWT y cifrarlo para cookie"""
    # Crear JWT normal
    jwt_token = crear_token_acceso(data, expires_delta)
    # Cifrar JWT
    encrypted_token = cifrar_token(jwt_token)
    return encrypted_token

def validar_token_cifrado(encrypted_token: str) -> dict:
    """Descifrar y validar JWT desde cookie"""
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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
   
    # Intentar obtener token de cookie primero, luego del header Authorization
    token = auth_token
    jwt_payload = None
    
    if token:
        # 🔧 NUEVO: Intentar descifrar token de cookie
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