#!/bin/bash
# Script para ejecutar tests en Linux/Mac

echo "========================================"
echo "  Tests Unitarios - Backend"
echo "========================================"
echo ""

# Verificar si pytest está instalado
if ! python -c "import pytest" 2>/dev/null; then
    echo "[ERROR] pytest no está instalado"
    echo ""
    echo "Instalando pytest..."
    pip install pytest pytest-asyncio pytest-cov
    echo ""
fi

# Menú de opciones
echo "Selecciona una opción:"
echo ""
echo "1. Ejecutar TODOS los tests"
echo "2. Ejecutar solo tests de validadores"
echo "3. Ejecutar tests con cobertura"
echo "4. Ejecutar tests con reporte HTML"
echo "5. Ejecutar un test específico"
echo "6. Instalar dependencias de testing"
echo "7. Salir"
echo ""

read -p "Ingresa el número de opción: " opcion

case $opcion in
    1)
        echo ""
        echo "Ejecutando todos los tests..."
        pytest -v
        ;;
    2)
        echo ""
        echo "Ejecutando tests de validadores..."
        pytest app/tests/test_validators.py -v
        ;;
    3)
        echo ""
        echo "Ejecutando tests con cobertura..."
        pytest --cov=app --cov-report=term-missing
        ;;
    4)
        echo ""
        echo "Ejecutando tests con reporte HTML..."
        pytest --cov=app --cov-report=html
        echo ""
        echo "[OK] Reporte generado en: htmlcov/index.html"
        echo "Abriendo reporte en navegador..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open htmlcov/index.html
        else
            xdg-open htmlcov/index.html
        fi
        ;;
    5)
        echo ""
        echo "Tests disponibles:"
        echo ""
        echo "  TestValidateDirectorName"
        echo "  TestValidatePasswordStrength"
        echo "  TestValidateUsername"
        echo "  TestValidateEmailFormat"
        echo "  TestValidateAnioFormat"
        echo "  TestValidateDateRange"
        echo "  TestValidateProjectDuration"
        echo "  TestValidatePeriodoDates"
        echo "  TestValidateCodigoUniqueFormat"
        echo "  TestValidatePresupuestoRange"
        echo ""
        read -p "Ingresa el nombre de la clase de test: " clase
        pytest "app/tests/test_validators.py::$clase" -v
        ;;
    6)
        echo ""
        echo "Instalando dependencias de testing..."
        pip install -r requirements-dev.txt
        echo ""
        echo "[OK] Dependencias instaladas"
        ;;
    7)
        echo ""
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo ""
        echo "[ERROR] Opción inválida"
        ;;
esac

echo ""
