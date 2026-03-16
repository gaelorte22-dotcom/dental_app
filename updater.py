"""
updater.py
Sistema de actualizaciones automáticas.
Revisa GitHub Releases al abrir la app y pregunta si descargar.
"""

import os
import sys
import json
import threading
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ── Configuración ─────────────────────────────────────────────────────────────
GITHUB_USER = "gaelorte22-dotcom"
GITHUB_REPO = "dental_app"
VERSION_ACTUAL = "1.0.0"

API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

PRIMARY  = "#1A6B8A"
SECONDARY= "#2196B0"
SUCCESS  = "#27AE60"
BG       = "#F5F8FA"
TEXT     = "#2C3E50"
MUTED    = "#7F8C8D"
BORDER   = "#DEE4E8"


def _btn(label, color, hover, text_color="white", w=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w: b.setFixedWidth(w)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{color}; color:{text_color};
            border:none; border-radius:8px;
            padding:8px 18px; font-size:13px; font-weight:600;
        }}
        QPushButton:hover {{ background:{hover}; }}
    """)
    return b


def _version_mayor(v1: str, v2: str) -> bool:
    """Retorna True si v1 > v2"""
    try:
        t1 = tuple(int(x) for x in v1.lstrip("v").split("."))
        t2 = tuple(int(x) for x in v2.lstrip("v").split("."))
        return t1 > t2
    except Exception:
        return False


# ── Worker thread para revisar actualizaciones ────────────────────────────────
class UpdateChecker:
    def __init__(self):
        self._callbacks = {"update": [], "sin_update": [], "error": []}

    def on_update(self, fn):   self._callbacks["update"].append(fn)
    def on_sin_update(self, fn): self._callbacks["sin_update"].append(fn)
    def on_error(self, fn):    self._callbacks["error"].append(fn)

    def _emit(self, key, *args):
        from PyQt6.QtCore import QTimer
        for fn in self._callbacks[key]:
            QTimer.singleShot(0, lambda f=fn, a=args: f(*a))

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        try:
            req = urllib.request.Request(
                API_URL,
                headers={"User-Agent": "DentalApp-Updater"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())

            version_nueva = data.get("tag_name", "").lstrip("v")
            if _version_mayor(version_nueva, VERSION_ACTUAL):
                assets = data.get("assets", [])
                asset_url = None; asset_name = None

                if sys.platform == "win32":
                    for a in assets:
                        if a["name"].endswith(".exe"):
                            asset_url = a["browser_download_url"]
                            asset_name = a["name"]; break
                elif sys.platform == "darwin":
                    for a in assets:
                        if "Mac" in a["name"] and a["name"].endswith(".zip"):
                            asset_url = a["browser_download_url"]
                            asset_name = a["name"]; break

                self._emit("update", {
                    "version":    version_nueva,
                    "notas":      data.get("body", ""),
                    "asset_url":  asset_url,
                    "asset_name": asset_name,
                    "fecha":      data.get("published_at", "")[:10],
                })
            else:
                self._emit("sin_update")

        except urllib.error.URLError:
            self._emit("error", "Sin conexión a internet")
        except Exception as e:
            self._emit("error", str(e))


# ── Worker thread para descargar ──────────────────────────────────────────────
class Downloader:
    def __init__(self, url: str, nombre: str):
        self.url    = url
        self.nombre = nombre
        self._callbacks = {"progreso": [], "completado": [], "error": []}

    def on_progreso(self, fn):   self._callbacks["progreso"].append(fn)
    def on_completado(self, fn): self._callbacks["completado"].append(fn)
    def on_error(self, fn):      self._callbacks["error"].append(fn)

    def _emit(self, key, *args):
        from PyQt6.QtCore import QTimer
        for fn in self._callbacks[key]:
            QTimer.singleShot(0, lambda f=fn, a=args: f(*a))

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        try:
            dest = os.path.join(os.path.expanduser("~"), "Downloads", self.nombre)
            req  = urllib.request.Request(
                self.url,
                headers={"User-Agent": "DentalApp-Updater"}
            )
            with urllib.request.urlopen(req) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                descargado = 0
                with open(dest, "wb") as f:
                    while True:
                        data = resp.read(8192)
                        if not data: break
                        f.write(data)
                        descargado += len(data)
                        if total:
                            self._emit("progreso", int(descargado * 100 / total))

            self._emit("progreso", 100)
            self._emit("completado", dest)

        except Exception as e:
            self._emit("error", str(e))


# ── Dialog de actualización ───────────────────────────────────────────────────
class UpdateDialog(QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("Actualización Disponible")
        self.setFixedWidth(460)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._downloader = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background:{PRIMARY};")
        hl = QVBoxLayout(hdr); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("🎉  Nueva Versión Disponible")
        t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t.setStyleSheet("color:white;"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        layout.addWidget(hdr)

        body = QWidget()
        bl = QVBoxLayout(body); bl.setContentsMargins(28,20,28,20); bl.setSpacing(12)

        # Versión
        ver_row = QHBoxLayout()
        ver_row.addWidget(self._info_card("Versión actual", f"v{VERSION_ACTUAL}", MUTED))
        ver_row.addWidget(QLabel("→"))
        ver_row.addWidget(self._info_card("Nueva versión", f"v{self.info['version']}", SUCCESS))
        bl.addLayout(ver_row)

        # Notas
        if self.info.get("notas"):
            notas_lbl = QLabel("Novedades:")
            notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            bl.addWidget(notas_lbl)

            notas = QLabel(self.info["notas"][:300])
            notas.setWordWrap(True)
            notas.setStyleSheet(f"""
                background:white; border-radius:8px; border:1px solid {BORDER};
                padding:10px; color:{TEXT}; font-size:12px;
            """)
            bl.addWidget(notas)

        # Barra de progreso (oculta inicialmente)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border:none; border-radius:5px;
                background:{BORDER};
            }}
            QProgressBar::chunk {{
                background:{PRIMARY}; border-radius:5px;
            }}
        """)
        self.progress.setVisible(False)
        bl.addWidget(self.progress)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(self.status_lbl)

        # Botones
        btn_row = QHBoxLayout(); btn_row.addStretch()
        self.skip_btn = _btn("Ahora no", "#ECF0F1", "#D5DBDB", TEXT)
        self.skip_btn.clicked.connect(self.reject)
        self.dl_btn = _btn("⬇️  Descargar Actualización", PRIMARY, SECONDARY)
        self.dl_btn.clicked.connect(self._descargar)
        btn_row.addWidget(self.skip_btn); btn_row.addWidget(self.dl_btn)
        bl.addLayout(btn_row)

        layout.addWidget(body)

    def _info_card(self, titulo, valor, color):
        card = QWidget()
        card.setStyleSheet(f"background:white; border-radius:8px; border:1px solid {BORDER};")
        cl = QVBoxLayout(card); cl.setContentsMargins(12,8,12,8); cl.setSpacing(2)
        t = QLabel(titulo); t.setStyleSheet(f"color:{MUTED}; font-size:11px; border:none; background:transparent;")
        v = QLabel(valor);  v.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        v.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        cl.addWidget(t); cl.addWidget(v)
        return card

    def _descargar(self):
        if not self.info.get("asset_url"):
            import webbrowser
            webbrowser.open(f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest")
            self.accept()
            return

        self.dl_btn.setEnabled(False)
        self.dl_btn.setText("Descargando…")
        self.skip_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_lbl.setText("Iniciando descarga…")

        self._downloader = Downloader(self.info["asset_url"], self.info["asset_name"])
        self._downloader.on_progreso(self._on_progreso)
        self._downloader.on_completado(self._on_completado)
        self._downloader.on_error(self._on_error)
        self._downloader.start()

    def _on_progreso(self, val):
        self.progress.setValue(val)
        self.status_lbl.setText(f"Descargando… {val}%")

    def _on_completado(self, ruta):
        self.status_lbl.setText(f"✅ Descargado en: {ruta}")
        self.dl_btn.setText("✅  Descargado")

        if sys.platform == "win32":
            # En Windows — ejecutar el instalador directamente
            self.status_lbl.setText("Abriendo instalador…")
            QTimer.singleShot(1000, lambda: self._instalar(ruta))
        elif sys.platform == "darwin":
            # En Mac — abrir la carpeta de descargas
            subprocess.Popen(["open", os.path.dirname(ruta)])
            self.status_lbl.setText("Abre el .zip en tu carpeta Descargas")
            self.skip_btn.setEnabled(True)
            self.skip_btn.setText("Cerrar")

    def _instalar(self, ruta):
        """Ejecuta el nuevo instalador y cierra la app actual."""
        try:
            subprocess.Popen([ruta])
            sys.exit(0)
        except Exception as e:
            self._on_error(str(e))

    def _on_error(self, msg):
        self.status_lbl.setText(f"❌ Error: {msg}")
        self.dl_btn.setEnabled(True)
        self.dl_btn.setText("⬇️  Reintentar")
        self.skip_btn.setEnabled(True)


# ── Función principal — llamar al arrancar la app ─────────────────────────────
def verificar_actualizacion(parent=None, silencioso=True):
    """
    Revisa si hay actualización disponible.
    silencioso=True → solo muestra dialog si hay actualización (al arrancar)
    silencioso=False → muestra resultado siempre (botón manual)
    """
    checker = UpdateChecker()

    def on_update(info):
        dlg = UpdateDialog(info, parent)
        dlg.exec()

    def on_sin_update():
        if not silencioso:
            from PyQt6.QtWidgets import QMessageBox
            m = QMessageBox(parent)
            m.setWindowTitle("Sin actualizaciones")
            m.setText("✅ Ya tienes la versión más reciente.")
            m.setStyleSheet("color:black; background:white;")
            m.exec()

    def on_error(msg):
        if not silencioso:
            from PyQt6.QtWidgets import QMessageBox
            m = QMessageBox(parent)
            m.setWindowTitle("Sin conexión")
            m.setText(f"No se pudo verificar actualizaciones:\n{msg}")
            m.setStyleSheet("color:black; background:white;")
            m.exec()

    checker.on_update(on_update)
    checker.on_sin_update(on_sin_update)
    checker.on_error(on_error)
    checker.start()

    return checker
