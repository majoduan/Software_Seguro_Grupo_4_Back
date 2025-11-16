"""
Validadores personalizados para el backend

Este módulo contiene validadores que replican las validaciones del frontend
para garantizar la integridad y seguridad de los datos en el backend.
"""

import re
from typing import Optional
from datetime import date
from dateutil.relativedelta import relativedelta


def validate_director_name(name: Optional[str]) -> Optional[str]:
    """
    Valida el formato del nombre del director de proyecto.

    Reglas (replicadas del frontend):
    - Entre 2 y 8 palabras
    - Solo caracteres alfabéticos (incluye acentos y ñ)

    Args:
        name: Nombre del director a validar

    Returns:
        El nombre si es válido

    Raises:
        ValueError: Si el nombre no cumple las reglas
    """
    if name is None or name.strip() == "":
        return None

    name = name.strip()
    words = name.split()

    if len(words) < 2 or len(words) > 8:
        raise ValueError(
            "El nombre del director debe contener entre 2 y 8 palabras "
            "(Nombre(s) Apellido(s))"
        )

    # Patrón que permite letras con acentos, ñ, etc.
    pattern = re.compile(r'^[A-Za-zÀ-ÖØ-öø-ÿ]+$')

    for word in words:
        if not pattern.match(word):
            raise ValueError(
                "El nombre del director solo puede contener letras "
                "(se permiten acentos y ñ)"
            )

    return name


def validate_password_strength(password: str) -> str:
    """
    Valida la complejidad de la contraseña.

    Reglas:
    - Mínimo 8 caracteres
    - Al menos una letra mayúscula
    - Al menos un número

    Args:
        password: Contraseña a validar

    Returns:
        La contraseña si es válida

    Raises:
        ValueError: Si la contraseña no cumple las reglas
    """
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")

    if not re.search(r'[A-Z]', password):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")

    if not re.search(r'\d', password):
        raise ValueError("La contraseña debe contener al menos un número")

    return password


def validate_username(username: str) -> str:
    """
    Valida el formato del nombre de usuario.

    Reglas:
    - Solo alfanuméricos y espacios
    - Longitud mínima 3, máxima 100

    Args:
        username: Nombre de usuario a validar

    Returns:
        El nombre de usuario si es válido

    Raises:
        ValueError: Si el nombre de usuario no cumple las reglas
    """
    username = username.strip()

    if len(username) < 3:
        raise ValueError("El nombre de usuario debe tener al menos 3 caracteres")

    if len(username) > 100:
        raise ValueError("El nombre de usuario no puede exceder 100 caracteres")

    if not re.match(r'^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚüÜ]+$', username):
        raise ValueError(
            "El nombre de usuario solo puede contener letras, números y espacios"
        )

    return username


def validate_email_format(email: str) -> str:
    """
    Valida el formato del correo electrónico.

    Reglas (replicadas del frontend):
    - Patrón: /^[^\s@]+@[^\s@]+\.[^\s@]+$/

    Args:
        email: Correo electrónico a validar

    Returns:
        El email si es válido

    Raises:
        ValueError: Si el email no cumple el formato
    """
    email = email.strip().lower()

    pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

    if not pattern.match(email):
        raise ValueError("Por favor ingresa un correo electrónico válido")

    return email


def validate_anio_format(anio: str) -> str:
    """
    Valida el formato del año (4 dígitos).

    Args:
        anio: Año a validar

    Returns:
        El año si es válido

    Raises:
        ValueError: Si el año no tiene 4 dígitos
    """
    if not re.match(r'^\d{4}$', anio):
        raise ValueError("El año debe tener exactamente 4 dígitos")

    year_int = int(anio)
    if year_int < 1900 or year_int > 2100:
        raise ValueError("El año debe estar entre 1900 y 2100")

    return anio


def validate_date_range(
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
    fecha_prorroga_inicio: Optional[date] = None,
    fecha_prorroga_fin: Optional[date] = None
) -> None:
    """
    Valida la coherencia de las fechas de un proyecto.

    Reglas (replicadas del frontend):
    - fecha_fin >= fecha_inicio
    - fecha_prorroga >= fecha_fin (si existe)
    - fecha_prorroga_inicio >= fecha_fin (si existe)
    - fecha_prorroga_fin >= fecha_prorroga_inicio (si existe)

    Args:
        fecha_inicio: Fecha de inicio del proyecto
        fecha_fin: Fecha de fin del proyecto
        fecha_prorroga_inicio: Fecha de inicio de prórroga (opcional)
        fecha_prorroga_fin: Fecha de fin de prórroga (opcional)

    Raises:
        ValueError: Si las fechas no son coherentes
    """
    if fecha_inicio and fecha_fin:
        if fecha_fin < fecha_inicio:
            raise ValueError(
                "La fecha de fin no puede ser anterior a la fecha de inicio"
            )

    if fecha_prorroga_inicio and fecha_fin:
        if fecha_prorroga_inicio < fecha_fin:
            raise ValueError(
                "La fecha de inicio de prórroga debe ser mayor o igual "
                "a la fecha de fin del proyecto"
            )

    if fecha_prorroga_fin and fecha_prorroga_inicio:
        if fecha_prorroga_fin <= fecha_prorroga_inicio:
            raise ValueError(
                "La fecha de fin de prórroga debe ser posterior a "
                "la fecha de inicio de prórroga"
            )


def validate_project_duration(
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
    duracion_maxima_meses: int
) -> None:
    """
    Valida que la duración del proyecto no exceda la máxima permitida.

    Reglas (replicadas del frontend):
    - La diferencia entre fecha_fin y fecha_inicio no debe exceder
      la duración máxima en meses del tipo de proyecto

    Args:
        fecha_inicio: Fecha de inicio del proyecto
        fecha_fin: Fecha de fin del proyecto
        duracion_maxima_meses: Duración máxima en meses permitida

    Raises:
        ValueError: Si la duración excede el máximo
    """
    if not fecha_inicio or not fecha_fin:
        return

    # Calcular la fecha fin máxima permitida
    fecha_fin_maxima = fecha_inicio + relativedelta(months=duracion_maxima_meses)

    # Ajustar por días (si pasa de 15 días, cuenta como mes adicional)
    if fecha_fin > fecha_fin_maxima:
        # Calcular duración real en meses
        delta = relativedelta(fecha_fin, fecha_inicio)
        duracion_real = delta.years * 12 + delta.months

        # Si tiene más de 15 días, cuenta como mes adicional
        if delta.days > 15:
            duracion_real += 1

        if duracion_real > duracion_maxima_meses:
            raise ValueError(
                f"La duración del proyecto ({duracion_real} meses) excede "
                f"la duración máxima permitida ({duracion_maxima_meses} meses) "
                f"para este tipo de proyecto"
            )


def validate_periodo_dates(fecha_inicio: date, fecha_fin: date) -> None:
    """
    Valida que la fecha de fin del periodo sea posterior a la de inicio.

    Args:
        fecha_inicio: Fecha de inicio del periodo
        fecha_fin: Fecha de fin del periodo

    Raises:
        ValueError: Si la fecha de fin es anterior o igual a la de inicio
    """
    if fecha_fin <= fecha_inicio:
        raise ValueError(
            "La fecha de fin del periodo debe ser posterior a la fecha de inicio"
        )


def validate_codigo_unique_format(codigo: str, min_length: int = 3, max_length: int = 50) -> str:
    """
    Valida el formato de un código (proyecto, POA, periodo, etc.).

    Args:
        codigo: Código a validar
        min_length: Longitud mínima
        max_length: Longitud máxima

    Returns:
        El código validado

    Raises:
        ValueError: Si el código no cumple el formato
    """
    codigo = codigo.strip()

    if len(codigo) < min_length:
        raise ValueError(f"El código debe tener al menos {min_length} caracteres")

    if len(codigo) > max_length:
        raise ValueError(f"El código no puede exceder {max_length} caracteres")

    return codigo


def validate_presupuesto_range(
    presupuesto: Optional[float],
    presupuesto_maximo: Optional[float]
) -> None:
    """
    Valida que el presupuesto esté dentro del rango permitido.

    Reglas (replicadas del frontend):
    - Presupuesto > 0
    - Presupuesto <= presupuesto_maximo (si está definido)

    Args:
        presupuesto: Presupuesto a validar
        presupuesto_maximo: Presupuesto máximo permitido

    Raises:
        ValueError: Si el presupuesto está fuera de rango
    """
    if presupuesto is not None:
        if presupuesto <= 0:
            raise ValueError("El presupuesto debe ser mayor a 0")

        if presupuesto_maximo is not None and presupuesto > presupuesto_maximo:
            raise ValueError(
                f"El presupuesto ({presupuesto}) excede el presupuesto máximo "
                f"permitido ({presupuesto_maximo}) para este tipo"
            )
