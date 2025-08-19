import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

# === ARCHIVO ===
archivo_excel = r"C:\Users\Usuario\Downloads\Formulario sin título (respuestas) (2).xlsx"
df = pd.read_excel(archivo_excel)

# === LIMPIEZA BÁSICA DE ENCABEZADOS ===
df.columns = (df.columns
              .str.strip()
              .str.replace('\u200f', '', regex=False)
              .str.replace('\u200e', '', regex=False))

# === HELPERS DE NORMALIZACIÓN ===
def a_horas(x):
    """Convierte entradas tipo '3', '3,5', '3:00', '1-2', '3 horas' -> horas (float)."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip().lower().replace(',', '.')
    # hh:mm[:ss]
    if re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', s):
        try:
            td = pd.to_timedelta(s)
            return td.total_seconds() / 3600.0
        except Exception:
            pass
    # rango a-b -> promedio
    m = re.match(r'^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$', s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (a + b) / 2.0
    # número con o sin "hora(s)"
    m = re.match(r'^\s*(\d+(?:\.\d+)?)\s*(h|hora|horas)?\s*$', s)
    if m:
        return float(m.group(1))
    # último recurso: primer número que aparezca
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    if m:
        return float(m.group(1))
    return np.nan

def a_porcentaje_0a100(x):
    """Convierte '60', '60%', '60 % útil', '0,6', '0.6' -> 0..100 (float)."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(',', '.').replace('%', '')
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    if not m:
        return np.nan
    v = float(m.group(0))
    if 0 <= v <= 1:
        v *= 100.0
    return v

# === NOMBRES DE COLUMNAS (sin espacios finales) ===
col_ocup = "Ocupación principal:"
col_total = "¿Cuántas horas al día usas tus dispositivos?"
col_redes = "¿Cuántas horas al día dedicas a aplicaciones de Redes sociales (ej. Instagram, TikTok, Facebook)?"
col_mens  = "¿Cuántas horas al día dedicas a aplicaciones de mensajería (WhatsApp, Telegram, etc.)?"
col_ent   = "¿Cuántas horas al día dedicas a entretenimiento (Netflix, YouTube, Spotify, etc.)?"
col_jueg  = "¿Cuántas horas al día dedicas a videojuegos en línea o apps de juegos móviles?"
col_trab  = "¿Cuántas horas al día dedicas a aplicaciones de trabajo o estudio (Office, Google Drive, Zoom, etc.)?"

# Columna del % útil -> se busca dinámicamente por si viene truncada
col_util = None
for c in df.columns:
    cs = c.lower()
    if "del tiempo total que pasas en dispositivos" in cs and "porcentaje" in cs and "útil" in cs:
        col_util = c
        break
if col_util is None:
    raise KeyError("No se encontró la columna del porcentaje útil. Revisa df.columns para ver el nombre exacto.")

# === CONVERSIÓN DE DATOS ===
for c in [col_total, col_redes, col_mens, col_ent, col_jueg, col_trab]:
    if c in df.columns:
        df[c] = df[c].apply(a_horas)

df[col_util] = df[col_util].apply(a_porcentaje_0a100)

# === CÁLCULOS GLOBALES ===
promedio_total_horas = df[col_total].mean()
promedio_redes = df[col_redes].mean()
promedio_mensajeria = df[col_mens].mean()
promedio_entretenimiento = df[col_ent].mean()
promedio_videojuegos = df[col_jueg].mean()
promedio_trabajo = df[col_trab].mean()
promedio_util = df[col_util].mean()  # <- promedio global de % útil

print("=== Promedios globales ===")
print("Promedio total de horas en dispositivos:", promedio_total_horas)
print("Distribución promedio (horas/día):")
print(" - Redes sociales:", promedio_redes)
print(" - Mensajería:", promedio_mensajeria)
print(" - Entretenimiento:", promedio_entretenimiento)
print(" - Videojuegos:", promedio_videojuegos)
print(" - Trabajo/Estudio:", promedio_trabajo)
print("Promedio % útil (global):", promedio_util)

# === SEPARACIÓN DE GRUPOS: Estudiantes vs Trabajadores (empleados + independientes) ===
# Patrón: contiene 'emplead' (empleado/empleada) o 'independ' (independiente)
mask_est = df[col_ocup].str.contains("estudiante", case=False, na=False)
mask_trab = df[col_ocup].str.contains(r"(emplead|independ)", case=False, na=False)

estudiantes = df[mask_est]
trabajadores = df[mask_trab]

col_actividades = [col_redes, col_mens, col_ent, col_jueg, col_trab]
labels = ["Redes", "Mensajería", "Entretenimiento", "Videojuegos", "Trabajo/Estudio"]

# Promedios por grupo
prom_total_est = estudiantes[col_total].mean()
prom_total_trab = trabajadores[col_total].mean()

prom_acts_est = estudiantes[col_actividades].mean()
prom_acts_trab = trabajadores[col_actividades].mean()

prom_util_est = estudiantes[col_util].mean()
prom_util_trab = trabajadores[col_util].mean()

print("\n=== Comparación por grupo ===")
print(f"Estudiantes: n={len(estudiantes)}")
print(" - Horas totales:", prom_total_est)
print(" - % útil:", prom_util_est)
print(" - Actividades (horas/día):")
for nom, val in zip(labels, prom_acts_est.values):
    print(f"   · {nom}: {val}")

print(f"\nTrabajadores (empleados + independientes): n={len(trabajadores)}")
print(" - Horas totales:", prom_total_trab)
print(" - % útil:", prom_util_trab)
print(" - Actividades (horas/día):")
for nom, val in zip(labels, prom_acts_trab.values):
    print(f"   · {nom}: {val}")

# === GRÁFICOS ===
# 1) Pastel global de distribución
valores = [promedio_redes, promedio_mensajeria, promedio_entretenimiento, promedio_videojuegos, promedio_trabajo]
plt.figure(figsize=(7,7))
plt.pie(valores, labels=labels, autopct="%1.1f%%", startangle=90)
plt.title("Distribución promedio global del uso por tipo de app")
plt.show()

# 2) Barras comparación Estudiantes vs Trabajadores por actividades
plt.figure(figsize=(9,6))
x = np.arange(len(labels))
plt.bar(x - 0.2, prom_acts_est.values, width=0.4, label="Estudiantes")
plt.bar(x + 0.2, prom_acts_trab.values, width=0.4, label="Trabajadores (empleados + independientes)")
plt.xticks(x, labels)
plt.ylabel("Horas promedio por día")
plt.title("Uso por tipo de app: Estudiantes vs Trabajadores")
plt.legend()
plt.show()

# 3) Barras del % útil por grupo
plt.figure(figsize=(6,5))
grupos = ["Estudiantes", "Trabajadores"]
val_util = [prom_util_est, prom_util_trab]
plt.bar(grupos, val_util)
plt.ylabel("% de uso útil (promedio)")
plt.title("Porcentaje de uso útil: Estudiantes vs Trabajadores")
plt.show()

# 4) (Opcional) Barras de horas totales por grupo
plt.figure(figsize=(6,5))
val_tot = [prom_total_est, prom_total_trab]
plt.bar(grupos, val_tot)
plt.ylabel("Horas totales (promedio/día)")
plt.title("Horas totales: Estudiantes vs Trabajadores")
plt.show()
