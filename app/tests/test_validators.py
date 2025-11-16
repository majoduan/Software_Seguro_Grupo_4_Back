"""
Tests unitarios para los validadores custom

Este archivo contiene tests para todas las funciones de validación
del módulo app/validators.py
"""

import pytest
from datetime import date
from decimal import Decimal

from app.validators import (
    validate_director_name,
    validate_password_strength,
    validate_username,
    validate_email_format,
    validate_anio_format,
    validate_date_range,
    validate_project_duration,
    validate_periodo_dates,
    validate_codigo_unique_format,
    validate_presupuesto_range
)


# ==========================================
# Tests para validate_director_name()
# ==========================================

class TestValidateDirectorName:
    """Tests para validación de nombre de director"""

    def test_nombre_valido_dos_palabras(self):
        """Debe aceptar nombre con 2 palabras"""
        result = validate_director_name("Juan Pérez")
        assert result == "Juan Pérez"

    def test_nombre_valido_ocho_palabras(self):
        """Debe aceptar nombre con 8 palabras (máximo)"""
        result = validate_director_name("Juan Carlos Alberto José María del Carmen López")
        assert result == "Juan Carlos Alberto José María del Carmen López"

    def test_nombre_valido_con_acentos(self):
        """Debe aceptar nombres con acentos y ñ"""
        result = validate_director_name("José María Muñoz Álvarez")
        assert result == "José María Muñoz Álvarez"

    def test_nombre_valido_con_espacios_extra(self):
        """Debe hacer trim de espacios extras"""
        result = validate_director_name("  Juan Pérez  ")
        assert result == "Juan Pérez"

    def test_nombre_invalido_una_palabra(self):
        """Debe rechazar nombre con solo 1 palabra"""
        with pytest.raises(ValueError) as exc_info:
            validate_director_name("Juan")
        assert "entre 2 y 8 palabras" in str(exc_info.value)

    def test_nombre_invalido_nueve_palabras(self):
        """Debe rechazar nombre con más de 8 palabras"""
        with pytest.raises(ValueError) as exc_info:
            validate_director_name("A B C D E F G H I")
        assert "entre 2 y 8 palabras" in str(exc_info.value)

    def test_nombre_invalido_con_numeros(self):
        """Debe rechazar nombre con números"""
        with pytest.raises(ValueError) as exc_info:
            validate_director_name("Juan 123 Pérez")
        assert "solo puede contener letras" in str(exc_info.value)

    def test_nombre_invalido_con_caracteres_especiales(self):
        """Debe rechazar nombre con caracteres especiales"""
        with pytest.raises(ValueError) as exc_info:
            validate_director_name("Juan @Pérez")
        assert "solo puede contener letras" in str(exc_info.value)

    def test_nombre_none(self):
        """Debe retornar None si el nombre es None"""
        result = validate_director_name(None)
        assert result is None

    def test_nombre_vacio(self):
        """Debe retornar None si el nombre esté vacío"""
        result = validate_director_name("")
        assert result is None


# ==========================================
# Tests para validate_password_strength()
# ==========================================

class TestValidatePasswordStrength:
    """Tests para validación de complejidad de contraseña"""

    def test_password_valida(self):
        """Debe aceptar contraseña válida"""
        result = validate_password_strength("Password123")
        assert result == "Password123"

    def test_password_valida_minima(self):
        """Debe aceptar contraseña con longitud mínima (8 caracteres)"""
        result = validate_password_strength("Passw0rd")
        assert result == "Passw0rd"

    def test_password_invalida_muy_corta(self):
        """Debe rechazar contraseña con menos de 8 caracteres"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("Pass1")
        assert "al menos 8 caracteres" in str(exc_info.value)

    def test_password_invalida_sin_mayuscula(self):
        """Debe rechazar contraseña sin letra mayúscula"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("password123")
        assert "al menos una letra mayúscula" in str(exc_info.value)

    def test_password_invalida_sin_numero(self):
        """Debe rechazar contraseña sin número"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("Password")
        assert "al menos un número" in str(exc_info.value)

    def test_password_con_caracteres_especiales(self):
        """Debe aceptar contraseña con caracteres especiales"""
        result = validate_password_strength("P@ssw0rd!")
        assert result == "P@ssw0rd!"


# ==========================================
# Tests para validate_username()
# ==========================================

class TestValidateUsername:
    """Tests para validación de nombre de usuario"""

    def test_username_valido(self):
        """Debe aceptar username válido"""
        result = validate_username("JuanPerez123")
        assert result == "JuanPerez123"

    def test_username_valido_con_espacios(self):
        """Debe aceptar username con espacios"""
        result = validate_username("Juan Perez")
        assert result == "Juan Perez"

    def test_username_valido_con_enie(self):
        """Debe aceptar username con ñ"""
        result = validate_username("Juan Muñoz")
        assert result == "Juan Muñoz"

    def test_username_valido_con_acentos(self):
        """Debe aceptar username con acentos"""
        result = validate_username("José García")
        assert result == "José García"

    def test_username_valido_minimo(self):
        """Debe aceptar username con longitud mínima (3 caracteres)"""
        result = validate_username("abc")
        assert result == "abc"

    def test_username_invalido_muy_corto(self):
        """Debe rechazar username con menos de 3 caracteres"""
        with pytest.raises(ValueError) as exc_info:
            validate_username("ab")
        assert "al menos 3 caracteres" in str(exc_info.value)

    def test_username_invalido_muy_largo(self):
        """Debe rechazar username con más de 100 caracteres"""
        username_largo = "a" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_username(username_largo)
        assert "no puede exceder 100 caracteres" in str(exc_info.value)

    def test_username_invalido_con_caracteres_especiales(self):
        """Debe rechazar username con caracteres especiales"""
        with pytest.raises(ValueError) as exc_info:
            validate_username("Juan@Perez")
        assert "solo puede contener letras, números y espacios" in str(exc_info.value)

    def test_username_con_espacios_extra_hace_trim(self):
        """Debe hacer trim de espacios extras"""
        result = validate_username("  Juan Perez  ")
        assert result == "Juan Perez"


# ==========================================
# Tests para validate_email_format()
# ==========================================

class TestValidateEmailFormat:
    """Tests para validación de formato de email"""

    def test_email_valido(self):
        """Debe aceptar email válido"""
        result = validate_email_format("usuario@ejemplo.com")
        assert result == "usuario@ejemplo.com"

    def test_email_valido_con_subdominios(self):
        """Debe aceptar email con subdominios"""
        result = validate_email_format("usuario@mail.ejemplo.com")
        assert result == "usuario@mail.ejemplo.com"

    def test_email_normaliza_a_minusculas(self):
        """Debe normalizar email a minúsculas"""
        result = validate_email_format("Usuario@Ejemplo.COM")
        assert result == "usuario@ejemplo.com"

    def test_email_hace_trim(self):
        """Debe hacer trim de espacios"""
        result = validate_email_format("  usuario@ejemplo.com  ")
        assert result == "usuario@ejemplo.com"

    def test_email_invalido_sin_arroba(self):
        """Debe rechazar email sin @"""
        with pytest.raises(ValueError) as exc_info:
            validate_email_format("usuario.ejemplo.com")
        assert "correo electrónico válido" in str(exc_info.value)

    def test_email_invalido_sin_dominio(self):
        """Debe rechazar email sin dominio"""
        with pytest.raises(ValueError) as exc_info:
            validate_email_format("usuario@")
        assert "correo electrónico válido" in str(exc_info.value)

    def test_email_invalido_con_espacios(self):
        """Debe rechazar email con espacios"""
        with pytest.raises(ValueError) as exc_info:
            validate_email_format("usuario @ejemplo.com")
        assert "correo electrónico válido" in str(exc_info.value)


# ==========================================
# Tests para validate_anio_format()
# ==========================================

class TestValidateAnioFormat:
    """Tests para validación de formato de año"""

    def test_anio_valido(self):
        """Debe aceptar año válido de 4 dígitos"""
        result = validate_anio_format("2024")
        assert result == "2024"

    def test_anio_valido_limite_inferior(self):
        """Debe aceptar año 1900 (límite inferior)"""
        result = validate_anio_format("1900")
        assert result == "1900"

    def test_anio_valido_limite_superior(self):
        """Debe aceptar año 2100 (límite superior)"""
        result = validate_anio_format("2100")
        assert result == "2100"

    def test_anio_invalido_tres_digitos(self):
        """Debe rechazar año con 3 dígitos"""
        with pytest.raises(ValueError) as exc_info:
            validate_anio_format("202")
        assert "4 dígitos" in str(exc_info.value)

    def test_anio_invalido_cinco_digitos(self):
        """Debe rechazar año con 5 dígitos"""
        with pytest.raises(ValueError) as exc_info:
            validate_anio_format("20244")
        assert "4 dígitos" in str(exc_info.value)

    def test_anio_invalido_con_letras(self):
        """Debe rechazar año con letras"""
        with pytest.raises(ValueError) as exc_info:
            validate_anio_format("202A")
        assert "4 dígitos" in str(exc_info.value)

    def test_anio_invalido_menor_a_1900(self):
        """Debe rechazar año menor a 1900"""
        with pytest.raises(ValueError) as exc_info:
            validate_anio_format("1899")
        assert "entre 1900 y 2100" in str(exc_info.value)

    def test_anio_invalido_mayor_a_2100(self):
        """Debe rechazar año mayor a 2100"""
        with pytest.raises(ValueError) as exc_info:
            validate_anio_format("2101")
        assert "entre 1900 y 2100" in str(exc_info.value)


# ==========================================
# Tests para validate_date_range()
# ==========================================

class TestValidateDateRange:
    """Tests para validación de rangos de fechas"""

    def test_fechas_validas_basicas(self):
        """Debe aceptar fecha_fin >= fecha_inicio"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        # No debe lanzar excepción
        validate_date_range(fecha_inicio, fecha_fin)

    def test_fechas_validas_iguales(self):
        """Debe aceptar fecha_fin igual a fecha_inicio"""
        fecha = date(2024, 1, 1)
        validate_date_range(fecha, fecha)

    def test_fechas_invalidas_fin_antes_de_inicio(self):
        """Debe rechazar fecha_fin < fecha_inicio"""
        fecha_inicio = date(2024, 12, 31)
        fecha_fin = date(2024, 1, 1)
        with pytest.raises(ValueError) as exc_info:
            validate_date_range(fecha_inicio, fecha_fin)
        assert "no puede ser anterior" in str(exc_info.value)

    def test_prorroga_valida(self):
        """Debe aceptar fecha_prorroga_inicio >= fecha_fin"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        fecha_prorroga_inicio = date(2025, 1, 1)
        fecha_prorroga_fin = date(2025, 6, 30)
        validate_date_range(
            fecha_inicio,
            fecha_fin,
            fecha_prorroga_inicio,
            fecha_prorroga_fin
        )

    def test_prorroga_invalida_inicio_antes_de_fin(self):
        """Debe rechazar fecha_prorroga_inicio < fecha_fin"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        fecha_prorroga_inicio = date(2024, 6, 1)  # Antes de fecha_fin
        with pytest.raises(ValueError) as exc_info:
            validate_date_range(fecha_inicio, fecha_fin, fecha_prorroga_inicio)
        assert "inicio de prórroga" in str(exc_info.value)

    def test_prorroga_invalida_fin_antes_de_inicio(self):
        """Debe rechazar fecha_prorroga_fin <= fecha_prorroga_inicio"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        fecha_prorroga_inicio = date(2025, 6, 30)
        fecha_prorroga_fin = date(2025, 1, 1)  # Antes de prorroga_inicio
        with pytest.raises(ValueError) as exc_info:
            validate_date_range(
                fecha_inicio,
                fecha_fin,
                fecha_prorroga_inicio,
                fecha_prorroga_fin
            )
        assert "fin de prórroga" in str(exc_info.value)

    def test_fechas_none_no_valida(self):
        """Debe permitir fechas None sin validar"""
        validate_date_range(None, None)  # No debe lanzar excepción


# ==========================================
# Tests para validate_project_duration()
# ==========================================

class TestValidateProjectDuration:
    """Tests para validación de duración de proyecto"""

    def test_duracion_valida_dentro_del_limite(self):
        """Debe aceptar duración dentro del límite"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 6, 30)  # 6 meses
        duracion_maxima = 12
        # No debe lanzar excepción
        validate_project_duration(fecha_inicio, fecha_fin, duracion_maxima)

    def test_duracion_valida_exacta(self):
        """Debe aceptar duración exacta al límite"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)  # 12 meses
        duracion_maxima = 12
        validate_project_duration(fecha_inicio, fecha_fin, duracion_maxima)

    def test_duracion_invalida_excede_limite(self):
        """Debe rechazar duración que excede el límite"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2025, 6, 30)  # 18 meses
        duracion_maxima = 12
        with pytest.raises(ValueError) as exc_info:
            validate_project_duration(fecha_inicio, fecha_fin, duracion_maxima)
        assert "excede la duración máxima" in str(exc_info.value)

    def test_duracion_con_dias_menores_a_15(self):
        """Debe no contar como mes adicional si días <= 15"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2025, 1, 10)  # 12 meses + 10 días
        duracion_maxima = 12
        # No debe lanzar excepción (10 días no se cuentan como mes)
        validate_project_duration(fecha_inicio, fecha_fin, duracion_maxima)

    def test_duracion_con_dias_mayores_a_15(self):
        """Debe contar como mes adicional si días > 15"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2025, 1, 20)  # 12 meses + 20 días
        duracion_maxima = 12
        with pytest.raises(ValueError) as exc_info:
            validate_project_duration(fecha_inicio, fecha_fin, duracion_maxima)
        assert "13 meses" in str(exc_info.value)

    def test_duracion_fechas_none(self):
        """Debe permitir fechas None sin validar"""
        validate_project_duration(None, None, 12)  # No debe lanzar excepción


# ==========================================
# Tests para validate_periodo_dates()
# ==========================================

class TestValidatePeriodoDates:
    """Tests para validación de fechas de periodo"""

    def test_fechas_validas(self):
        """Debe aceptar fecha_fin > fecha_inicio"""
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        # No debe lanzar excepción
        validate_periodo_dates(fecha_inicio, fecha_fin)

    def test_fechas_invalidas_iguales(self):
        """Debe rechazar fecha_fin == fecha_inicio (estricto)"""
        fecha = date(2024, 1, 1)
        with pytest.raises(ValueError) as exc_info:
            validate_periodo_dates(fecha, fecha)
        assert "posterior a la fecha de inicio" in str(exc_info.value)

    def test_fechas_invalidas_fin_antes_de_inicio(self):
        """Debe rechazar fecha_fin < fecha_inicio"""
        fecha_inicio = date(2024, 12, 31)
        fecha_fin = date(2024, 1, 1)
        with pytest.raises(ValueError) as exc_info:
            validate_periodo_dates(fecha_inicio, fecha_fin)
        assert "posterior a la fecha de inicio" in str(exc_info.value)


# ==========================================
# Tests para validate_codigo_unique_format()
# ==========================================

class TestValidateCodigoUniqueFormat:
    """Tests para validación de formato de códigos"""

    def test_codigo_valido_longitud_minima(self):
        """Debe aceptar código con longitud mínima"""
        result = validate_codigo_unique_format("ABC", min_length=3, max_length=50)
        assert result == "ABC"

    def test_codigo_valido_longitud_maxima(self):
        """Debe aceptar código con longitud máxima"""
        codigo = "A" * 50
        result = validate_codigo_unique_format(codigo, min_length=3, max_length=50)
        assert result == codigo

    def test_codigo_hace_trim(self):
        """Debe hacer trim de espacios"""
        result = validate_codigo_unique_format("  ABC123  ", min_length=3, max_length=50)
        assert result == "ABC123"

    def test_codigo_invalido_muy_corto(self):
        """Debe rechazar código menor a longitud mínima"""
        with pytest.raises(ValueError) as exc_info:
            validate_codigo_unique_format("AB", min_length=3, max_length=50)
        assert "al menos 3 caracteres" in str(exc_info.value)

    def test_codigo_invalido_muy_largo(self):
        """Debe rechazar código mayor a longitud máxima"""
        codigo = "A" * 51
        with pytest.raises(ValueError) as exc_info:
            validate_codigo_unique_format(codigo, min_length=3, max_length=50)
        assert "no puede exceder 50 caracteres" in str(exc_info.value)

    def test_codigo_con_parametros_default(self):
        """Debe usar valores por defecto (3-50)"""
        result = validate_codigo_unique_format("ABC")
        assert result == "ABC"


# ==========================================
# Tests para validate_presupuesto_range()
# ==========================================

class TestValidatePresupuestoRange:
    """Tests para validación de rango de presupuesto"""

    def test_presupuesto_valido(self):
        """Debe aceptar presupuesto > 0 y dentro del máximo"""
        # No debe lanzar excepción
        validate_presupuesto_range(50000.00, 100000.00)

    def test_presupuesto_valido_igual_al_maximo(self):
        """Debe aceptar presupuesto igual al máximo"""
        validate_presupuesto_range(100000.00, 100000.00)

    def test_presupuesto_invalido_cero(self):
        """Debe rechazar presupuesto = 0"""
        with pytest.raises(ValueError) as exc_info:
            validate_presupuesto_range(0, 100000.00)
        assert "mayor a 0" in str(exc_info.value)

    def test_presupuesto_invalido_negativo(self):
        """Debe rechazar presupuesto negativo"""
        with pytest.raises(ValueError) as exc_info:
            validate_presupuesto_range(-1000.00, 100000.00)
        assert "mayor a 0" in str(exc_info.value)

    def test_presupuesto_invalido_excede_maximo(self):
        """Debe rechazar presupuesto que excede el máximo"""
        with pytest.raises(ValueError) as exc_info:
            validate_presupuesto_range(150000.00, 100000.00)
        assert "excede el presupuesto máximo" in str(exc_info.value)

    def test_presupuesto_none_no_valida(self):
        """Debe permitir presupuesto None sin validar"""
        validate_presupuesto_range(None, 100000.00)  # No debe lanzar excepción

    def test_presupuesto_sin_maximo(self):
        """Debe validar solo > 0 si no hay máximo"""
        validate_presupuesto_range(999999.00, None)  # No debe lanzar excepción


# ==========================================
# Pytest Fixtures (opcional)
# ==========================================

@pytest.fixture
def fechas_proyecto_validas():
    """Fixture con fechas válidas para proyecto"""
    return {
        'fecha_inicio': date(2024, 1, 1),
        'fecha_fin': date(2024, 12, 31),
        'fecha_prorroga_inicio': date(2025, 1, 1),
        'fecha_prorroga_fin': date(2025, 6, 30)
    }


@pytest.fixture
def datos_usuario_validos():
    """Fixture con datos válidos de usuario"""
    return {
        'nombre_usuario': 'Juan Perez',
        'email': 'juan.perez@ejemplo.com',
        'password': 'Password123'
    }
