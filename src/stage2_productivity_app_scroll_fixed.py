#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import math
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt

DEFAULT_EXCEL = "usage_real.xlsx"  # expected columns: App, RealMinutes (weekly total)

def read_real_usage(path: str) -> pd.DataFrame:
    # Read first sheet by default
    df = pd.read_excel(path)
    cols = {str(c).strip().lower(): c for c in df.columns}
    if "app" not in cols or ("realminutes" not in cols and "real_minutes" not in cols):
        raise ValueError("Excel must include columns: 'App' and 'RealMinutes' (weekly).")
    real_col = cols.get("realminutes", cols.get("real_minutes"))
    out = df[[cols["app"], real_col]].copy()
    out.columns = ["App", "RealMinutes"]
    out["App"] = out["App"].astype(str).str.strip()
    out["RealMinutes"] = pd.to_numeric(out["RealMinutes"], errors="coerce").fillna(0).clip(lower=0)

    # Optional Category support
    is_prod = pd.Series(False, index=out.index)
    if "category" in cols:
        cat_series = df[cols["category"]].astype(str).str.strip().str.lower()
        is_prod = cat_series.isin(["productivity","productivo","productividad","work","trabajo","laboral","office"])
        # Align length if user provided category for fewer rows
        if len(is_prod) != len(out):
            is_prod = is_prod.reindex(out.index, fill_value=False)
    out["IsProductivity"] = is_prod.values
    return out

def greedy_fractional_block(df: pd.DataFrame, total_block_minutes: float, avoid_block_productivity: bool) -> pd.DataFrame:
    df = df.copy()
    eps = 1e-9
    if "EstMinutes" not in df.columns:
        df["EstMinutes"] = 0.0
    df["Disparity"] = (df["RealMinutes"] - df["EstMinutes"]).clip(lower=0)
    ratio = df["RealMinutes"] / (df["EstMinutes"] + eps)
    ratio = ratio.replace([np.inf, -np.inf], 1e6).clip(lower=0, upper=1e6)
    alpha, beta = 0.6, 0.4
    df["UPM"] = alpha * (df["Disparity"] / (df["RealMinutes"] + eps)) + beta * ratio / (ratio.max() + eps)

    if avoid_block_productivity and ("IsProductivity" in df.columns):
        df.loc[df["IsProductivity"] == True, "UPM"] = -1.0

    df = df.sort_values("UPM", ascending=False, kind="mergesort").reset_index(drop=True)

    remaining = float(total_block_minutes)
    blocked = []
    for _, row in df.iterrows():
        if remaining <= 0:
            blocked.append(0.0)
            continue
        if avoid_block_productivity and ("IsProductivity" in df.columns) and bool(row.get("IsProductivity", False)):
            blocked.append(0.0)
            continue
        block_cap = float(row["RealMinutes"])
        take = min(block_cap, remaining)
        blocked.append(take)
        remaining -= take

    df["BlockMinutesSuggested"] = blocked
    df["BlockPerDayMinutes"] = (df["BlockMinutesSuggested"] / 7.0).round(1)
    return df

class ScrollableFrame(ttk.Frame):
    """A vertically scrollable frame using a Canvas + scrollbar pattern."""
    def __init__(self, parent, height=350):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, height=height)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", self._on_frame_configure)

        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Mouse wheel support
        self.inner.bind_all("<MouseWheel>", self._on_mousewheel)       # Windows
        self.inner.bind_all("<Button-4>", self._on_mousewheel_linux)   # Linux up
        self.inner.bind_all("<Button-5>", self._on_mousewheel_linux)   # Linux down

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Resize inner frame to canvas width
        self.canvas.itemconfig(self.window_id, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        # For Windows, delta positive is up, negative is down
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Uso de Apps - Etapa 2 (Prototipo)")
        self.geometry("860x640")
        self.minsize(820, 600)

        self.real_path_var = tk.StringVar(value=DEFAULT_EXCEL)
        self.block_budget_var = tk.StringVar(value="300")
        self.no_block_productivity_var = tk.BooleanVar(value=True)

        header = ttk.Label(self, text="Paso 1: Estima tu uso. Paso 2: Compara vs real y recibe recomendación.", font=("Segoe UI", 12, "bold"))
        header.pack(pady=(12, 6))

        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=16, pady=4)
        ttk.Label(topbar, text="Excel con uso REAL (App, RealMinutes [+ Category opcional]):").pack(side="left")
        ttk.Entry(topbar, textvariable=self.real_path_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(topbar, text="Buscar...", command=self.choose_file).pack(side="left")

        options = ttk.Frame(self)
        options.pack(fill="x", padx=16, pady=4)
        ttk.Label(options, text="Presupuesto de bloqueo (min/semana):").pack(side="left")
        ttk.Entry(options, textvariable=self.block_budget_var, width=10).pack(side="left", padx=8)
        ttk.Checkbutton(options, text="No bloquear apps de productividad (★)", variable=self.no_block_productivity_var).pack(side="left", padx=12)

        # Scrollable estimation area
        self.form_wrapper = ScrollableFrame(self, height=380)
        self.form_wrapper.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # Bottom buttons
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=16, pady=8)
        ttk.Button(btns, text="Cargar apps (no muestra real) → Estimar", command=self.load_and_build_form).pack(side="left")
        ttk.Button(btns, text="Analizar y recomendar", command=self.run_analysis).pack(side="right")

        self.estimate_vars = {}
        self.df_real = None

    def choose_file(self):
        path = filedialog.askopenfilename(title="Selecciona el Excel de uso real", filetypes=[("Excel", "*.xlsx")])
        if path:
            self.real_path_var.set(path)

    def load_and_build_form(self):
        try:
            df_real = read_real_usage(self.real_path_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el Excel: {e}")
            return
        self.df_real = df_real

        # Clear inner frame
        for w in self.form_wrapper.inner.winfo_children():
            w.destroy()
        self.estimate_vars.clear()

        # Label
        mark_prod = ("IsProductivity" in df_real.columns) and df_real["IsProductivity"].any()
        label_text = "1) Ingresa tu estimación (min/sem) por app (sin ver lo real)."
        if mark_prod: label_text += " Las de productividad se marcan con ★."
        ttk.Label(self.form_wrapper.inner, text=label_text).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(0,6))

        # Headers
        ttk.Label(self.form_wrapper.inner, text="App", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(self.form_wrapper.inner, text="Estimado (min/sem)", font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=4, pady=2)

        # Rows
        for i, row in enumerate(df_real.itertuples(index=False), start=2):
            app = row.App
            is_prod = bool(getattr(row, "IsProductivity", False))
            app_label = f"{'★ ' if (mark_prod and is_prod) else ''}{app}"
            ttk.Label(self.form_wrapper.inner, text=app_label).grid(row=i, column=0, sticky="w", padx=4, pady=2)
            var = tk.StringVar(value="")
            self.estimate_vars[app] = var
            ttk.Entry(self.form_wrapper.inner, textvariable=var, width=14).grid(row=i, column=1, sticky="e", padx=4, pady=2)

        self.form_wrapper.inner.grid_columnconfigure(0, weight=1)
        self.form_wrapper.inner.grid_columnconfigure(1, weight=0)

    def run_analysis(self):
        if self.df_real is None:
            messagebox.showwarning("Atención", "Primero carga el Excel y genera el formulario de estimación.")
            return

        est_rows = []
        for app, var in self.estimate_vars.items():
            try:
                est = float(var.get())
            except ValueError:
                est = 0.0
            # Safely read IsProductivity from df_real if exists
            is_prod = False
            if "IsProductivity" in self.df_real.columns:
                try:
                    is_prod = bool(self.df_real.loc[self.df_real["App"] == app, "IsProductivity"].iloc[0])
                except Exception:
                    is_prod = False
            est_rows.append({"App": app, "EstMinutes": max(est, 0.0), "IsProductivity": is_prod})
        df_est = pd.DataFrame(est_rows)

        df = pd.merge(df_est, self.df_real[["App","RealMinutes"] + (["IsProductivity"] if "IsProductivity" in self.df_real.columns else [])], on="App", how="left")
        df["RealMinutes"] = pd.to_numeric(df["RealMinutes"], errors="coerce").fillna(0).clip(lower=0)
        if "IsProductivity" not in df.columns:
            df["IsProductivity"] = False

        try:
            budget = float(self.block_budget_var.get())
        except ValueError:
            budget = 0.0
        budget = max(budget, 0.0)
        avoid_prod = bool(self.no_block_productivity_var.get())

        rec = greedy_fractional_block(df, total_block_minutes=budget, avoid_block_productivity=avoid_prod)
        rec["AbsError"] = (rec["RealMinutes"] - rec["EstMinutes"]).abs()
        rec["Overuse"] = (rec["RealMinutes"] - rec["EstMinutes"]).clip(lower=0)
        rec = rec.sort_values(["Overuse","RealMinutes"], ascending=[False, False]).reset_index(drop=True)

        out_csv = "analysis_report.csv"
        out_xlsx = "analysis_report.xlsx"
        rec.to_csv(out_csv, index=False, encoding="utf-8")
        try:
            rec.to_excel(out_xlsx, index=False)
        except Exception:
            out_xlsx = None

        try:
            plt.figure(figsize=(11,6))
            x = np.arange(len(rec["App"]))
            width = 0.4
            plt.bar(x - width/2, rec["EstMinutes"], width, label="Estimado")
            plt.bar(x + width/2, rec["RealMinutes"], width, label="Real")
            plt.xticks(x, rec["App"], rotation=45, ha="right")
            plt.ylabel("Minutos por semana")
            suffix = " (★ = productividad)" if ("IsProductivity" in rec.columns and rec["IsProductivity"].any()) else ""
            plt.title("Comparación Estimado vs Real por app" + suffix)
            plt.legend()
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showwarning("Gráfica", f"No se pudo mostrar la gráfica: {e}")

        top = rec.iloc[0] if not rec.empty else None
        msg = ["Análisis completado."]
        if top is not None:
            msg.append(f"Top app que te come tiempo: {top['App']} (sobreuso: {int(top['Overuse'])} min/sem)")
        msg.append(f"Presupuesto de bloqueo aplicado: {int(budget)} min/sem")
        if avoid_prod and ("IsProductivity" in rec.columns) and rec["IsProductivity"].any():
            msg.append("Política: NO se bloquean apps de productividad (marcadas con ★).")
        msg.append("Sugerencia bloqueo por día (ej.):")
        for _, row in rec.head(3).iterrows():
            if avoid_prod and ("IsProductivity" in rec.columns) and bool(row.get("IsProductivity", False)):
                continue
            msg.append(f" - {row['App']}: {row['BlockPerDayMinutes']} min/día")
        if out_xlsx:
            msg.append(f"Se guardó: {out_csv} y {out_xlsx}")
        else:
            msg.append(f"Se guardó: {out_csv}")
        messagebox.showinfo("Recomendación", "\n".join(msg))

def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print("GUI no disponible. Ejecutando en modo consola...\n", e)
        path = DEFAULT_EXCEL
        print(f"Leyendo {path} ...")
        df_real = read_real_usage(path)
        est = []
        for app in df_real["App"]:
            v = input(f"Estima minutos/sem en {app}: ")
            try:
                est.append(float(v))
            except:
                est.append(0.0)
        df = pd.DataFrame({"App": df_real["App"], "EstMinutes": est})
        df = df.merge(df_real, on="App", how="left")
        if "IsProductivity" not in df.columns:
            df["IsProductivity"] = False
        budget = float(input("Presupuesto de bloqueo (min/sem): ") or "300")
        avoid_prod = True
        rec = greedy_fractional_block(df, budget, avoid_block_productivity=avoid_prod)
        rec.to_csv("analysis_report.csv", index=False)
        print("Reporte guardado en analysis_report.csv")

if __name__ == "__main__":
    main()
