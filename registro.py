"""Registro horario de entradas y salidas, en tiempo real.

Cada vez que se ejecuta iniciar.bat se crea una sesion nueva en
registros/sesion_AAAAMMDD_HHMMSS/ con:

  eventos.csv   -> cada "Entrada detectada" / "Salida detectada" del Arduino,
                   con su hora exacta y el tramo horario al que pertenece
                   (no depende del contador).
  cortes.csv    -> punto 0 al iniciar y un corte cada hora con la cantidad de
                   entradas y salidas de ese intervalo.
  reporte.html  -> reporte, se reescribe solo en cada entrada/salida y en
                   cada corte (no hace falta generarlo a mano).

El reporte en vivo esta en http://localhost:5000/reporte: la fila de la hora
en curso se actualiza con cada evento y al cumplirse la hora queda cerrada y
empieza una fila nueva.
"""
import csv
import json
import os
import sys
import threading
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registros")
PLANTILLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "reporte.html")
FMT = "%Y-%m-%d %H:%M:%S"
INTERVALO = timedelta(minutes=float(os.environ.get("REGISTRO_INTERVALO_MIN", "60")))

ENTRADA = "entrada"
SALIDA = "salida"
CORTES_HEADER = ["punto", "hora", "entradas_intervalo", "salidas_intervalo",
                 "entradas_acumuladas", "salidas_acumuladas", "neto"]


class Registro:
    def __init__(self, on_change=None):
        """on_change(estado) se llama en cada entrada, salida y corte."""
        self.on_change = on_change
        self.inicio = datetime.now().replace(microsecond=0)
        self.dir = os.path.join(BASE_DIR, "sesion_" + self.inicio.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(self.dir, exist_ok=True)
        self.eventos_path = os.path.join(self.dir, "eventos.csv")
        self.cortes_path = os.path.join(self.dir, "cortes.csv")

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.punto = 0
        self.proximo_corte = self.inicio + INTERVALO
        self.ent_intervalo = self.sal_intervalo = 0
        self.ent_total = self.sal_total = 0

        with open(self.eventos_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["hora", "tipo", "tramo"])
        with open(self.cortes_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CORTES_HEADER)
            w.writerow([0, self.inicio.strftime(FMT), 0, 0, 0, 0, 0])
        self._actualizar()
        print(f"Registro iniciado (punto 0: {self.inicio.strftime(FMT)}) en {self.dir}")

    def estado(self):
        return estado(self.dir, self.proximo_corte if not self._stop.is_set() else None)

    def _actualizar(self):
        est = self.estado()
        escribir_reporte(self.dir, est)
        if self.on_change:
            self.on_change(est)

    def registrar(self, tipo: str):
        with self._lock:
            if tipo == ENTRADA:
                self.ent_intervalo += 1
                self.ent_total += 1
            else:
                self.sal_intervalo += 1
                self.sal_total += 1
            with open(self.eventos_path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([datetime.now().strftime(FMT), tipo, self.punto + 1])
        self._actualizar()

    def corte(self):
        """Cierra el tramo actual, lo escribe en cortes.csv y abre el siguiente."""
        with self._lock:
            self.punto += 1
            fila = [self.punto, datetime.now().strftime(FMT),
                    self.ent_intervalo, self.sal_intervalo,
                    self.ent_total, self.sal_total, self.ent_total - self.sal_total]
            self.ent_intervalo = self.sal_intervalo = 0
            with open(self.cortes_path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(fila)
        print(f"Corte #{fila[0]}: +{fila[2]} entradas / -{fila[3]} salidas")
        self._actualizar()

    def iniciar_cortes_horarios(self):
        def loop():
            while not self._stop.wait(max(0, (self.proximo_corte - datetime.now()).total_seconds())):
                self.proximo_corte += INTERVALO
                self.corte()
        threading.Thread(target=loop, daemon=True).start()

    def finalizar(self) -> str:
        """Corte final (tramo parcial) y reporte definitivo."""
        self._stop.set()
        self.corte()
        return os.path.join(self.dir, "reporte.html")


def estado(sesion_dir, proximo_corte=None):
    """Arma el estado del reporte a partir de los archivos de la sesion:
    los tramos cerrados (cortes.csv) + el tramo en curso (eventos sin corte)."""
    with open(os.path.join(sesion_dir, "cortes.csv"), newline="", encoding="utf-8") as f:
        cortes = list(csv.DictReader(f))
    with open(os.path.join(sesion_dir, "eventos.csv"), newline="", encoding="utf-8") as f:
        eventos = list(csv.DictReader(f))

    filas = []
    desde = cortes[0]["hora"]
    for c in cortes[1:]:
        filas.append({"punto": int(c["punto"]), "desde": desde, "hasta": c["hora"],
                      "entradas": int(c["entradas_intervalo"]), "salidas": int(c["salidas_intervalo"]),
                      "en_curso": False})
        desde = c["hora"]

    ultimo_punto = int(cortes[-1]["punto"])
    pendientes = [ev for ev in eventos if int(ev["tramo"]) > ultimo_punto]
    if proximo_corte is not None or pendientes:
        e = sum(ev["tipo"] == ENTRADA for ev in pendientes)
        filas.append({"punto": ultimo_punto + 1, "desde": desde,
                      "hasta": proximo_corte.strftime(FMT) if proximo_corte else pendientes[-1]["hora"],
                      "entradas": e, "salidas": len(pendientes) - e,
                      "en_curso": proximo_corte is not None})

    ent = sal = 0
    for f in filas:
        ent += f["entradas"]
        sal += f["salidas"]
        f.update(entradas_acum=ent, salidas_acum=sal, neto=ent - sal)

    return {"inicio": cortes[0]["hora"], "actualizado": datetime.now().strftime(FMT),
            "en_vivo": proximo_corte is not None, "filas": filas,
            "entradas": ent, "salidas": sal, "neto": ent - sal}


def escribir_reporte(sesion_dir, est) -> str:
    """Guarda reporte.html (misma plantilla que la vista en vivo, con los datos embebidos)."""
    with open(PLANTILLA, encoding="utf-8") as f:
        contenido = f.read().replace("{{ estado_json | safe }}", json.dumps(est).replace("</", "<\\/"))
    ruta = os.path.join(sesion_dir, "reporte.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return ruta


if __name__ == "__main__":
    # Regenera el reporte de una sesion vieja: python registro.py [carpeta_de_sesion]
    if len(sys.argv) > 1:
        sesion = sys.argv[1]
    else:
        sesion = os.path.join(BASE_DIR, sorted(d for d in os.listdir(BASE_DIR) if d.startswith("sesion_"))[-1])
    print(f"Reporte generado: {escribir_reporte(sesion, estado(sesion))}")
