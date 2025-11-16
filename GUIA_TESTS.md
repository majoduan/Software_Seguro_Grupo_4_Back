# Guía de Testing - Backend

Esta guía te explica paso a paso cómo ejecutar los tests unitarios del backend.

## 📋 Índice

1. [Instalación de Dependencias](#1-instalación-de-dependencias)
2. [Ejecutar Tests](#2-ejecutar-tests)
3. [Ver Cobertura](#3-ver-cobertura)
4. [Estructura de Tests](#4-estructura-de-tests)
5. [Ejemplos de Salida](#5-ejemplos-de-salida)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Instalación de Dependencias

### Paso 1.1: Instalar pytest y dependencias de testing

```bash
# Desde la carpeta raíz del backend
cd Software_Seguro_Grupo_4_Back

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

**O instalar solo pytest manualmente:**

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Paso 1.2: Verificar instalación

```bash
pytest --version
```

**Salida esperada:**
```
pytest 8.0.0
```

---

## 2. Ejecutar Tests

### 2.1 Ejecutar TODOS los tests

```bash
pytest
```

### 2.2 Ejecutar solo tests de validadores

```bash
pytest app/tests/test_validators.py
```

### 2.3 Ejecutar un test específico

```bash
# Ejecutar una clase de tests
pytest app/tests/test_validators.py::TestValidateDirectorName

# Ejecutar un test individual
pytest app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_dos_palabras
```

### 2.4 Ejecutar con modo verbose (más detalles)

```bash
pytest -v
```

### 2.5 Ejecutar con output detallado

```bash
pytest -vv
```

### 2.6 Mostrar print() durante tests

```bash
pytest -s
```

### 2.7 Detener en el primer fallo

```bash
pytest -x
```

---

## 3. Ver Cobertura

### 3.1 Ejecutar tests con reporte de cobertura

```bash
pytest --cov=app --cov-report=term-missing
```

**Salida esperada:**
```
---------- coverage: platform win32, python 3.11.0 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
app/__init__.py                       0      0   100%
app/validators.py                   102      0   100%
app/business_validators.py          145     15    90%   45-50, 78-82
app/schemas.py                       85      5    94%   112, 156
---------------------------------------------------------------
TOTAL                               332     20    94%
```

### 3.2 Generar reporte HTML de cobertura

```bash
pytest --cov=app --cov-report=html
```

Esto genera una carpeta `htmlcov/`. Abre `htmlcov/index.html` en tu navegador para ver el reporte interactivo.

### 3.3 Ver solo cobertura de validadores

```bash
pytest app/tests/test_validators.py --cov=app.validators --cov-report=term-missing
```

---

## 4. Estructura de Tests

### 4.1 Archivos actuales

```
app/tests/
├── __init__.py                    # Inicialización del paquete
└── test_validators.py             # Tests de validadores (✅ creado)
```

### 4.2 Tests implementados en test_validators.py

| Clase de Test | Función Validada | # Tests |
|---------------|------------------|---------|
| `TestValidateDirectorName` | `validate_director_name()` | 10 tests |
| `TestValidatePasswordStrength` | `validate_password_strength()` | 6 tests |
| `TestValidateUsername` | `validate_username()` | 9 tests |
| `TestValidateEmailFormat` | `validate_email_format()` | 7 tests |
| `TestValidateAnioFormat` | `validate_anio_format()` | 8 tests |
| `TestValidateDateRange` | `validate_date_range()` | 7 tests |
| `TestValidateProjectDuration` | `validate_project_duration()` | 6 tests |
| `TestValidatePeriodoDates` | `validate_periodo_dates()` | 3 tests |
| `TestValidateCodigoUniqueFormat` | `validate_codigo_unique_format()` | 6 tests |
| `TestValidatePresupuestoRange` | `validate_presupuesto_range()` | 7 tests |
| **TOTAL** | **10 validadores** | **69 tests** |

### 4.3 Categorías de tests

Cada validador tiene tests para:

✅ **Casos válidos:** Datos que deben ser aceptados
- Valores mínimos/máximos permitidos
- Formatos correctos
- Casos límite válidos

❌ **Casos inválidos:** Datos que deben ser rechazados
- Valores fuera de rango
- Formatos incorrectos
- Caracteres no permitidos

🔄 **Casos edge:** Situaciones especiales
- Valores None
- Strings vacíos
- Espacios extras (trim)

---

## 5. Ejemplos de Salida

### 5.1 Todos los tests pasan ✅

```bash
$ pytest app/tests/test_validators.py -v

======================== test session starts =========================
platform win32 -- Python 3.11.0, pytest-8.0.0
collected 69 items

app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_dos_palabras PASSED     [  1%]
app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_ocho_palabras PASSED    [  2%]
app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_con_acentos PASSED      [  4%]
...
app/tests/test_validators.py::TestValidatePresupuestoRange::test_presupuesto_sin_maximo PASSED     [100%]

======================== 69 passed in 0.35s ==========================
```

### 5.2 Un test falla ❌

```bash
$ pytest app/tests/test_validators.py::TestValidateDirectorName::test_nombre_invalido_con_numeros -v

======================== test session starts =========================
platform win32 -- Python 3.11.0, pytest-8.0.0
collected 1 item

app/tests/test_validators.py::TestValidateDirectorName::test_nombre_invalido_con_numeros FAILED [100%]

============================== FAILURES ==============================
_________ TestValidateDirectorName.test_nombre_invalido_con_numeros __________

    def test_nombre_invalido_con_numeros(self):
        """Debe rechazar nombre con números"""
        with pytest.raises(ValueError) as exc_info:
>           validate_director_name("Juan 123 Pérez")
E           Failed: DID NOT RAISE <class 'ValueError'>

app/tests/test_validators.py:66: Failed
====================== 1 failed in 0.12s =========================
```

### 5.3 Reporte de cobertura

```bash
$ pytest --cov=app.validators --cov-report=term-missing

---------- coverage: platform win32, python 3.11.0 -----------
Name                 Stmts   Miss  Cover   Missing
--------------------------------------------------
app/validators.py      102      0   100%
--------------------------------------------------
TOTAL                  102      0   100%
```

**100% de cobertura** significa que cada línea de código en `validators.py` fue ejecutada al menos una vez durante los tests.

---

## 6. Troubleshooting

### Problema 1: "pytest: command not found"

**Causa:** pytest no está instalado

**Solución:**
```bash
pip install pytest
```

### Problema 2: "ModuleNotFoundError: No module named 'app'"

**Causa:** Ejecutando desde directorio incorrecto

**Solución:**
```bash
# Asegúrate de estar en la raíz del backend
cd Software_Seguro_Grupo_4_Back

# O configura PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%CD%          # Windows CMD
$env:PYTHONPATH += ";$PWD"                # Windows PowerShell
```

### Problema 3: Tests fallan por imports

**Causa:** Dependencias no instaladas

**Solución:**
```bash
pip install -r requirements.txt
pip install python-dateutil
```

### Problema 4: "ImportError: cannot import name 'validate_director_name'"

**Causa:** El módulo validators.py tiene errores de sintaxis

**Solución:**
1. Verificar que `app/validators.py` existe
2. Revisar que todas las funciones estén correctamente definidas
3. Corregir errores de sintaxis si los hay

### Problema 5: Warnings sobre "PytestUnraisableExceptionWarning"

**Causa:** Normal en tests con async (no afecta resultados)

**Solución (opcional):**
```bash
pytest -W ignore::pytest.PytestUnraisableExceptionWarning
```

---

## 7. Comandos Útiles Resumidos

```bash
# Instalar dependencias
pip install -r requirements-dev.txt

# Ejecutar todos los tests
pytest

# Ejecutar solo validadores
pytest app/tests/test_validators.py

# Ejecutar con cobertura
pytest --cov=app --cov-report=term-missing

# Ejecutar con HTML de cobertura
pytest --cov=app --cov-report=html

# Ejecutar en modo verbose
pytest -v

# Detener en primer fallo
pytest -x

# Mostrar prints
pytest -s

# Ejecutar test específico
pytest app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_dos_palabras
```

---

## 8. Próximos Pasos

Una vez que domines los tests unitarios, puedes:

1. **Crear tests de integración** para endpoints en `test_endpoints.py`
2. **Agregar tests para schemas** en `test_schemas.py`
3. **Crear tests para business validators** en `test_business_validators.py`

---

## 9. Estructura de un Test Unitario

```python
def test_nombre_descriptivo(self):
    """Descripción clara de qué se está probando"""

    # 1. ARRANGE (Preparar)
    # Definir los datos de entrada
    nombre = "Juan Pérez"

    # 2. ACT (Actuar)
    # Ejecutar la función a probar
    resultado = validate_director_name(nombre)

    # 3. ASSERT (Afirmar)
    # Verificar el resultado esperado
    assert resultado == "Juan Pérez"
```

### Ejemplo de test que espera excepción:

```python
def test_nombre_invalido_con_numeros(self):
    """Debe rechazar nombre con números"""

    # Esperamos que lance ValueError
    with pytest.raises(ValueError) as exc_info:
        validate_director_name("Juan 123 Pérez")

    # Verificar el mensaje de error
    assert "solo puede contener letras" in str(exc_info.value)
```

---

## 10. Buenas Prácticas

✅ **DO (Hacer):**
- Escribir tests antes de hacer cambios (TDD)
- Nombrar tests de forma descriptiva
- Probar casos válidos e inválidos
- Mantener tests simples y enfocados
- Ejecutar tests antes de hacer commit

❌ **DON'T (No hacer):**
- Tests que dependen del orden de ejecución
- Tests que modifican estado global
- Tests muy largos o complejos
- Ignorar tests que fallan

---

## 📊 Estado Actual

- ✅ **69 tests unitarios** implementados para validadores
- ✅ **100% cobertura** esperada en `validators.py`
- ⏳ Tests de integración (pendiente)
- ⏳ Tests de schemas (pendiente)
- ⏳ Tests de business validators (pendiente)

---

**¡Listo para ejecutar!** 🚀

Ejecuta `pytest app/tests/test_validators.py -v` para ver todos los tests en acción.
