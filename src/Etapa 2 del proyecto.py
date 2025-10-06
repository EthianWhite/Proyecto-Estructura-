
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import pandas as pd
import matplotlib.pyplot as plt
import os


DEFAULT_APPS = ["Instagram", "TikTok", "YouTube", "WhatsApp", "Games", "Other", "Study", "Reading", "Exercise"]
CHART_OUTPUT = "ratio_reallocation.png"

def ask_estimates_and_values(apps):
    """Ask user for ESTIMATED daily minutes and PRODUCTIVITY VALUE (1-10) per app/activity."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Fase 2 — Estimaciones + Valor", 
                        "Ingresa para cada app/actividad:\n• Minutos por DÍA (estimados)\n• Valor de productividad (1-10)")
    est_minutes = {}
    values = {}
    for app in apps:
        while True:
            val = simpledialog.askinteger("Estimación diaria", f"[{app}] Minutos por DÍA (estimado):", minvalue=0)
            if val is None: raise KeyboardInterrupt("Cancelled by user")
            try:
                est_minutes[app] = int(val)
                break
            except: pass
        while True:
            v = simpledialog.askinteger("Valor de productividad", f"[{app}] Valor (1-10):", minvalue=1, maxvalue=10)
            if v is None: raise KeyboardInterrupt("Cancelled by user")
            try:
                values[app] = int(v)
                break
            except: pass
    return est_minutes, values

def pick_excel_file():
    root = tk.Tk(); root.withdraw()
    path = filedialog.askopenfilename(
        title="Selecciona el Excel con USO REAL (por día) — hoja 'usage' (date, app, minutes)",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not path: raise KeyboardInterrupt("No file selected")
    return path

def load_usage(path):
    try:
        df = pd.read_excel(path, sheet_name="usage")
    except Exception:
        df = pd.read_excel(path)
    cols = {c.lower(): c for c in df.columns}
    for c in ["date","app","minutes"]:
        if c not in cols: raise ValueError(f"Falta columna '{c}'")
    df = df.rename(columns={cols["date"]:"date", cols["app"]:"app", cols["minutes"]:"minutes"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["app"] = df["app"].astype(str)
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    return df

def weekly_totals(df):
    return df.groupby("app", as_index=False)["minutes"].sum()

def build_ratio_table(weekly, values):
    """Compute ratio = value / time (hours) using ACTUAL weekly usage scaled to per-day."""

    m_per_day = weekly.set_index("app")["minutes"].to_dict()
    data = []
    apps = sorted(set(list(m_per_day.keys()) + list(values.keys())))
    for app in apps:
        week_m = int(m_per_day.get(app, 0))
        day_m = week_m / 7.0
        hours = day_m / 60.0 if day_m > 0 else 0.0
        val = values.get(app, 1)
        ratio = (val / hours) if hours > 0 else float('inf') if val>0 else 0.0
        data.append({"app":app, "value":val, "day_minutes":day_m, "ratio_value_per_hour":ratio})
    return pd.DataFrame(data).sort_values(by=["ratio_value_per_hour","value"], ascending=[False, False])

def greedy_reallocation(df_ratio, goal_recover_minutes_per_day):
    """
    Greedy (ratio): increase time in high-ratio apps, reduce from low-ratio apps,
    while meeting the 'goal_recover_minutes_per_day' (minutes to shift from low to high).
    Rule: cut FIRST from lowest ratio; add FIRST to highest ratio.
    """

    inc_order = df_ratio.sort_values(by="ratio_value_per_hour", ascending=False).reset_index(drop=True)
    dec_order = df_ratio.sort_values(by="ratio_value_per_hour", ascending=True).reset_index(drop=True)
    remaining = float(goal_recover_minutes_per_day)
    cuts = [] 
    adds = []  


    for i in range(len(dec_order)):
        if remaining <= 0: break
        app = dec_order.loc[i, "app"]
        current = float(dec_order.loc[i, "day_minutes"])
        if current <= 0: continue
 
        cap = max(0.0, 0.4*current)
        take = min(cap, remaining)

        take = int(5 * round(take / 5.0))
        if take <= 0: continue
        cuts.append((app, take))
        remaining -= take
        dec_order.loc[i, "day_minutes"] = current - take


    to_add = sum(m for _,m in cuts)
    remaining_add = float(to_add)
    for i in range(len(inc_order)):
        if remaining_add <= 0: break
        app = inc_order.loc[i, "app"]

        val = int(inc_order.loc[i, "value"])
        if val < 6: continue
        base = float(inc_order.loc[i, "day_minutes"])
        cap = max(15.0, 0.3*max(30.0, base))  
        give = min(cap, remaining_add)
        give = int(5 * round(give / 5.0))
        if give <= 0: continue
        adds.append((app, give))
        remaining_add -= give

    return cuts, adds, remaining

def plot_ratios(df_ratio, path):

    apps = df_ratio["app"].tolist()
    daym = df_ratio["day_minutes"].tolist()
    vals = df_ratio["value"].tolist()
    plt.figure()
    x = range(len(apps))
    width = 0.4
    plt.bar([i - width/2 for i in x], daym, width=width, label="Min/día (reales)")
    plt.bar([i + width/2 for i in x], vals, width=width, label="Valor (1-10)")
    plt.xticks(list(x), apps, rotation=30, ha="right")
    plt.ylabel("Min/día y Valor")
    plt.title("Uso real por día vs Valor (1-10) — Ordenado por Ratio Valor/Hora")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def main():

    est, values = ask_estimates_and_values(DEFAULT_APPS)


    root = tk.Tk(); root.withdraw()
    goal = simpledialog.askinteger("Objetivo", "¿Cuántos minutos por DÍA quieres RECUPERAR de ocio para productividad? (ej. 60)", minvalue=0)
    if goal is None: goal = 0


    excel_path = pick_excel_file()
    df = load_usage(excel_path)
    week = weekly_totals(df)


    ratio_df = build_ratio_table(week, values)
    plot_ratios(ratio_df, CHART_OUTPUT)


    cuts, adds, rem = greedy_reallocation(ratio_df, goal)


    out_dir = os.path.dirname(excel_path)
    ratio_csv = os.path.join(out_dir, "phase2_ratio_table.csv")
    ratio_df.to_csv(ratio_csv, index=False)

    lines = ["Recomendaciones (Greedy por Ratio Valor/Hora):"]
    if cuts:
        lines.append("\nCORTES sugeridos (bloqueo por app, min/día):")
        for app, m in cuts:
            lines.append(f"• {app}: bloquear {m} min/día")
    if adds:
        lines.append("\nASIGNACIONES sugeridas (incrementar tiempo productivo, min/día):")
        for app, m in adds:
            lines.append(f"• {app}: añadir {m} min/día")
    if rem > 0:
        lines.append(f"\nNota: Faltan {int(rem)} min/día para alcanzar el objetivo. Considera aumentar cortes o el objetivo.")

    lines.append(f"\nSe guardó la tabla: {ratio_csv}")
    lines.append(f"Gráfica: {os.path.abspath(CHART_OUTPUT)}")

    messagebox.showinfo("Resultados", "\n".join(lines))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Error", str(e))
