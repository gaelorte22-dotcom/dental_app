"""
app_utils.py
Utilidades compartidas entre módulos.
"""
import os
import sys


def get_app_data_dir() -> str:
    """
    Retorna la carpeta de datos de la app según el sistema operativo.
    Windows: C:/Users/[user]/AppData/Roaming/DentalApp/
    Mac:     /Users/[user]/Library/Application Support/DentalApp/
    Linux:   /home/[user]/.dentalapp/
    """
    if sys.platform == "win32" or os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.expanduser("~")

    app_dir = os.path.join(base, "DentalApp")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir
