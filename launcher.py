# -*- coding: utf-8 -*-
"""
launcher.py — Exécution d'une macro FreeCAD (.FCMacro / .py).

La macro cible est exécutée dans son propre espace de nommage, avec
__file__ et __name__ correctement initialisés, de façon à ce qu'elle
se comporte exactement comme si elle avait été lancée directement
depuis le gestionnaire de macros de FreeCAD.
"""

from __future__ import annotations

import os
import traceback

import FreeCAD


def launch_macro(macro_path: str) -> bool:
    """Exécute la macro située à `macro_path`.

    Args:
        macro_path: chemin absolu vers le fichier .FCMacro ou .py.

    Returns:
        True si l'exécution s'est terminée sans exception, False sinon.
    """
    if not macro_path:
        FreeCAD.Console.PrintError("SmartFinder : chemin de macro vide.\n")
        return False

    if not os.path.isfile(macro_path):
        FreeCAD.Console.PrintError(
            f"SmartFinder : macro introuvable → {macro_path}\n"
        )
        return False

    FreeCAD.Console.PrintMessage(f"SmartFinder : lancement de {macro_path}\n")

    # Espace de nommage isolé pour la macro
    namespace: dict = {
        "__file__" : macro_path,
        "__name__" : "__main__",
        "__package__": None,
    }

    try:
        with open(macro_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        code = compile(source, macro_path, "exec")
        exec(code, namespace)       # noqa: S102
        return True

    except SystemExit:
        # Une macro peut appeler sys.exit() — on le tolère silencieusement.
        return True

    except Exception:
        FreeCAD.Console.PrintError(
            f"SmartFinder : erreur lors de l'exécution de {macro_path} :\n"
            f"{traceback.format_exc()}\n"
        )
        return False
