# -*- coding: utf-8 -*-
"""
ui_add_wizard.py — Assistant d'ajout / de modification d'une famille.
"""

from __future__ import annotations

import os

import FreeCAD
from PySide2 import QtWidgets
from i18n import tr


class AddFamilyWizard(QtWidgets.QDialog):

    def __init__(
        self,
        existing: dict | None = None,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self._existing = existing
        self._result   = None
        self._setup_ui()
        if existing:
            self._populate_from_existing(existing)
        else:
            self._refresh_properties()

    def _setup_ui(self) -> None:
        self.setWindowTitle(
            tr("wizard.title_edit") if self._existing else tr("wizard.title_add")
        )
        self.setMinimumWidth(500)

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # ── ① Nom ─────────────────────────────────────────────────────────────
        grp_name = QtWidgets.QGroupBox(tr("wizard.grp_name"))
        lay_name = QtWidgets.QHBoxLayout(grp_name)
        self._edit_name = QtWidgets.QLineEdit()
        self._edit_name.setPlaceholderText(tr("wizard.name_placeholder"))
        lay_name.addWidget(self._edit_name)
        root.addWidget(grp_name)

        # ── ② Propriété identifiante ──────────────────────────────────────────
        grp_prop = QtWidgets.QGroupBox(tr("wizard.grp_property"))
        lay_prop = QtWidgets.QVBoxLayout(grp_prop)

        self._lbl_obj = QtWidgets.QLabel(tr("wizard.obj_none"))
        self._lbl_obj.setStyleSheet("color: gray; font-style: italic;")
        lay_prop.addWidget(self._lbl_obj)

        self._combo_prop = QtWidgets.QComboBox()
        self._combo_prop.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        lay_prop.addWidget(self._combo_prop)

        self._chk_all_props = QtWidgets.QCheckBox(tr("wizard.chk_all_props"))
        self._chk_all_props.toggled.connect(self._refresh_properties)
        lay_prop.addWidget(self._chk_all_props)

        btn_refresh = QtWidgets.QPushButton(tr("wizard.btn_refresh"))
        btn_refresh.clicked.connect(self._refresh_properties)
        lay_prop.addWidget(btn_refresh)

        row_manual = QtWidgets.QHBoxLayout()
        row_manual.addWidget(QtWidgets.QLabel(tr("wizard.lbl_manual")))
        self._edit_prop_manual = QtWidgets.QLineEdit()
        self._edit_prop_manual.setPlaceholderText(tr("wizard.prop_manual_placeholder"))
        row_manual.addWidget(self._edit_prop_manual)
        lay_prop.addLayout(row_manual)

        root.addWidget(grp_prop)

        # ── ③ Macro associée ──────────────────────────────────────────────────
        grp_macro = QtWidgets.QGroupBox(tr("wizard.grp_macro"))
        lay_macro = QtWidgets.QHBoxLayout(grp_macro)
        self._edit_macro = QtWidgets.QLineEdit()
        self._edit_macro.setReadOnly(True)
        self._edit_macro.setPlaceholderText(tr("wizard.macro_placeholder"))
        btn_browse = QtWidgets.QPushButton(tr("wizard.btn_browse"))
        btn_browse.clicked.connect(self._browse_macro)
        lay_macro.addWidget(self._edit_macro)
        lay_macro.addWidget(btn_browse)
        root.addWidget(grp_macro)

        # ── Boutons de validation ─────────────────────────────────────────────
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        root.addWidget(sep)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self._btn_ok  = QtWidgets.QPushButton(tr("wizard.btn_ok"))
        self._btn_ok.setDefault(True)
        btn_cancel = QtWidgets.QPushButton(tr("wizard.btn_cancel"))
        btn_row.addWidget(self._btn_ok)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        self._btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)

    def _refresh_properties(self) -> None:
        from detector import get_selected_object, get_custom_properties, get_all_properties

        obj = get_selected_object()
        self._combo_prop.clear()

        if obj is None:
            self._lbl_obj.setText(tr("wizard.obj_none"))
            self._lbl_obj.setStyleSheet("color: gray; font-style: italic;")
            return

        self._lbl_obj.setText(
            tr("wizard.obj_selected", label=obj.Label, type=type(obj).__name__)
        )
        self._lbl_obj.setStyleSheet("color: #2a7; font-weight: bold;")

        props = (get_all_properties(obj)
                 if self._chk_all_props.isChecked()
                 else get_custom_properties(obj))

        if not props:
            self._combo_prop.addItem(tr("wizard.no_custom_props"))
            return

        for prop_name, group, type_id in props:
            display = f"{prop_name}   [{group}]  — {type_id}"
            self._combo_prop.addItem(display, prop_name)

    def _populate_from_existing(self, existing: dict) -> None:
        self._edit_name.setText(existing.get("name", ""))
        self._edit_macro.setText(existing.get("macro", ""))
        self._edit_prop_manual.setText(existing.get("property", ""))
        self._refresh_properties()

    def _browse_macro(self) -> None:
        macro_dir = FreeCAD.getUserMacroDir(True)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            tr("wizard.browse_title"),
            macro_dir,
            tr("wizard.browse_filter"),
        )
        if path:
            self._edit_macro.setText(path)

    def _resolve_property(self) -> str:
        manual = self._edit_prop_manual.text().strip()
        if manual:
            return manual
        data = self._combo_prop.currentData()
        return data if data else ""

    def _on_ok(self) -> None:
        name       = self._edit_name.text().strip()
        prop       = self._resolve_property()
        macro_path = self._edit_macro.text().strip()

        errors = []
        if not name:
            errors.append(tr("wizard.err_name"))
        if not prop:
            errors.append(tr("wizard.err_property"))
        if not macro_path:
            errors.append(tr("wizard.err_macro_required"))
        elif not os.path.isfile(macro_path):
            errors.append(tr("wizard.err_macro_missing", path=macro_path))

        if errors:
            QtWidgets.QMessageBox.warning(
                self, tr("wizard.err_title"), "\n".join(errors)
            )
            return

        self._result = {"name": name, "prop": prop, "macro_path": macro_path}
        self.accept()

    def get_result(self):
        return self._result
