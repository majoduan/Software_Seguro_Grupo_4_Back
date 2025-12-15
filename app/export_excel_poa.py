# export_excel_poa.py
"""
Módulo para exportar POAs a Excel con formato institucional EXACTO de la plantilla.

Características:
- Nombre de hoja: "POA {año}" (ej: "POA 2025")
- Encabezado institucional con título, dirección y código de proyecto
- Estructura de columnas:
  * A: Nombre de actividad/tarea
  * B: DESCRIPCIÓN O DETALLE
  * C: ITEM PRESUPUESTARIO
  * D: CANTIDAD (sin decimales)
  * E: PRECIO UNITARIO
  * F: TOTAL (fórmula =D*E)
  * G: TOTAL POR ACTIVIDAD (fórmula suma de F por actividad)
  * H-S: 12 meses (formato "ene-26", "feb-26"...)
  * T: SUMAN (fórmula suma de meses)
- Fórmulas automáticas de suma (=SUM(), =CANTIDAD*PRECIO)
- Colores institucionales EXACTOS de la plantilla
- 100% compatible con transformador_excel.py para re-importación
- Maneja POAs vacíos (genera solo encabezados)
"""

import io
from collections import defaultdict
import xlsxwriter


def generar_excel_poa(reporte: list, poa_vacio: bool = False) -> io.BytesIO:
    """
    Genera archivo Excel con formato institucional EXACTO y compatible con importación.

    Args:
        reporte: Lista de tareas con estructura:
            - anio_poa: str
            - codigo_proyecto: str
            - nombre: str (formato "9.1 Descripción")
            - detalle_descripcion: str
            - item_presupuestario: str
            - cantidad: int/float
            - precio_unitario: float
            - total: float
            - programacion_mensual: dict (claves: "enero", "febrero", etc.)
        poa_vacio: bool - Si True, genera archivo con solo encabezados

    Returns:
        BytesIO con el archivo Excel generado
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Obtener año del POA y código de proyecto
    anio_poa = reporte[0]["anio_poa"] if reporte else ""
    codigo_proyecto = reporte[0]["codigo_proyecto"] if reporte else ""

    # Crear hoja con nombre "POA {año}"
    worksheet = workbook.add_worksheet(f"POA {anio_poa}")

    # ========== DEFINIR FORMATOS ==========

    # Encabezados de columnas (gris claro, negrita)
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9D9D9',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 9
    })

    # Filas de actividades (azul claro, negrita)
    actividad_format = workbook.add_format({
        'bold': True,
        'bg_color': '#B4C7E7',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 10
    })

    # Fila TOTAL PRESUPUESTO (amarillo, negrita)
    total_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FFFF00',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'font_size': 10
    })

    # Celdas de texto normales
    texto_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 9
    })

    # Celdas centradas
    centro_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 9
    })

    # Cantidad (ENTERO SIN DECIMALES)
    cantidad_format = workbook.add_format({
        'num_format': '0',  # Sin decimales
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 9
    })

    # Moneda normal
    moneda_format = workbook.add_format({
        'num_format': '"$"#,##0.00',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 9
    })

    # Moneda en totales (amarillo)
    moneda_total_format = workbook.add_format({
        'num_format': '"$"#,##0.00',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#FFFF00',
        'bold': True,
        'font_size': 9
    })

    # Moneda en actividades (azul claro)
    moneda_actividad_format = workbook.add_format({
        'num_format': '"$"#,##0.00',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#B4C7E7',
        'bold': True,
        'font_size': 9
    })

    # Formato de fecha para encabezados de meses (mmm-yy)
    fecha_header_format = workbook.add_format({
        'num_format': 'mmm-yy',  # Formato: ene-26, feb-26
        'bold': True,
        'bg_color': '#D9D9D9',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 9
    })

    # ========== AGRUPAR TAREAS POR ACTIVIDAD ==========

    actividades_dict = defaultdict(list)
    descripciones_actividades = {}  # Diccionario para guardar las descripciones de actividades

    # Si el POA no está vacío, agrupar tareas
    if not poa_vacio and reporte and reporte[0].get("nombre"):
        for tarea in reporte:
            nombre_tarea = tarea.get("nombre", "")
            if nombre_tarea:  # Solo procesar tareas con nombre
                # Extraer número de actividad (ej: "9.1" -> 9)
                partes = nombre_tarea.split(".")
                if len(partes) >= 1 and partes[0].strip().isdigit():
                    num_actividad = int(partes[0].strip())
                    actividades_dict[num_actividad].append(tarea)

                    # Guardar descripción de actividad (del primer registro de cada actividad)
                    if num_actividad not in descripciones_actividades:
                        descripciones_actividades[num_actividad] = tarea.get("descripcion_actividad", f"Actividad {num_actividad}")

    actividades_ordenadas = sorted(actividades_dict.items())

    # ========== CONFIGURAR COLUMNAS ==========

    meses_orden = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Generar fechas en formato "ene-26", "feb-26", etc. (texto visible)
    # Y también generar objetos datetime para las fórmulas de Excel
    meses_abreviados = {
        "enero": "ene", "febrero": "feb", "marzo": "mar", "abril": "abr",
        "mayo": "may", "junio": "jun", "julio": "jul", "agosto": "ago",
        "septiembre": "sept", "octubre": "oct", "noviembre": "nov", "diciembre": "dic"
    }

    fechas_headers = []  # Formato texto: "ene-26", "feb-26"
    fechas_excel = []    # Objetos datetime para Excel
    anio_siguiente = int(anio_poa) + 1
    anio_corto = str(anio_siguiente)[-2:]  # Últimos 2 dígitos (ej: 2026 -> 26)

    from datetime import datetime
    for i, mes in enumerate(meses_orden, start=1):
        mes_abr = meses_abreviados[mes]
        fecha_texto = f"{mes_abr}-{anio_corto}"  # Formato visible: "ene-26"
        fecha_obj = datetime(anio_siguiente, i, 1)  # Objeto datetime para Excel
        fechas_headers.append(fecha_texto)
        fechas_excel.append(fecha_obj)

    # Definir posición de columnas (según plantilla institucional)
    COL_NOMBRE_TAREA = 0          # A
    COL_DESCRIPCION = 1           # B (DESCRIPCIÓN O DETALLE)
    COL_ITEM_PRESU = 2            # C (ITEM PRESUPUESTARIO)
    COL_CANTIDAD = 3              # D (CANTIDAD)
    COL_PRECIO_UNIT = 4           # E (PRECIO UNITARIO)
    COL_TOTAL = 5                 # F (TOTAL)
    COL_TOTAL_POR_ACTIVIDAD = 6   # G (TOTAL POR ACTIVIDAD) ✅ CORREGIDO
    COL_MESES_INICIO = 7          # H-S (12 meses: columnas 7-18)
    COL_SUMAN = 19                # T (SUMAN)

    # Ajustar anchos de columna (según plantilla)
    worksheet.set_column(COL_NOMBRE_TAREA, COL_NOMBRE_TAREA, 45)           # A
    worksheet.set_column(COL_DESCRIPCION, COL_DESCRIPCION, 45)             # B
    worksheet.set_column(COL_ITEM_PRESU, COL_ITEM_PRESU, 16)               # C
    worksheet.set_column(COL_CANTIDAD, COL_CANTIDAD, 11)                   # D
    worksheet.set_column(COL_PRECIO_UNIT, COL_PRECIO_UNIT, 12)             # E
    worksheet.set_column(COL_TOTAL, COL_TOTAL, 12)                         # F
    worksheet.set_column(COL_TOTAL_POR_ACTIVIDAD, COL_TOTAL_POR_ACTIVIDAD, 18)  # G
    worksheet.set_column(COL_MESES_INICIO, COL_MESES_INICIO + 11, 11)      # H-S (12 meses)
    worksheet.set_column(COL_SUMAN, COL_SUMAN, 12)                         # T

    # ========== ESCRIBIR ENCABEZADO INSTITUCIONAL ==========

    fila_actual = 0

    # Formato para encabezado institucional (sin bordes, centrado, negrita)
    titulo_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 11
    })

    # Fila 1: VACÍA
    fila_actual += 1

    # Fila 2: VICERRECTORADO DE INVESTIGACIÓN, INNOVACIÓN Y VINCULACIÓN (merge A-G)
    worksheet.merge_range(fila_actual, 0, fila_actual, 6,
                          'VICERRECTORADO DE INVESTIGACIÓN, INNOVACIÓN Y VINCULACIÓN',
                          titulo_format)
    fila_actual += 1

    # Fila 3: DIRECCIÓN DE INVESTIGACIÓN (merge A-G)
    worksheet.merge_range(fila_actual, 0, fila_actual, 6,
                          'DIRECCIÓN DE INVESTIGACIÓN',
                          titulo_format)
    fila_actual += 1

    # Fila 4: PROGRAMACIÓN PARA EL POA {año} (merge A-G)
    worksheet.merge_range(fila_actual, 0, fila_actual, 6,
                          f'PROGRAMACIÓN PARA EL POA {anio_poa}',
                          titulo_format)
    fila_actual += 1

    # Fila 5: PROYECTOS DE INVESTIGACIÓN (merge A-G)
    worksheet.merge_range(fila_actual, 0, fila_actual, 6,
                          'PROYECTOS DE INVESTIGACIÓN',
                          titulo_format)
    fila_actual += 1

    # Fila 6: CODIGO DE PROYECTO: {código} (merge A-G)
    codigo_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 10
    })
    worksheet.merge_range(fila_actual, 0, fila_actual, 6,
                          f'CODIGO DE PROYECTO: {codigo_proyecto}',
                          codigo_format)
    fila_actual += 1

    # Fila 7: TOTAL POR ACTIVIDAD en G7 y PROGRAMACIÓN DE EJECUCIÓN {año+1} en H7-T7
    total_header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FCE4D6',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 9
    })
    worksheet.write(fila_actual, COL_TOTAL_POR_ACTIVIDAD, 'TOTAL POR\nACTIVIDAD', total_header_format)

    # PROGRAMACIÓN DE EJECUCIÓN {año+1} desde H7 hasta T7
    prog_ejecucion_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9D9D9',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 9
    })
    anio_siguiente = int(anio_poa) + 1
    worksheet.merge_range(fila_actual, COL_MESES_INICIO, fila_actual, COL_SUMAN,
                          f'PROGRAMACIÓN DE EJECUCIÓN {anio_siguiente}',
                          prog_ejecucion_format)
    fila_actual += 1

    # ========== ESCRIBIR ENCABEZADOS DE COLUMNAS ==========

    # Encabezado de columnas de datos
    cabecera_datos = [
        "",  # Columna vacía para nombres de actividad/tarea
        "DESCRIPCIÓN O DETALLE",
        "ITEM\nPRESUPUESTARIO",
        "CANTIDAD\n(Meses de contrato)",
        "PRECIO\nUNITARIO",
        "TOTAL"
    ]

    # Escribir encabezados principales (A-F)
    for col_idx, header_text in enumerate(cabecera_datos):
        worksheet.write(fila_actual, col_idx, header_text, header_format)

    # Columna G: TOTAL POR ACTIVIDAD (encabezado ya escrito en fila 7, aquí va vacío)
    # No se escribe nada aquí

    # Escribir encabezados de meses (H-S) usando objetos datetime con formato mmm-yy
    for i, fecha_obj in enumerate(fechas_excel):
        col_idx = COL_MESES_INICIO + i
        worksheet.write_datetime(fila_actual, col_idx, fecha_obj, fecha_header_format)

    # Columna T: SUMAN
    worksheet.write(fila_actual, COL_SUMAN, 'SUMAN', header_format)

    fila_actual += 1

    # ========== ESCRIBIR ACTIVIDADES Y TAREAS ==========

    primera_fila_datos = fila_actual  # Guardar para fórmulas de totales

    for num_actividad, tareas_actividad in actividades_ordenadas:
        # Guardar fila de inicio de actividad para fórmulas
        fila_inicio_actividad = fila_actual

        # FILA DE ACTIVIDAD - Usar descripción real desde la base de datos
        descripcion_real = descripciones_actividades.get(num_actividad, f"Actividad {num_actividad}")
        descripcion_actividad = f"({num_actividad}) {descripcion_real}"
        worksheet.write(fila_actual, COL_NOMBRE_TAREA, descripcion_actividad, actividad_format)

        # FÓRMULA: TOTAL POR ACTIVIDAD (suma de totales de tareas)
        # Se calculará después de escribir las tareas
        fila_actividad_actual = fila_actual
        fila_actual += 1

        # FILAS DE TAREAS
        fila_inicio_tareas = fila_actual
        for tarea in tareas_actividad:
            prog = tarea.get("programacion_mensual", {})

            # Columna 0: Nombre de tarea
            worksheet.write(fila_actual, COL_NOMBRE_TAREA, tarea["nombre"], texto_format)

            # Columna 1: Descripción
            worksheet.write(fila_actual, COL_DESCRIPCION, tarea["detalle_descripcion"], texto_format)

            # Columna 2: Item presupuestario
            worksheet.write(fila_actual, COL_ITEM_PRESU, tarea["item_presupuestario"], centro_format)

            # Columna 3: Cantidad (SIN DECIMALES)
            worksheet.write_number(fila_actual, COL_CANTIDAD, tarea["cantidad"], cantidad_format)

            # Columna 4: Precio unitario
            worksheet.write_number(fila_actual, COL_PRECIO_UNIT, tarea["precio_unitario"], moneda_format)

            # Columna 5: TOTAL (FÓRMULA: =CANTIDAD * PRECIO UNITARIO)
            celda_cantidad = xl_rowcol_to_cell(fila_actual, COL_CANTIDAD)
            celda_precio = xl_rowcol_to_cell(fila_actual, COL_PRECIO_UNIT)
            formula_total = f"={celda_cantidad}*{celda_precio}"
            worksheet.write_formula(fila_actual, COL_TOTAL, formula_total, moneda_format)

            # Columna 6 (G): TOTAL POR ACTIVIDAD - Vacía para tareas (solo en fila de actividad)
            # No se escribe nada aquí

            # Columnas 7-18 (H-S): 12 meses VISIBLES
            for col_idx, mes in enumerate(meses_orden, start=COL_MESES_INICIO):
                valor_mes = prog.get(mes, 0)
                worksheet.write_number(fila_actual, col_idx, valor_mes, moneda_format)

            # Columna 19 (T): SUMAN (FÓRMULA: =SUMA(meses))
            celda_inicio_meses = xl_rowcol_to_cell(fila_actual, COL_MESES_INICIO)
            celda_fin_meses = xl_rowcol_to_cell(fila_actual, COL_MESES_INICIO + 11)
            formula_suman = f"=SUM({celda_inicio_meses}:{celda_fin_meses})"
            worksheet.write_formula(fila_actual, COL_SUMAN, formula_suman, moneda_format)

            fila_actual += 1

        fila_fin_tareas = fila_actual - 1

        # Escribir FÓRMULA en fila de actividad: TOTAL POR ACTIVIDAD
        celda_inicio_totales = xl_rowcol_to_cell(fila_inicio_tareas, COL_TOTAL)
        celda_fin_totales = xl_rowcol_to_cell(fila_fin_tareas, COL_TOTAL)
        formula_total_actividad = f"=SUM({celda_inicio_totales}:{celda_fin_totales})"
        worksheet.write_formula(fila_actividad_actual, COL_TOTAL_POR_ACTIVIDAD, formula_total_actividad, moneda_actividad_format)

    fila_fin_datos = fila_actual - 1

    # ========== FILA FINAL: TOTAL PRESUPUESTO ==========

    # Merge de A a F con texto centrado "TOTAL PRESUPUESTO POA-{año}"
    total_presupuesto_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FFFF00',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 10
    })
    worksheet.merge_range(fila_actual, 0, fila_actual, COL_TOTAL,
                          f'TOTAL PRESUPUESTO POA-{anio_poa}',
                          total_presupuesto_format)

    # FÓRMULA: Suma de todas las columnas de meses
    for col_idx in range(COL_MESES_INICIO, COL_MESES_INICIO + 12):
        celda_inicio = xl_rowcol_to_cell(primera_fila_datos, col_idx)
        celda_fin = xl_rowcol_to_cell(fila_fin_datos, col_idx)
        formula_mes_total = f"=SUM({celda_inicio}:{celda_fin})"
        worksheet.write_formula(fila_actual, col_idx, formula_mes_total, moneda_total_format)

    # FÓRMULA: SUMAN total
    celda_inicio_suman = xl_rowcol_to_cell(primera_fila_datos, COL_SUMAN)
    celda_fin_suman = xl_rowcol_to_cell(fila_fin_datos, COL_SUMAN)
    formula_suman_total = f"=SUM({celda_inicio_suman}:{celda_fin_suman})"
    worksheet.write_formula(fila_actual, COL_SUMAN, formula_suman_total, moneda_total_format)

    # FÓRMULA: TOTAL POR ACTIVIDAD (suma de todos los totales)
    celda_inicio_total = xl_rowcol_to_cell(primera_fila_datos, COL_TOTAL_POR_ACTIVIDAD)
    celda_fin_total = xl_rowcol_to_cell(fila_fin_datos, COL_TOTAL_POR_ACTIVIDAD)
    formula_total_presupuesto = f"=SUM({celda_inicio_total}:{celda_fin_total})"
    worksheet.write_formula(fila_actual, COL_TOTAL_POR_ACTIVIDAD, formula_total_presupuesto, moneda_total_format)

    fila_actual += 1

    # ========== NOTAS AL FINAL ==========

    # Formato para las notas (sin fondo, alineación izquierda)
    nota_format = workbook.add_format({
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 9
    })

    # Saltar una fila
    fila_actual += 1

    # Merge de columnas A-G para las 3 notas
    notas_texto = (
        "Nota1: La planificación del POA 2024 corresponde a la ejecución presupuestaria que se "
        "llevará a cabo a partir del inicio del proyecto hasta diciembre de 2026\n\n"
        "Nota 2: En el caso que se requiera reformas presupuestarias o reformas al POA para la "
        "inclusión o retiro de ítems, se deberá completar la matriz de reformas y realizar la "
        "solicitud correspondiente\n\n"
        "Nota 3: Considerar que las contrataciones de personal las podrán solicitar una vez que "
        "ha iniciado el proyecto y estas iniciarán el mes siguiente a la solicitud."
    )

    worksheet.merge_range(fila_actual, 0, fila_actual + 2, 6, notas_texto, nota_format)

    # Ajustar altura de las filas de notas para que se vean completas
    worksheet.set_row(fila_actual, 60)
    worksheet.set_row(fila_actual + 1, 60)
    worksheet.set_row(fila_actual + 2, 60)

    workbook.close()
    output.seek(0)
    return output


def xl_rowcol_to_cell(row, col):
    """
    Convierte índices de fila/columna a notación Excel (ej: 0,0 -> A1)

    Args:
        row: Índice de fila (0-based)
        col: Índice de columna (0-based)

    Returns:
        str: Celda en notación Excel (ej: "A1", "B2", "AA10")
    """
    col_str = ""
    col_tmp = col
    while col_tmp >= 0:
        col_str = chr(col_tmp % 26 + 65) + col_str
        col_tmp = col_tmp // 26 - 1
    return f"{col_str}{row + 1}"
