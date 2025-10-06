
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import os

APP_DEFAULTS = ["Instagram","TikTok","YouTube","WhatsApp","Games","Other","Study","Reading","Exercise"]
CHART_OUTPUT = "comparison_estimated_vs_real.png"

COL_NAME_MIN = 160
COL_EST_MIN = 140
COL_VAL_MIN = 120
GAP_PX = 28  

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Productivity Planner — Phase 2")
        self.geometry("960x600")
        self.minsize(920, 560)
        self.configure(bg="#0f172a")

        self.excel_path = None
        self.goal_minutes = tk.IntVar(value=60)

        self.build_ui()

    def build_ui(self):
        header = tk.Frame(self, bg="#0f172a")
        header.pack(fill="x", padx=16, pady=(16,8))
        tk.Label(header, text="Fase 2 — Análisis y Recomendación",
                 font=("Segoe UI", 18, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w")
        tk.Label(header, text="Ingresa tus estimaciones y valor (1-10). Luego carga el Excel con uso real por día.",
                 font=("Segoe UI", 10), fg="#94a3b8", bg="#0f172a").pack(anchor="w", pady=(4,0))

        main = tk.Frame(self, bg="#0f172a")
        main.pack(fill="both", expand=True, padx=16, pady=8)

        left = tk.Frame(main, bg="#0f172a")
        left.pack(side="left", fill="both", expand=True)

        card = tk.Frame(left, bg="#111827", bd=0, highlightbackground="#1f2937", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=(0,8), pady=0)

        
        canvas = tk.Canvas(card, bg="#111827", highlightthickness=0)
        vsb = tk.Scrollbar(card, orient="vertical", command=canvas.yview)
        self.rows_frame = tk.Frame(canvas, bg="#111827")
        self.rows_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=12, pady=(12,12))
        vsb.pack(side="right", fill="y", padx=(0,12), pady=(12,12))

       
        for c, minsize in enumerate([COL_NAME_MIN, COL_EST_MIN, COL_VAL_MIN]):
            self.rows_frame.grid_columnconfigure(c, weight=0, minsize=minsize)
        self.rows_frame.grid_columnconfigure(0, weight=1)  

        
        tk.Label(self.rows_frame, text="Aplicación", fg="#e5e7eb", bg="#111827",
                 font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(self.rows_frame, text="Min/día (estimado)", fg="#e5e7eb", bg="#111827",
                 font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=(8,0))
        tk.Label(self.rows_frame, text="Valor (1-10)", fg="#e5e7eb", bg="#111827",
                 font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=2, sticky="w", padx=(GAP_PX,0))

     
        self.row_vars = []
        for r, app in enumerate(APP_DEFAULTS, start=1): 
            tk.Label(self.rows_frame, text=app, fg="#f1f5f9", bg="#111827", anchor="w",
                     font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w", pady=4)

            est = tk.Spinbox(self.rows_frame, from_=0, to=1440, increment=5, width=10, justify="right")
            est.delete(0, "end"); est.insert(0, "0")
            est.grid(row=r, column=1, sticky="w", pady=4, padx=(8,0))

            val = tk.Spinbox(self.rows_frame, from_=1, to=10, increment=1, width=6, justify="right")
            val.delete(0, "end"); val.insert(0, "5")
            val.grid(row=r, column=2, sticky="w", pady=4, padx=(GAP_PX,0))

            self.row_vars.append((app, est, val))

       
        right = tk.Frame(main, bg="#0f172a")
        right.pack(side="right", fill="y")

        action_card = tk.Frame(right, bg="#111827", bd=0, highlightbackground="#1f2937", highlightthickness=1)
        action_card.pack(fill="x", padx=(8,0), pady=(0,8))

        tk.Label(action_card, text="Acciones", font=("Segoe UI", 12, "bold"),
                 fg="#e2e8f0", bg="#111827").pack(anchor="w", padx=12, pady=(12,4))

        goal_fr = tk.Frame(action_card, bg="#111827")
        goal_fr.pack(fill="x", padx=12, pady=4)
        tk.Label(goal_fr, text="Objetivo: recuperar min/día", fg="#cbd5e1", bg="#111827",
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(goal_fr, textvariable=self.goal_minutes, width=6, justify="right").pack(side="left", padx=8)

        def primary_btn(parent, text, cmd):
            b = tk.Button(parent, text=text, command=cmd, fg="#0b1220", bg="#93c5fd",
                          activebackground="#60a5fa", relief="flat", padx=12, pady=6, font=("Segoe UI", 10, "bold"))
            b.pack(fill="x", padx=12, pady=6)
            return b

        def secondary_btn(parent, text, cmd):
            b = tk.Button(parent, text=text, command=cmd, fg="#0b1220", bg="#86efac",
                          activebackground="#4ade80", relief="flat", padx=12, pady=6, font=("Segoe UI", 10, "bold"))
            b.pack(fill="x", padx=12, pady=6)
            return b

        primary_btn(action_card, "1) Cargar Excel (uso real)", self.load_excel)
        primary_btn(action_card, "2) Ejecutar análisis", self.run_analysis)
        secondary_btn(action_card, "Abrir carpeta de salida", self.open_outdir)

        self.status = tk.Label(action_card, text="Sin archivo cargado.", fg="#94a3b8", bg="#111827",
                               font=("Segoe UI", 9), justify="left", wraplength=280)
        self.status.pack(fill="x", padx=12, pady=(6,12))

        footer = tk.Frame(self, bg="#0f172a")
        footer.pack(fill="x", padx=16, pady=(4,12))
        tk.Label(footer, text="Reglas: no se bloquean apps con valor > 8 · Tope de corte 45% · Greedy por ratio valor/hora",
                 font=("Segoe UI", 9), fg="#64748b", bg="#0f172a").pack(anchor="w")

    def load_excel(self):
        path = filedialog.askopenfilename(
            title="Selecciona el Excel con USO REAL (hoja 'usage': date, app, minutes)",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if path:
            self.excel_path = path
            self.status.config(text=f"Archivo cargado:\n{path}")

    def gather_inputs(self):
        est = {}
        val = {}
        for app, est_w, val_w in self.row_vars:
            try:
                est[app] = int(est_w.get())
            except:
                est[app] = 0
            try:
                vv = int(val_w.get())
                vv = max(1, min(10, vv))
                val[app] = vv
            except:
                val[app] = 5
        return est, val

    def run_analysis(self):
        if not self.excel_path:
            messagebox.showerror("Falta archivo", "Primero carga el Excel con uso real.")
            return
        try:
            df = self.read_usage(self.excel_path)
        except Exception as e:
            messagebox.showerror("Error al leer Excel", str(e))
            return

        est, values = self.gather_inputs()
        weekly = self.aggregate_weekly(df)

        comp, chart_path = self.compare_and_plot(weekly, est)
        ratio_df = self.build_ratio_table(weekly, values)

        goal = max(0, int(self.goal_minutes.get()))
        cuts, adds, rem = self.greedy_reallocation(ratio_df, goal)

        out_dir = os.path.dirname(self.excel_path)
        ratio_csv = os.path.join(out_dir, "phase2_ratio_table.csv")
        comp_csv = os.path.join(out_dir, "phase2_comparison.csv")
        ratio_df.to_csv(ratio_csv, index=False)
        comp.to_csv(comp_csv, index=False)

        lines = []
        if cuts:
            lines.append("Bloqueos sugeridos (min/día):")
            for app, m in cuts:
                lines.append(f"• {app}: {m}")
        else:
            lines.append("No se sugieren bloqueos (o todas las apps con sobreuso tienen valor > 8).")

        if adds:
            lines.append("\nReasignaciones sugeridas (min/día):")
            for app, m in adds:
                lines.append(f"• {app}: +{m}")

        if rem > 0:
            lines.append(f"\nFaltan {int(rem)} min/día para el objetivo. Considera aumentar cortes o el objetivo.")

        lines.append(f"\nGráfica comparativa: {os.path.abspath(chart_path)}")
        lines.append(f"Tablas guardadas:\n- {comp_csv}\n- {ratio_csv}")
        messagebox.showinfo("Resultados", "\n".join(lines))

    @staticmethod
    def read_usage(path):
        try:
            df = pd.read_excel(path, sheet_name="usage")
        except Exception:
            df = pd.read_excel(path)
        cols = {c.lower(): c for c in df.columns}
        for c in ["date","app","minutes"]:
            if c not in cols:
                raise ValueError(f"Falta columna '{c}'. Columnas: {list(df.columns)}")
        df = df.rename(columns={cols["date"]:"date", cols["app"]:"app", cols["minutes"]:"minutes"})
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["app"] = df["app"].astype(str)
        df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
        return df

    @staticmethod
    def aggregate_weekly(df):
        return df.groupby("app", as_index=False)["minutes"].sum()

    @staticmethod
    def compare_and_plot(weekly_usage, daily_estimates):
        all_apps = sorted(set(weekly_usage["app"]).union(daily_estimates.keys()))
        actual_week = {row["app"]: int(row["minutes"]) for _, row in weekly_usage.iterrows()}
        est_week = {app: int(daily_estimates.get(app, 0)) * 7 for app in all_apps}

        rows = []
        for app in all_apps:
            a = actual_week.get(app, 0)
            e = est_week.get(app, 0)
            rows.append({"app": app, "actual_week_min": a, "estimated_week_min": e, "diff_week": a - e})
        comp = pd.DataFrame(rows).sort_values(by="actual_week_min", ascending=False)

        apps = comp["app"].tolist()
        actual_vals = comp["actual_week_min"].tolist()
        est_vals = comp["estimated_week_min"].tolist()

        plt.figure()
        x = range(len(apps))
        width = 0.4
        plt.bar([i - width/2 for i in x], actual_vals, width=width, label="Uso real (semana)")
        plt.bar([i + width/2 for i in x], est_vals, width=width, label="Estimado (semana)")
        plt.xticks(list(x), apps, rotation=30, ha="right")
        plt.ylabel("Minutos en la semana")
        plt.title("Comparación: Uso real vs Estimado (por app)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(CHART_OUTPUT)
        plt.close()

        return comp, CHART_OUTPUT

    @staticmethod
    def build_ratio_table(weekly, values):
        m_per_day = weekly.set_index("app")["minutes"].to_dict()
        data = []
        apps = sorted(set(list(m_per_day.keys()) + list(values.keys())))
        for app in apps:
            week_m = int(m_per_day.get(app, 0))
            day_m = week_m / 7.0
            hours = day_m / 60.0 if day_m > 0 else 0.0
            val = int(values.get(app, 1))
            ratio = (val / hours) if hours > 0 else float('inf') if val>0 else 0.0
            data.append({"app":app, "value":val, "day_minutes":day_m, "ratio_value_per_hour":ratio})
        df = pd.DataFrame(data).sort_values(by=["ratio_value_per_hour","value"], ascending=[False, False])
        return df

    @staticmethod
    def greedy_reallocation(df_ratio, goal_recover_minutes_per_day):
        remaining = float(goal_recover_minutes_per_day)
        cuts = []
        adds = []

        inc_order = df_ratio.sort_values(by="ratio_value_per_hour", ascending=False).reset_index(drop=True)
        dec_order = df_ratio.sort_values(by="ratio_value_per_hour", ascending=True).reset_index(drop=True)

        
        for i in range(len(dec_order)):
            if remaining <= 0: break
            app = dec_order.loc[i, "app"]
            val = int(dec_order.loc[i, "value"])
            if val > 8:
                continue
            current = float(dec_order.loc[i, "day_minutes"])
            if current <= 0: continue
            cap = max(0.0, 0.45*current)  
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
            if val < 6:
                continue
            base = float(inc_order.loc[i, "day_minutes"])
            cap = max(15.0, 0.3*max(30.0, base))
            give = min(cap, remaining_add)
            give = int(5 * round(give / 5.0))
            if give <= 0: continue
            adds.append((app, give))
            remaining_add -= give

        return cuts, adds, remaining

    def open_outdir(self):
        if not self.excel_path:
            messagebox.showinfo("Carpeta", "Primero carga un archivo para conocer la carpeta de salida.")
            return
        out_dir = os.path.dirname(self.excel_path)
        try:
            if os.name == "nt":
                os.startfile(out_dir)
            elif os.name == "posix":
                import subprocess
                subprocess.Popen(["xdg-open", out_dir])
        except Exception as e:
            messagebox.showerror("No se pudo abrir", str(e))

if __name__ == "__main__":
    App().mainloop()
