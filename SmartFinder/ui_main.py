# -*- coding: utf-8 -*-
"""
ui_main.py — Dialogue principal de Smart Finder.

Affiché quand la détection automatique d'un composant existant échoue ou
est ambiguë, ou quand la sélection est filtrée/repliée sur la liste des
familles enregistrées (voir controller.py).

Codes de retour :
    QDialog.Accepted (1)  → Lancer
    QDialog.Rejected (0)  → Annuler
    EDIT_CODE        (2)  → Éditer les types…
"""

from __future__ import annotations

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
from i18n import tr

EDIT_CODE: int = 2


class MainDialog(QtWidgets.QDialog):

    def __init__(
        self,
        families:                   list,
        detected_label:             str | None = None,
        ambiguous_names:            list       = None,
        info_message:               str | None = None,
        allow_browse_unregistered:  bool       = False,
        parent:                     QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self._families                  = families
        self._detected_label            = detected_label
        self._ambiguous_names           = ambiguous_names or []
        self._info_message              = info_message
        self._allow_browse_unregistered = allow_browse_unregistered
        self._display_families          = list(families)
        self._selected                  = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle(tr("main.title"))
        self.setMinimumWidth(420)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        if self._ambiguous_names:
            root.addWidget(self._make_banner_ambiguous())
        else:
            lbl = QtWidgets.QLabel(self._info_message or tr("main.no_selection"))
            lbl.setWordWrap(True)
            root.addWidget(lbl)

        self._combo = QtWidgets.QComboBox()
        self._populate_combo()
        root.addWidget(self._combo)

        if self._allow_browse_unregistered:
            self._chk_browse = QtWidgets.QCheckBox(tr("main.chk_browse_unregistered"))
            self._chk_browse.toggled.connect(self._on_toggle_browse)
            root.addWidget(self._chk_browse)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_ok     = QtWidgets.QPushButton(tr("main.btn_launch"))
        self._btn_edit   = QtWidgets.QPushButton(tr("main.btn_edit_types"))
        self._btn_cancel = QtWidgets.QPushButton(tr("main.btn_cancel"))

        self._btn_ok.setDefault(True)
        self._btn_ok.setEnabled(bool(self._display_families))

        btn_row.addWidget(self._btn_ok)
        btn_row.addWidget(self._btn_edit)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_cancel)
        root.addLayout(btn_row)

        self._btn_ok.clicked.connect(self._on_launch)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_cancel.clicked.connect(self.reject)

    def _populate_combo(self) -> None:
        self._combo.clear()
        for f in self._display_families:
            self._combo.addItem(f["name"])

    def _on_toggle_browse(self, checked: bool) -> None:
        if checked:
            import families as fam_mod
            extra = fam_mod.list_unregistered_macros(self._families)
            self._display_families = list(self._families) + extra
        else:
            self._display_families = list(self._families)
        self._populate_combo()
        self._btn_ok.setEnabled(bool(self._display_families))

    def _make_banner_ambiguous(self) -> QtWidgets.QFrame:
        names_str = ", ".join(f"<b>{n}</b>" for n in self._ambiguous_names)
        obj_str   = (f"<b>{self._detected_label}</b>"
                     if self._detected_label
                     else tr("main.ambiguous_obj"))
        html = tr("main.ambiguous_html", obj=obj_str, names=names_str)

        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background: #fcf8e3; border: 1px solid #faebcc; border-radius: 4px; }"
        )
        lay = QtWidgets.QHBoxLayout(frame)
        lay.setContentsMargins(8, 6, 8, 6)

        icon = QtWidgets.QLabel("⚠")
        icon.setStyleSheet("color: #8a6d3b; font-size: 16px; font-weight: bold;"
                           " border: none; background: transparent;")
        lay.addWidget(icon)

        text = QtWidgets.QLabel(html)
        text.setWordWrap(True)
        text.setStyleSheet("color: #6d4c00; border: none; background: transparent;")
        lay.addWidget(text, stretch=1)
        return frame

    def _on_launch(self) -> None:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._display_families):
            self._selected = self._display_families[idx]
        self.accept()

    def _on_edit(self) -> None:
        self._selected = None
        self.done(EDIT_CODE)

    def get_selected_family(self):
        return self._selected
