"""
notificaciones.py
Sistema de recordatorios de citas:
  - Notificación nativa de Windows (plyer)
  - Ventana emergente dentro de la app
  - Timer que revisa cada minuto
"""

import os, sys
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont

sys.path.insert(0, os.path.dirname(__file__))
from database.db_manager import get_connection


# ── DB helper ─────────────────────────────────────────────────────────────────
def get_citas_proximas(minutos_antes=60) -> list:
    """Citas que empiezan en los próximos `minutos_antes` minutos y están pendientes/confirmadas."""
    conn = get_connection()
    cur  = conn.cursor()
    hoy  = date.today().strftime("%Y-%m-%d")
    ahora = datetime.now()

    cur.execute("""
        SELECT c.*, p.nombre || ' ' || p.apellido AS paciente_nombre
        FROM citas c
        LEFT JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.fecha = ? AND c.estado IN ('pendiente', 'confirmada')
        ORDER BY c.hora
    """, (hoy,))

    resultado = []
    for row in cur.fetchall():
        r = dict(row)
        try:
            cita_dt = datetime.strptime(f"{r['fecha']} {r['hora']}", "%Y-%m-%d %H:%M")
            diff = (cita_dt - ahora).total_seconds() / 60  # minutos
            if 0 < diff <= minutos_antes:
                r["minutos_restantes"] = int(diff)
                r["hora_formato"] = cita_dt.strftime("%I:%M %p")
                resultado.append(r)
        except Exception:
            pass

    conn.close()
    return resultado


# ── Notificación nativa (cross-platform) ─────────────────────────────────────
def notificar_sistema(titulo: str, mensaje: str):
    """Envía notificación nativa según el sistema operativo."""
    import sys, subprocess

    # Intentar con plyer (funciona en Windows y Mac)
    try:
        from plyer import notification
        notification.notify(
            title=titulo,
            message=mensaje,
            app_name="DentalApp",
            timeout=10
        )
        return True
    except Exception:
        pass

    # Mac — usar osascript
    if sys.platform == "darwin":
        try:
            subprocess.Popen([
                "osascript", "-e",
                f'display notification "{mensaje}" with title "{titulo}"'
            ])
            return True
        except Exception:
            pass

    # Windows — usar PowerShell
    elif sys.platform == "win32":
        try:
            script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $template.SelectSingleNode('//text[@id=1]').InnerText = '{titulo}'
            $template.SelectSingleNode('//text[@id=2]').InnerText = '{mensaje}'
            $notif = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('DentalApp').Show($notif)
            """
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            return True
        except Exception:
            pass

    return False

# Alias para compatibilidad
notificar_windows = notificar_sistema


# ── In-app popup notification ─────────────────────────────────────────────────
class NotificacionPopup(QFrame):
    cerrado = pyqtSignal()

    def __init__(self, citas: list, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build(citas)
        self._posicionar()

    def _build(self, citas):
        self.setStyleSheet("""
            QFrame#popup {
                background: #1A6B8A;
                border-radius: 12px;
                border: 2px solid #4ECDC4;
            }
        """)
        self.setObjectName("popup")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setStyleSheet("background: #4ECDC4; border-radius: 10px 10px 0 0;")
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(14, 10, 14, 10)
        bell = QLabel("🔔")
        bell.setFont(QFont("Segoe UI", 16))
        bell.setStyleSheet("background:transparent; color:white;")
        hl.addWidget(bell)
        title = QLabel("Recordatorio de Citas")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("background:transparent; color:white;")
        hl.addWidget(title)
        hl.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.2); color:white;
                border-radius: 12px; border:none; font-size:12px; font-weight:700;
            }
            QPushButton:hover { background: rgba(255,255,255,0.4); }
        """)
        close_btn.clicked.connect(self._cerrar)
        hl.addWidget(close_btn)
        layout.addWidget(hdr)

        # Citas
        body = QWidget()
        body.setStyleSheet("background: #1A6B8A; border-radius: 0 0 10px 10px;")
        bl = QVBoxLayout(body); bl.setContentsMargins(14, 10, 14, 12); bl.setSpacing(8)

        for c in citas[:5]:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.1);
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.2);
                }
            """)
            cl = QHBoxLayout(card); cl.setContentsMargins(10, 8, 10, 8); cl.setSpacing(10)

            left = QVBoxLayout(); left.setSpacing(2)
            pac = QLabel(f"👤  {c.get('paciente_nombre','—')}")
            pac.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            pac.setStyleSheet("color:white; background:transparent; border:none;")
            motivo = QLabel(f"📋  {c.get('motivo','Sin motivo') or 'Sin motivo'}")
            motivo.setStyleSheet("color: #B2EBF2; font-size:11px; background:transparent; border:none;")
            left.addWidget(pac); left.addWidget(motivo)

            right = QVBoxLayout(); right.setSpacing(2); right.setAlignment(Qt.AlignmentFlag.AlignRight)
            mins  = c.get("minutos_restantes", 0)
            tiempo_lbl = QLabel(f"⏰ {mins} min")
            tiempo_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            tiempo_lbl.setStyleSheet(
                f"color: {'#FFD43B' if mins <= 15 else '#51CF66'}; background:transparent; border:none;"
            )
            hora_lbl = QLabel(c.get("hora_formato",""))
            hora_lbl.setStyleSheet("color: #B2EBF2; font-size:11px; background:transparent; border:none;")
            right.addWidget(tiempo_lbl); right.addWidget(hora_lbl)

            cl.addLayout(left); cl.addStretch(); cl.addLayout(right)
            bl.addWidget(card)

        layout.addWidget(body)

        # Auto-close timer (30 segundos)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._cerrar)
        self._timer.start(30_000)

    def _posicionar(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        x = screen.right()  - self.width()  - 20
        y = screen.bottom() - self.height() - 20
        self.move(x, y)

    def _cerrar(self):
        self._timer.stop()
        self.hide()
        self.cerrado.emit()
        self.deleteLater()


# ── Reminder manager ──────────────────────────────────────────────────────────
class ReminderManager(QObject):
    mostrar_popup = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notificadas = set()  # IDs ya notificados hoy
        self._popup = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._revisar)
        self._timer.start(60_000)  # revisar cada minuto

        # Primera revisión al arrancar (5 segundos después)
        QTimer.singleShot(5_000, self._revisar)

    def _revisar(self):
        citas = get_citas_proximas(minutos_antes=60)

        # Filtrar las que ya notificamos
        nuevas = [c for c in citas if c["id"] not in self._notificadas]
        if not nuevas:
            return

        for c in nuevas:
            self._notificadas.add(c["id"])
            # Notificación de Windows
            mins = c.get("minutos_restantes", 60)
            notificar_windows(
                "🦷 DentalApp — Cita próxima",
                f"{c.get('paciente_nombre','Paciente')} en {mins} min\n"
                f"{c.get('hora_formato','')} — {c.get('motivo','') or 'Sin motivo'}"
            )

        # Popup in-app
        self.mostrar_popup.emit(nuevas)

    def mostrar(self, citas: list, parent_widget=None):
        """Llamado desde main para mostrar el popup en la ventana principal."""
        if self._popup:
            try:
                self._popup.deleteLater()
            except Exception:
                pass

        self._popup = NotificacionPopup(citas, parent_widget)
        self._popup.show()
