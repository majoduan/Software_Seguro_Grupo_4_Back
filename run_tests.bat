@echo off
REM Script para ejecutar tests en Windows

echo ========================================
echo   Tests Unitarios - Backend
echo ========================================
echo.

REM Verificar si pytest está instalado
python -c "import pytest" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] pytest no está instalado
    echo.
    echo Instalando pytest...
    pip install pytest pytest-asyncio pytest-cov
    echo.
)

REM Menú de opciones
echo Selecciona una opcion:
echo.
echo 1. Ejecutar TODOS los tests
echo 2. Ejecutar solo tests de validadores
echo 3. Ejecutar tests con cobertura
echo 4. Ejecutar tests con reporte HTML
echo 5. Ejecutar un test especifico
echo 6. Instalar dependencias de testing
echo 7. Salir
echo.

set /p opcion="Ingresa el numero de opcion: "

if "%opcion%"=="1" (
    echo.
    echo Ejecutando todos los tests...
    pytest -v
    goto fin
)

if "%opcion%"=="2" (
    echo.
    echo Ejecutando tests de validadores...
    pytest app/tests/test_validators.py -v
    goto fin
)

if "%opcion%"=="3" (
    echo.
    echo Ejecutando tests con cobertura...
    pytest --cov=app --cov-report=term-missing
    goto fin
)

if "%opcion%"=="4" (
    echo.
    echo Ejecutando tests con reporte HTML...
    pytest --cov=app --cov-report=html
    echo.
    echo [OK] Reporte generado en: htmlcov/index.html
    echo Abriendo reporte en navegador...
    start htmlcov/index.html
    goto fin
)

if "%opcion%"=="5" (
    echo.
    echo Tests disponibles:
    echo.
    echo   TestValidateDirectorName
    echo   TestValidatePasswordStrength
    echo   TestValidateUsername
    echo   TestValidateEmailFormat
    echo   TestValidateAnioFormat
    echo   TestValidateDateRange
    echo   TestValidateProjectDuration
    echo   TestValidatePeriodoDates
    echo   TestValidateCodigoUniqueFormat
    echo   TestValidatePresupuestoRange
    echo.
    set /p clase="Ingresa el nombre de la clase de test: "
    pytest app/tests/test_validators.py::!clase! -v
    goto fin
)

if "%opcion%"=="6" (
    echo.
    echo Instalando dependencias de testing...
    pip install -r requirements-dev.txt
    echo.
    echo [OK] Dependencias instaladas
    goto fin
)

if "%opcion%"=="7" (
    echo.
    echo Saliendo...
    goto fin
)

echo.
echo [ERROR] Opcion invalida
echo.

:fin
echo.
pause
