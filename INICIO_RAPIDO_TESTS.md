# 🚀 Inicio Rápido - Tests Unitarios

## En 3 pasos

### 1️⃣ Instalar pytest

```bash
pip install pytest pytest-asyncio pytest-cov
```

### 2️⃣ Ejecutar tests

```bash
pytest app/tests/test_validators.py -v
```

### 3️⃣ Ver cobertura

```bash
pytest --cov=app.validators --cov-report=term-missing
```

---

## ⚡ Opción más fácil (Windows)

**Doble clic en:** `run_tests.bat`

Menú interactivo que te guía paso a paso.

---

## ⚡ Opción más fácil (Linux/Mac)

```bash
chmod +x run_tests.sh
./run_tests.sh
```

---

## 📊 Resultados Esperados

### ✅ Si todo funciona bien:

```
======================== test session starts =========================
collected 69 items

app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_dos_palabras PASSED
app/tests/test_validators.py::TestValidateDirectorName::test_nombre_valido_ocho_palabras PASSED
...
======================== 69 passed in 0.35s ==========================
```

### ❌ Si pytest no está instalado:

```
'pytest' is not recognized as an internal or external command
```

**Solución:** Ejecutar paso 1️⃣ arriba.

---

## 📝 ¿Qué se está probando?

Los **69 tests** validan todas las reglas del frontend ahora en el backend:

- ✅ Nombres de director (2-8 palabras, solo letras)
- ✅ Contraseñas (mínimo 8 caracteres, mayúscula + número)
- ✅ Emails (formato válido)
- ✅ Fechas (coherencia, rangos)
- ✅ Presupuestos (positivos, dentro de límites)
- ✅ Códigos (longitudes, unicidad)
- ✅ Y más...

---

## 🔍 Ver detalles

Lee la [Guía Completa de Tests](GUIA_TESTS.md) para más información.

---

## 🆘 Problemas?

### Problema: ModuleNotFoundError

```bash
# Solución: Asegúrate de estar en la carpeta correcta
cd Software_Seguro_Grupo_4_Back
pytest app/tests/test_validators.py
```

### Problema: Import errors

```bash
# Solución: Instala las dependencias
pip install -r requirements.txt
pip install python-dateutil
```

---

**¡Eso es todo!** 🎉

Ejecuta los tests y verifica que todo funciona correctamente.
