"""
license_manager.py
Sistema de licencias vinculado al hardware.

Flujo:
1. La app lee el hardware_id de la máquina.
2. Busca un archivo license.key en la carpeta de la app.
3. Verifica que la clave fue generada para ESE hardware_id.
4. Si es válida, arranca. Si no, muestra pantalla de activación.

Para generar licencias usa: generate_license.py (script separado para el vendedor)
"""

import hashlib
import hmac
import os
import sys
import uuid
import json
import subprocess
import platform

# ── Clave secreta interna (cámbiala por algo tuyo y no la compartas) ──────────
_SECRET = b"DentalApp2026-X9k#mZqLpR"

def _get_app_data_dir():
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
    app_dir = os.path.join(base, 'DentalApp')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

LICENSE_FILE = os.path.join(_get_app_data_dir(), "license.key")


# ── Obtener ID de hardware ────────────────────────────────────────────────────
def get_hardware_id() -> str:
    """Obtiene un identificador único del hardware de la máquina."""
    system = platform.system()
    raw = ""

    try:
        if system == "Windows":
            # Usa el UUID del motherboard vía WMIC
            result = subprocess.check_output(
                "wmic csproduct get UUID", shell=True, stderr=subprocess.DEVNULL
            ).decode().strip().split("\n")
            raw = result[-1].strip()

        elif system == "Linux":
            with open("/etc/machine-id") as f:
                raw = f.read().strip()

        elif system == "Darwin":  # macOS
            result = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stderr=subprocess.DEVNULL
            ).decode()
            for line in result.split("\n"):
                if "IOPlatformUUID" in line:
                    raw = line.split('"')[-2]
                    break
    except Exception:
        pass

    if not raw or raw.upper() in ("UUID", "", "NONE"):
        # Fallback: MAC address
        raw = str(uuid.getnode())

    # Hash del raw para que no sea legible
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
    # Formato: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    return "-".join(hashed[i:i+4] for i in range(0, 24, 4))


# ── Generar licencia (usado por el vendedor) ──────────────────────────────────
def generate_license(hardware_id: str) -> str:
    """Genera una clave de licencia para un hardware_id dado."""
    payload = f"DENTAL:{hardware_id}:LICENSED"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32].upper()
    return "-".join(sig[i:i+8] for i in range(0, 32, 8))


# ── Verificar licencia ────────────────────────────────────────────────────────
# ── IDs de desarrollo (siempre activos, sin necesitar licencia) ───────────────
_DEV_IDS = {
    "C406-4DF8-221D-B4DB-E9B9-85D6",  # Gaelo - PC principal
}


def verify_license() -> tuple[bool, str]:
    """
    Verifica si la licencia instalada es válida para este hardware.
    Retorna (True, "") si es válida, (False, motivo) si no.
    """
    # Modo desarrollador — sin necesidad de licencia
    if get_hardware_id() in _DEV_IDS:
        return True, "Desarrollador"

    if not os.path.exists(LICENSE_FILE):
        return False, "no_file"

    try:
        with open(LICENSE_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return False, "corrupted"

    stored_hw   = data.get("hardware_id", "")
    stored_key  = data.get("license_key", "")
    consultorio = data.get("consultorio", "")

    current_hw = get_hardware_id()

    if stored_hw != current_hw:
        return False, "wrong_machine"

    expected = generate_license(current_hw)
    if stored_key != expected:
        return False, "invalid_key"

    return True, consultorio


# ── Guardar licencia ──────────────────────────────────────────────────────────
def save_license(hardware_id: str, license_key: str, consultorio: str) -> bool:
    """Guarda la licencia en disco tras validarla."""
    expected = generate_license(hardware_id)
    if license_key != expected:
        return False
    current_hw = get_hardware_id()
    if hardware_id != current_hw:
        return False
    data = {
        "hardware_id":  hardware_id,
        "license_key":  license_key,
        "consultorio":  consultorio,
    }
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True
