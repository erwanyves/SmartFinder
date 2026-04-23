# -*- coding: utf-8 -*-
"""
ui_editor.py — Dialogue de gestion (CRUD) des familles Smart Finder.
"""

from __future__ import annotations

import os

from PySide2 import QtWidgets
from i18n import tr


class EditorDialog(QtWidgets.QDialog):

    def __init__(self, families: list, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._families = families
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        self.setWindowTitle(tr("editor.title"))
        self.setMinimumSize(600, 380)

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        lbl = QtWidgets.QLabel(tr("editor.intro"))
        lbl.setWordWrap(True)
        root.addWidget(lbl)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels([
            tr("editor.col_family"),
            tr("editor.col_property"),
            tr("editor.col_macro"),
        ])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._tree.header().setStretchLastSection(True)
        self._tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self._tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self._tree.doubleClicked.connect(self._on_edit)
        root.addWidget(self._tree)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_add    = QtWidgets.QPushButton(tr("editor.btn_add"))
        self._btn_edit   = QtWidgets.QPushButton(tr("editor.btn_edit"))
        self._btn_delete = QtWidgets.QPushButton(tr("editor.btn_delete"))
        self._btn_close  = QtWidgets.QPushButton(tr("editor.btn_close"))

        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_close)
        root.addLayout(btn_row)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_close.clicked.connect(self.accept)

    def _refresh_list(self) -> None:
        self._tree.clear()
        for f in self._families:
            macro_short = os.path.basename(f.get("macro", ""))
            item = QtWidgets.QTreeWidgetItem([
                f.get("name", ""),
                f.get("property", ""),
                macro_short,
            ])
            item.setToolTip(2, f.get("macro", ""))
            self._tree.addTopLevelItem(item)

    def _current_index(self):
        idx = self._tree.currentIndex().row()
        return idx if 0 <= idx < len(self._families) else None

    def _on_add(self) -> None:
        from ui_add_wizard import AddFamilyWizard
        import families as fam_mod

        dlg = AddFamilyWizard(parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            result = dlg.get_result()
            if result:
                fam_mod.add_family(
                    self._families,
                    name       = result["name"],
                    prop       = result["prop"],
                    macro_path = result["macro_path"],
                )
                self._refresh_list()

    def _on_edit(self) -> None:
        idx = self._current_index()
        if idx is None:
            QtWidgets.QMessageBox.information(
                self,
                tr("editor.no_selection_title"),
                tr("editor.no_selection_edit"),
            )
            return

        from ui_add_wizard import AddFamilyWizard
        import families as fam_mod

        dlg = AddFamilyWizard(existing=self._families[idx], parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            result = dlg.get_result()
            if result:
                fam_mod.update_family(
                    self._families, idx,
                    name       = result["name"],
                    prop       = result["prop"],
                    macro_path = result["macro_path"],
                )
                self._refresh_list()

    def _on_delete(self) -> None:
        idx = self._current_index()
        if idx is None:
            QtWidgets.QMessageBox.information(
                self,
                tr("editor.no_selection_title"),
                tr("editor.no_selection_delete"),
            )
            return

        import families as fam_mod

        name  = self._families[idx].get("name", "?")
        reply = QtWidgets.QMessageBox.question(
            self,
            tr("editor.confirm_delete_title"),
            tr("editor.confirm_delete_msg", name=name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            fam_mod.remove_family(self._families, idx)
            self._refresh_list()
