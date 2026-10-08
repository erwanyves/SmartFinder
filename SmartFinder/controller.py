# -*- coding: utf-8 -*-
"""
controller.py — Contrôleur principal de Smart Finder.

Deux axes de détection, articulés dans `run()` (voir detector.py) :

  A. Reconnaissance d'un composant EXISTANT (propriété identifiante) :
       1 famille détectée  → lancement direct, sans dialogue.
       N familles (ambigu) → dialogue, bandeau orange, choix manuel.

  B. Si aucun composant existant n'est reconnu, classification du TYPE
     géométrique brut de la sélection (Body/Part, arc/cercle, LCS) pour
     filtrer les familles qui déclarent savoir s'y positionner pour une
     CRÉATION (`detection_modes`) :
       rien sélectionné     → liste complète + option macros non enregistrées.
       1 famille filtrée    → lancement direct.
       N familles filtrées  → dialogue restreint, bandeau orange.
       0 famille filtrée    → repli sur la liste complète, message explicite.
"""

from __future__ import annotations

import FreeCAD
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

import families as fam_mod
from detector  import get_selected_component, detect_all_families, classify_selection_geometry
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
        # Remonte au besoin vers le composant parent (clic sur une face/arête
        # dans la vue 3D plutôt que sur l'objet racine dans l'arbre).
        obj      = get_selected_component(families)
        matches  = detect_all_families(obj, families)

        # ── A. Composant existant reconnu, correspondance unique → lancement direct
        if len(matches) == 1:
            family = matches[0]
            label  = getattr(obj, "Label", "?")
            FreeCAD.Console.PrintMessage(
                tr("ctrl.direct_launch", name=family["name"], label=label)
            )
            launch_macro(family["macro"])
            return

        # ── A. Composant existant reconnu, mais ambigu → dialogue restreint
        if len(matches) > 1:
            names = [f["name"] for f in matches]
            FreeCAD.Console.PrintWarning(
                tr("ctrl.ambiguous_warn",
                   label=getattr(obj, "Label", "?"), names=", ".join(names))
            )
            self._run_main_dialog(matches, getattr(obj, "Label", None), names)
            return

        # ── B. Aucun composant existant reconnu : bascule sur le type
        #      géométrique brut de la sélection courante ───────────────────
        if obj is None:
            # Rien n'est sélectionné → point d'entrée principal de
            # SmartFinder : liste des familles enregistrées, avec option
            # d'inclure les macros non enregistrées (uniquement ici).
            self._run_main_dialog(
                families, None, [], allow_browse_unregistered=True
            )
            return

        label    = getattr(obj, "Label", None)
        geo_mode = classify_selection_geometry()

        if geo_mode in (None, "surface_geometry"):
            # Type non reconnu, ou surface/élément de géométrie non circulaire
            # sans famille déclarant s'y positionner (aucun mode dédié pour
            # ce cas, voir spec 25/08/2026) → repli sur la liste complète.
            self._run_main_dialog(
                families, label, [],
                info_message=tr("main.no_geo_match", label=label or "?"),
            )
            return

        filtered = [f for f in families if geo_mode in (f.get("detection_modes") or [])]

        if len(filtered) == 1:
            family = filtered[0]
            FreeCAD.Console.PrintMessage(
                tr("ctrl.direct_launch", name=family["name"], label=label or "?")
            )
            launch_macro(family["macro"])
            return

        if filtered:
            names = [f["name"] for f in filtered]
            self._run_main_dialog(filtered, label, names)
            return

        # Aucune famille ne déclare accepter ce type d'élément → repli sur
        # la liste complète, avec message explicite.
        self._run_main_dialog(
            families, label, [],
            info_message=tr("main.no_geo_match", label=label or "?"),
        )

    # ─────────────────────────────────────────────────────────────────────────

    def _run_main_dialog(
        self,
        families:                   list,
        detected_label:             str | None,
        ambiguous_names:            list,
        allow_browse_unregistered:  bool = False,
        info_message:               str | None = None,
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
                detected_label            = detected_label,
                ambiguous_names           = ambiguous_names,
                info_message              = info_message,
                allow_browse_unregistered = allow_browse_unregistered,
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
                info_message    = None
                continue

            else:
                break
