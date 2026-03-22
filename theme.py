# Colores y estilos globales de la app.
# Si se necesita cambiar la paleta, hacerlo aqui para que afecte todo.


def get_palette():
    return {
        "PRIMARY":    "#1A6B8A",
        "SECONDARY":  "#2196B0",
        "ACCENT":     "#4ECDC4",
        "BG":         "#F5F8FA",
        "CARD":       "#FFFFFF",
        "TEXT":       "#2C3E50",
        "MUTED":      "#7F8C8D",
        "DANGER":     "#E74C3C",
        "SUCCESS":    "#27AE60",
        "WARNING":    "#F39C12",
        "BORDER":     "#DEE4E8",
        "SIDEBAR_BG": "#0F3D52",
        "SIDEBAR_HVR":"#1A6B8A",
        "SIDEBAR_ACT":"#2196B0",
        "SIDEBAR_TXT":"#FFFFFF",
        "INPUT_BG":   "#FFFFFF",
    }


def app_stylesheet():
    p = get_palette()
    return f"""
        QMainWindow, QDialog {{ background:{p['BG']}; color:{p['TEXT']}; }}
        QWidget   {{ background:{p['BG']}; color:{p['TEXT']}; }}
        QLabel    {{ background:transparent; color:{p['TEXT']}; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background:{p['INPUT_BG']}; color:{p['TEXT']};
            border:1.5px solid {p['BORDER']}; border-radius:8px;
            padding:7px 10px; font-size:13px;
        }}
        QLineEdit:focus, QTextEdit:focus {{ border-color:{p['SECONDARY']}; }}

        QComboBox {{
            background:{p['INPUT_BG']}; color:{p['TEXT']};
            border:1.5px solid {p['BORDER']}; border-radius:8px;
            padding:7px 10px; font-size:13px;
        }}
        QComboBox QAbstractItemView {{
            background:{p['CARD']}; color:{p['TEXT']};
            selection-background-color:{p['PRIMARY']};
        }}

        QSpinBox, QDoubleSpinBox {{
            background:{p['INPUT_BG']}; color:{p['TEXT']};
            border:1.5px solid {p['BORDER']}; border-radius:8px;
            padding:7px 10px; font-size:13px;
        }}

        QDateEdit {{
            background:{p['INPUT_BG']}; color:{p['TEXT']};
            border:1.5px solid {p['BORDER']}; border-radius:8px;
            padding:7px 10px; font-size:13px;
        }}

        QTableWidget {{
            background:{p['CARD']}; color:{p['TEXT']};
            border:1px solid {p['BORDER']}; border-radius:10px;
            gridline-color:{p['BORDER']};
        }}
        QTableWidget::item {{ color:{p['TEXT']}; padding:8px; }}
        QTableWidget::item:alternate {{ background:{p['BG']}; }}
        QTableWidget::item:selected {{ background:{p['PRIMARY']}; color:white; }}
        QHeaderView::section {{
            background:{p['PRIMARY']}; color:white;
            padding:9px; font-weight:700; border:none;
        }}

        QTabWidget::pane {{ border:none; background:{p['BG']}; }}
        QTabBar::tab {{
            background:{p['BG']}; color:{p['MUTED']};
            padding:9px 20px; font-size:13px; font-weight:600;
            border-radius:0; margin-right:2px;
            border-bottom:2px solid transparent;
        }}
        QTabBar::tab:selected {{
            color:{p['PRIMARY']}; border-bottom:3px solid {p['PRIMARY']};
            background:{p['CARD']};
        }}
        QTabBar::tab:hover {{ color:{p['TEXT']}; }}

        QScrollBar:vertical {{
            background:{p['BORDER']}; width:12px;
            border-radius:6px; margin:0;
        }}
        QScrollBar::handle:vertical {{
            background:{p['PRIMARY']}; border-radius:6px; min-height:40px;
        }}
        QScrollBar::handle:vertical:hover {{ background:{p['SECONDARY']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; border:none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}

        QScrollBar:horizontal {{
            background:{p['BORDER']}; height:12px;
            border-radius:6px; margin:0;
        }}
        QScrollBar::handle:horizontal {{
            background:{p['PRIMARY']}; border-radius:6px; min-width:40px;
        }}
        QScrollBar::handle:horizontal:hover {{ background:{p['SECONDARY']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0px; border:none; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}

        QScrollArea {{ border:none; background:transparent; }}
        QAbstractScrollArea {{ border:none; }}
        QAbstractScrollArea::corner {{ background:{p['BORDER']}; }}
        QAbstractScrollArea QScrollBar:vertical {{ width:12px; }}
        QAbstractScrollArea QScrollBar:horizontal {{ height:12px; }}

        QToolTip {{
            background:{p['CARD']}; color:{p['TEXT']};
            border:1px solid {p['BORDER']}; padding:4px; font-size:12px;
        }}
    """
