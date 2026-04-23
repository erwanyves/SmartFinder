# -*- coding: utf-8 -*-
"""
detector.py — Détection de la famille d'un composant FreeCAD sélectionné.

Logique :
  1. Récupération de l'objet actuellement sélectionné.
  2. Inventaire de ses propriétés « non standard » (ajoutées par une macro).
  3. Comparaison avec la propriété identifiante de chaque famille connue.
  4. Si plusieurs familles correspondent (ambiguïté), on retourne None et
     laisse l'utilisateur choisir via le dialogue principal.
"""

from __future__ import annotations

import FreeCAD

# Groupes de propriétés standard de FreeCAD — les propriétés dans ces groupes
# ne sont PAS considérées comme des propriétés personnalisées.
_STANDARD_GROUPS: frozenset[str] = frozenset({
    "",
    "Base",
    "Attachment",
    "Draft",
    "Arch",
    "Component",
    "Drawing",
    "Part Design",
    "Sketcher",
    "Spreadsheet",
    "Link",
    "Visibility",
    "View",
})


# ─────────────────────────────────────────────────────────────────────────────
#  Sélection courante
# ─────────────────────────────────────────────────────────────────────────────

def get_selected_object():
    """Retourne le premier objet sélectionné dans FreeCAD, ou None."""
    try:
        sel = FreeCAD.Gui.Selection.getSelection()
        return sel[0] if sel else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  Inventaire des propriétés personnalisées
# ─────────────────────────────────────────────────────────────────────────────

def get_custom_properties(obj) -> list:
    """Retourne la liste des propriétés non-standard d'un objet FreeCAD.

    Returns:
        Liste de tuples (nom_propriété, groupe, type_id).
        Triée par groupe puis par nom.
    """
    if obj is None:
        return []

    results = []

    for prop in obj.PropertiesList:
        try:
            group   = obj.getGroupOfProperty(prop)
            type_id = obj.getTypeIdOfProperty(prop)
        except Exception:
            continue

        # On exclut les propriétés des groupes standard
        if group in _STANDARD_GROUPS:
            continue

        results.append((prop, group, type_id))

    # Tri : groupe d'abord, puis nom de propriété
    results.sort(key=lambda t: (t[1].lower(), t[0].lower()))
    return results


def get_all_properties(obj) -> list:
    """Retourne TOUTES les propriétés d'un objet (standard + custom).
    Utile si l'utilisateur souhaite cibler une propriété standard.
    """
    if obj is None:
        return []

    results = []
    for prop in obj.PropertiesList:
        try:
            group   = obj.getGroupOfProperty(prop)
            type_id = obj.getTypeIdOfProperty(prop)
        except Exception:
            continue
        results.append((prop, group, type_id))

    results.sort(key=lambda t: (t[1].lower(), t[0].lower()))
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  Détection de famille
# ─────────────────────────────────────────────────────────────────────────────

def detect_all_families(obj, families: list) -> list:
    """Retourne la liste de TOUTES les familles dont la propriété identifiante
    est présente sur l'objet donné.

    Plusieurs résultats = détection ambiguë (propriétés identifiantes
    partagées entre familles) → laisser l'utilisateur trancher.

    Args:
        obj:       objet FreeCAD (peut être None).
        families:  liste de dicts famille chargés depuis families.json.

    Returns:
        Liste (éventuellement vide) de dicts famille correspondants.
    """
    if obj is None or not families:
        return []

    try:
        obj_props = set(obj.PropertiesList)
    except Exception:
        return []

    return [
        f for f in families
        if f.get("property") and f["property"] in obj_props
    ]


def detect_family(obj, families: list):
    """Retourne la famille correspondante uniquement si la détection est
    NON ambiguë (exactement une famille identifiée).

    En cas d'ambiguïté (0 ou 2+ familles), retourne None pour que
    l'utilisateur choisisse lui-même via le dialogue principal.

    Args:
        obj:       objet FreeCAD (peut être None).
        families:  liste de dicts famille chargés depuis families.json.

    Returns:
        Le dict famille si correspondance unique, None sinon.
    """
    matches = detect_all_families(obj, families)
    return matches[0] if len(matches) == 1 else None
