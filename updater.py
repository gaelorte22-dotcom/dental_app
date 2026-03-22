# Sistema de actualizaciones automaticas via GitHub Releases.
# Revisa al abrir la app y descarga/instala si hay version nueva.

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
    QPushButton, QProgressBar, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal as _Signal
from PyQt6.QtGui import QFont

GITHUB_USER   = "gaelorte22-dotcom"
GITHUB_REPO   = "dental_app"
VERSION_ACTUAL = "1.3.0"

API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

PRIMARY   = "#1A6B8A"
SECONDARY = "#2196B0"
BG        = "#F5F8FA"
TEXT      = "#2C3E50"
MUTED     = "#7F8C8D"
BORDER    = "#DEE4E8"


def _btn(label, color, hover, text_color="white", w=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w:
        b.setFixedWidth(w)
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
    try:
        def normalizar(v):
            partes = v.lstrip("v").split(".")
            # Rellenar con ceros para comparar versiones de diferente longitud
            while len(partes) < 4:
                partes.append("0")
            return tuple(int(x) for x in partes[:4])
        return normalizar(v1) > normalizar(v2)
    except Exception:
        return False


def _carpeta_downloads() -> str:
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(path, exist_ok=True)
    return path


# Bridge para pasar senales desde hilos secundarios al hilo principal de Qt
class _CheckerBridge(QObject):
    update_signal     = _Signal(dict)
    sin_update_signal = _Signal()
    error_signal      = _Signal(str)


class _DownloaderBridge(QObject):
    progreso_signal   = _Signal(int)
    completado_signal = _Signal(str)
    error_signal      = _Signal(str)


class UpdateChecker:
    def __init__(self):
        self._bridge = _CheckerBridge()
        self._cb_update     = []
        self._cb_sin_update = []
        self._cb_error      = []
        self._bridge.update_signal.connect(lambda d: [fn(d) for fn in self._cb_update])
        self._bridge.sin_update_signal.connect(lambda: [fn() for fn in self._cb_sin_update])
        self._bridge.error_signal.connect(lambda m: [fn(m) for fn in self._cb_error])

    def on_update(self, fn):     self._cb_update.append(fn)
    def on_sin_update(self, fn): self._cb_sin_update.append(fn)
    def on_error(self, fn):      self._cb_error.append(fn)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            req = urllib.request.Request(
                API_URL,
                headers={"User-Agent": "DentalApp-Updater"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            version_nueva = data.get("tag_name", "").lstrip("v")
            if not _version_mayor(version_nueva, VERSION_ACTUAL):
                self._bridge.sin_update_signal.emit()
                return

            assets     = data.get("assets", [])
            asset_url  = None
            asset_name = None

            if sys.platform == "win32":
                # Buscar primero el instalador Setup
                for a in assets:
                    if "Setup" in a["name"] and a["name"].endswith(".exe"):
                        asset_url  = a["browser_download_url"]
                        asset_name = a["name"]
                        break
                # Si no hay Setup, usar cualquier .exe
                if not asset_url:
                    for a in assets:
                        if a["name"].endswith(".exe"):
                            asset_url  = a["browser_download_url"]
                            asset_name = a["name"]
                            break
            elif sys.platform == "darwin":
                for a in assets:
                    if "Mac" in a["name"] and a["name"].endswith(".zip"):
                        asset_url  = a["browser_download_url"]
                        asset_name = a["name"]
                        break

            self._bridge.update_signal.emit({
                "version":    version_nueva,
                "notas":      data.get("body", ""),
                "asset_url":  asset_url,
                "asset_name": asset_name,
                "fecha":      data.get("published_at", "")[:10],
            })

        except urllib.error.URLError:
            self._bridge.error_signal.emit("Sin conexion a internet")
        except Exception as e:
            self._bridge.error_signal.emit(str(e))


class Downloader:
    def __init__(self, url: str, nombre: str):
        self.url    = url
        self.nombre = nombre or "DentalApp_update"
        self._bridge = _DownloaderBridge()
        self._cb_progreso   = []
        self._cb_completado = []
        self._cb_error      = []
        self._bridge.progreso_signal.connect(lambda v: [fn(v) for fn in self._cb_progreso])
        self._bridge.completado_signal.connect(lambda v: [fn(v) for fn in self._cb_completado])
        self._bridge.error_signal.connect(lambda v: [fn(v) for fn in self._cb_error])

    def on_progreso(self, fn):   self._cb_progreso.append(fn)
    def on_completado(self, fn): self._cb_completado.append(fn)
    def on_error(self, fn):      self._cb_error.append(fn)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            # Agregar timestamp al nombre para evitar conflictos de permisos
            base, ext = os.path.splitext(self.nombre)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(_carpeta_downloads(), f"{base}_{ts}{ext}")

            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "DentalApp-Updater"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total      = int(resp.headers.get("Content-Length", 0))
                descargado = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        descargado += len(chunk)
                        if total:
                            self._bridge.progreso_signal.emit(int(descargado * 100 / total))

            self._bridge.progreso_signal.emit(100)
            self._bridge.completado_signal.emit(dest)

        except Exception as e:
            self._bridge.error_signal.emit(str(e))


class UpdateDialog(QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("Actualizacion disponible")
        self.setFixedWidth(460)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._downloader = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background:{PRIMARY};")
        hl = QVBoxLayout(hdr)
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("Nueva version disponible")
        t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t.setStyleSheet("color:white;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        layout.addWidget(hdr)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 20, 28, 20)
        bl.setSpacing(12)

        ver_row = QHBoxLayout()
        ver_row.addWidget(self._info_card("Version actual", f"v{VERSION_ACTUAL}", MUTED))
        ver_row.addWidget(QLabel("->"))
        ver_row.addWidget(self._info_card("Version nueva", f"v{self.info['version']}", "#27AE60"))
        bl.addLayout(ver_row)

        if self.info.get("notas"):
            notas_lbl = QLabel("Novedades:")
            notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            bl.addWidget(notas_lbl)
            notas = QLabel(self.info["notas"][:400])
            notas.setWordWrap(True)
            notas.setStyleSheet(f"""
                background:white; border-radius:8px; border:1px solid {BORDER};
                padding:10px; color:{TEXT}; font-size:12px;
            """)
            bl.addWidget(notas)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border:none; border-radius:5px; background:{BORDER}; }}
            QProgressBar::chunk {{ background:{PRIMARY}; border-radius:5px; }}
        """)
        self.progress.setVisible(False)
        bl.addWidget(self.progress)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        bl.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.skip_btn = _btn("Ahora no", "#ECF0F1", "#D5DBDB", TEXT)
        self.skip_btn.clicked.connect(self.reject)
        self.dl_btn = _btn("Descargar actualizacion", PRIMARY, SECONDARY)
        self.dl_btn.clicked.connect(self._descargar)
        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.dl_btn)
        bl.addLayout(btn_row)

        layout.addWidget(body)

    def _info_card(self, titulo, valor, color):
        card = QWidget()
        card.setStyleSheet(f"background:white; border-radius:8px; border:1px solid {BORDER};")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 8, 12, 8)
        cl.setSpacing(2)
        t = QLabel(titulo)
        t.setStyleSheet(f"color:{MUTED}; font-size:11px; border:none; background:transparent;")
        v = QLabel(valor)
        v.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        v.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        cl.addWidget(t)
        cl.addWidget(v)
        return card

    def _descargar(self):
        if not self.info.get("asset_url"):
            import webbrowser
            webbrowser.open(f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest")
            self.accept()
            return

        self.dl_btn.setEnabled(False)
        self.dl_btn.setText("Descargando...")
        self.skip_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_lbl.setText("Iniciando descarga...")

        self._downloader = Downloader(self.info["asset_url"], self.info["asset_name"])
        self._downloader.on_progreso(self._on_progreso)
        self._downloader.on_completado(self._on_completado)
        self._downloader.on_error(self._on_error)
        self._downloader.start()

    def _on_progreso(self, val):
        self.progress.setValue(val)
        self.status_lbl.setText(f"Descargando... {val}%")

    def _on_completado(self, ruta):
        self.dl_btn.setText("Descargado")

        if sys.platform == "win32":
            self.status_lbl.setText("Descarga completa. Abriendo instalador...")
            QTimer.singleShot(1000, lambda: self._instalar_windows(ruta))

        elif sys.platform == "darwin":
            self._instalar_mac(ruta)

        else:
            self.status_lbl.setText(f"Descargado en: {ruta}")
            self.skip_btn.setEnabled(True)
            self.skip_btn.setText("Cerrar")

    def _instalar_windows(self, ruta):
        try:
            os.startfile(ruta)
            QTimer.singleShot(800, lambda: sys.exit(0))
        except Exception as e:
            self._on_error(str(e))

    def _instalar_mac(self, ruta):
        import zipfile, shutil, stat, tempfile

        try:
            # Descomprimir
            extract_dir = os.path.join(_carpeta_downloads(), "DentalApp_update")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(ruta, "r") as z:
                z.extractall(extract_dir)

            # Buscar el ejecutable dentro del zip
            app_origen = None
            for item in os.listdir(extract_dir):
                if item.endswith(".app") or item == "DentalApp":
                    app_origen = os.path.join(extract_dir, item)
                    break

            if not app_origen:
                raise FileNotFoundError("No se encontro DentalApp en el zip")

            # Detectar ruta actual del ejecutable instalado
            ejecutable = sys.executable
            if ".app" in ejecutable:
                app_destino = ejecutable.split(".app")[0] + ".app"
            else:
                app_destino = ejecutable

            subprocess.run(["chmod", "+x", app_origen], check=False)

            # Script externo que espera a que la app cierre, reemplaza y reabre
            script = f"""#!/bin/bash
sleep 2
cp -f "{app_origen}" "{app_destino}" 2>/dev/null
if [ $? -ne 0 ]; then
  osascript -e 'do shell script "cp -f \\"{app_origen}\\" \\"{app_destino}\\"" with administrator privileges' 2>/dev/null
fi
chmod +x "{app_destino}"
open "{app_destino}"
sleep 3
rm -rf "{extract_dir}"
rm -f "{ruta}"
"""
            script_path = os.path.join(tempfile.gettempdir(), "dentalapp_update.sh")
            with open(script_path, "w") as f:
                f.write(script)
            os.chmod(script_path, stat.S_IRWXU)

            subprocess.Popen(
                ["bash", script_path],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.status_lbl.setText("Actualizacion lista.\nLa app se cerrara y abrira la nueva version.")
            QTimer.singleShot(2000, lambda: sys.exit(0))

        except Exception as e:
            # Si algo falla, abrir Downloads y mostrar instrucciones
            subprocess.Popen(["open", _carpeta_downloads()])
            self.status_lbl.setText(
                "Descargado en Downloads.\n"
                "1. Descomprime DentalApp-Mac.zip\n"
                "2. Reemplaza DentalApp en Aplicaciones\n"
                "3. Abre la nueva version"
            )
            self.skip_btn.setEnabled(True)
            self.skip_btn.setText("Cerrar")

    def _on_error(self, msg):
        self.status_lbl.setText(f"Error al descargar: {msg}")
        self.dl_btn.setEnabled(True)
        self.dl_btn.setText("Reintentar")
        self.skip_btn.setEnabled(True)


def verificar_actualizacion(parent=None, silencioso=True):
    checker = UpdateChecker()

    def on_update(info):
        dlg = UpdateDialog(info, parent)
        dlg.exec()

    def on_sin_update():
        if not silencioso:
            m = QMessageBox(parent)
            m.setWindowTitle("Sin actualizaciones")
            m.setText("Ya tienes la version mas reciente.")
            m.setStyleSheet("color:black; background:white;")
            m.exec()

    def on_error(msg):
        if not silencioso:
            m = QMessageBox(parent)
            m.setWindowTitle("Sin conexion")
            m.setText(f"No se pudo verificar actualizaciones:\n{msg}")
            m.setStyleSheet("color:black; background:white;")
            m.exec()

    checker.on_update(on_update)
    checker.on_sin_update(on_sin_update)
    checker.on_error(on_error)
    checker.start()

    return checker
