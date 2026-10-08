# -*- coding: utf-8 -*-
"""
families.py — Couche d'accès aux données des familles de composants.

Chaque famille est un dict :
    {
        "name"            : str        — nom affiché (ex. "Oring")
        "property"        : str        — nom de la propriété FreeCAD identifiant la famille
        "macro"           : str        — chemin absolu vers la .FCMacro associée
        "detection_modes" : list[str]  — types de sélection bruts acceptés pour une
                                          CRÉATION (indépendant de la reconnaissance par
                                          propriété identifiante ci-dessus, voir detector.py) :
                                          "body_part", "arc_circle", "lcs". Optionnel,
                                          [] par défaut (rétro-compatible avec les
                                          entrées existantes qui n'ont pas ce champ).
    }

Les données sont persistées dans families.json, dans le même dossier que ce module.
"""

import json
import os

# ── Chemin du fichier de données ─────────────────────────────────────────────
_DATA_FILE = os.path.join(os.path.dirname(__file__), "families.json")


# ─────────────────────────────────────────────────────────────────────────────
#  Lecture / écriture
# ─────────────────────────────────────────────────────────────────────────────

def load_families() -> list:
    """Charge et retourne la liste des familles depuis families.json.
    Retourne [] si le fichier n'existe pas encore.
    """
    if not os.path.isfile(_DATA_FILE):
        return []
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Validation minimale : garder uniquement les dicts bien formés
        return [f for f in data if _is_valid(f)]
    except (json.JSONDecodeError, OSError) as exc:
        import FreeCAD
        FreeCAD.Console.PrintWarning(
            f"SmartFinder : impossible de lire families.json ({exc})\n"
        )
        return []


def save_families(families: list) -> None:
    """Persiste la liste des familles dans families.json."""
    try:
        with open(_DATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(families, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        import FreeCAD
        FreeCAD.Console.PrintError(
            f"SmartFinder : impossible d'écrire families.json ({exc})\n"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  CRUD
# ─────────────────────────────────────────────────────────────────────────────

def add_family(
    families: list,
    name: str,
    prop: str,
    macro_path: str,
    detection_modes: list | None = None,
) -> None:
    """Ajoute une nouvelle famille et sauvegarde."""
    families.append({
        "name": name,
        "property": prop,
        "macro": macro_path,
        "detection_modes": list(detection_modes or []),
    })
    save_families(families)


def update_family(
    families: list,
    index: int,
    name: str,
    prop: str,
    macro_path: str,
    detection_modes: list | None = None,
) -> None:
    """Met à jour la famille à l'index donné et sauvegarde."""
    if 0 <= index < len(families):
        families[index] = {
            "name": name,
            "property": prop,
            "macro": macro_path,
            "detection_modes": list(detection_modes or []),
        }
        save_families(families)


def remove_family(families: list, index: int) -> None:
    """Supprime la famille à l'index donné et sauvegarde."""
    if 0 <= index < len(families):
        families.pop(index)
        save_families(families)


def find_by_name(families: list, name: str) -> dict | None:
    """Retourne la famille dont le nom correspond (insensible à la casse)."""
    name_lower = name.lower()
    for f in families:
        if f.get("name", "").lower() == name_lower:
            return f
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Macros non enregistrées (option affichée uniquement quand rien n'est
#  sélectionné à l'appel de SmartFinder — voir controller.py)
# ─────────────────────────────────────────────────────────────────────────────

def list_unregistered_macros(families: list) -> list:
    """Retourne les fichiers .py / .FCMacro à la racine du dossier macro
    FreeCAD qui ne sont pas déjà associés à une famille enregistrée (ni
    SmartFinder.FCMacro lui-même). Ne descend pas dans les sous-dossiers
    (modules internes des macros métier).

    Returns:
        Liste de dicts {"name": str, "macro": str}, triée par nom.
    """
    try:
        import FreeCAD
        macro_dir = FreeCAD.getUserMacroDir(True)
    except Exception:
        return []

    if not macro_dir or not os.path.isdir(macro_dir):
        return []

    def _norm(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))

    registered = {_norm(f["macro"]) for f in families if f.get("macro")}
    self_path  = _norm(os.path.join(macro_dir, "SmartFinder.FCMacro"))

    try:
        entries = os.listdir(macro_dir)
    except OSError:
        return []

    results = []
    for entry in entries:
        if not entry.lower().endswith((".py", ".fcmacro")):
            continue
        full = os.path.join(macro_dir, entry)
        if not os.path.isfile(full):
            continue
        norm = _norm(full)
        if norm in registered or norm == self_path:
            continue
        results.append({"name": entry, "macro": full})

    results.sort(key=lambda d: d["name"].lower())
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  Validation interne
# ─────────────────────────────────────────────────────────────────────────────

def _is_valid(family: dict) -> bool:
    return (
        isinstance(family, dict)
        and bool(family.get("name"))
        and bool(family.get("property"))
        and bool(family.get("macro"))
    )
