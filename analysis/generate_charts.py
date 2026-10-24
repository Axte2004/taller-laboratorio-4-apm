import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/workspace/resultados")
with (ROOT / "mediciones.csv").open(newline="", encoding="utf-8-sig") as handle:
    rows = list(csv.DictReader(handle))
if len(rows) < 6:
    raise SystemExit("mediciones.csv debe contener los seis escalones medidos")

users = [int(row["usuarios"]) for row in rows]
series = [
    ("peticiones_por_segundo", "Peticiones por segundo", "Peticiones/s", "usuarios_vs_rps.png"),
    ("p95_ms", "Latencia p95", "Milisegundos", "usuarios_vs_p95.png"),
    ("error_porcentaje", "Tasa de error", "Porcentaje", "usuarios_vs_error.png"),
]
for key, title, ylabel, filename in series:
    values = [float(row[key]) for row in rows]
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.plot(users, values, marker="o", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Usuarios virtuales concurrentes")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.savefig(ROOT / filename, dpi=160)
    plt.close(fig)
print("Gráficas generadas en /workspace/resultados")
