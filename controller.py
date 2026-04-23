# -*- coding: utf-8 -*-
"""
controller.py — Contrôleur principal de Smart Finder.

  1 famille détectée  → lancement direct, sans dialogue
  0 famille           → dialogue, aucune pré-sélection
  N familles (ambigu) → dialogue, bandeau orange, choix manuel
"""

from __future__ import annotations

import FreeCAD
from PySide2 import QtWidgets

import families as fam_mod
from detector  import get_selected_object, detect_all_families
from i18n      import tr
from launcher  import launch_macro
from ui_main   import MainDialog, EDIT_CODE
from ui_editor import EditorDialog


class SmartFinderController:

    def run(self) -> None:
        if not hasattr(FreeCAD, "Gui") or FreeCAD.Gui is None:
            FreeCAD.Console.PrintError(tr("ctrl.no_gui"))
            return

        families = fam_mod.load_families()
        obj      = get_selected_object()
        matches  = detect_all_families(obj, families)

        # ── Correspondance unique → lancement direct ──────────────────────────
        if len(matches) == 1:
            family = matches[0]
            label  = getattr(obj, "Label", "?")
            FreeCAD.Console.PrintMessage(
                tr("ctrl.direct_launch", name=family["name"], label=label)
            )
            launch_macro(family["macro"])
            return

        # ── 0 ou N matches → dialogue ─────────────────────────────────────────
        ambiguous_names = [f["name"] for f in matches] if len(matches) > 1 else []
        detected_label  = getattr(obj, "Label", None) if obj else None

        if ambiguous_names:
            FreeCAD.Console.PrintWarning(
                tr("ctrl.ambiguous_warn",
                   label=detected_label or "?",
                   names=", ".join(ambiguous_names))
            )

        self._run_main_dialog(families, detected_label, ambiguous_names)

    # ─────────────────────────────────────────────────────────────────────────

    def _run_main_dialog(
        self,
        families:        list,
        detected_label:  str | None,
        ambiguous_names: list,
    ) -> None:

        while True:
            if not families:
                reply = QtWidgets.QMessageBox.question(
                    None,
                    tr("ctrl.no_family_title"),
                    tr("ctrl.no_family_msg"),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.Yes,
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    editor = EditorDialog(families)
                    editor.exec_()
                    families        = fam_mod.load_families()
                    ambiguous_names = []
                    continue
                break

            dlg = MainDialog(
                families,
                detected_label  = detected_label,
                ambiguous_names = ambiguous_names,
            )
            result = dlg.exec_()

            if result == QtWidgets.QDialog.Accepted:
                selected = dlg.get_selected_family()
                if selected:
                    launch_macro(selected["macro"])
                break

            elif result == EDIT_CODE:
                editor = EditorDialog(families)
                editor.exec_()
                families        = fam_mod.load_families()
                ambiguous_names = []

            else:
                break
