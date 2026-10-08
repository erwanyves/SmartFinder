# -*- coding: utf-8 -*-
"""
detector.py — Détection de la famille d'un composant FreeCAD sélectionné.

Deux mécanismes de détection, indépendants et complémentaires :

  1. Reconnaissance d'un COMPOSANT EXISTANT (édition), par propriété
     identifiante : `get_selected_component()` / `detect_all_families()`.
       1 famille détectée  → lancement direct, sans dialogue.
       0 famille           → dialogue, aucune pré-sélection.
       N familles (ambigu) → dialogue, bandeau orange, choix manuel.

  2. Classification du TYPE GÉOMÉTRIQUE BRUT de la sélection (création),
     par `classify_selection_geometry()` — utilisé pour filtrer quelles
     familles déclarent savoir se positionner sur ce type d'élément
     (`detection_modes` de chaque famille), indépendamment de toute
     reconnaissance de composant existant. Voir controller.py pour
     l'articulation des deux mécanismes.
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
#  Résolution sélection → composant parent
#
#  Logique dupliquée indépendamment dans chaque macro (aucun module partagé
#  entre macros — voir doc d'audit) : remonter d'un sous-élément sélectionné
#  (face, arête, feature interne à un PartDesign::Body...) vers son composant
#  racine, de façon à détecter la famille même quand l'utilisateur clique sur
#  un élément du composant dans la vue 3D plutôt que sur l'objet dans l'arbre.
# ─────────────────────────────────────────────────────────────────────────────

def resolve_selected_component(obj, marker_check=None, max_depth: int = 8):
    """Remonte de `obj` vers son composant parent, en essayant successivement :
    l'objet lui-même, `_Body` (feature interne à un PartDesign::Body),
    le premier parent `InList` de type Body/Part, `getParentGeoFeatureGroup()`,
    puis un éventuel `LinkedObject` (App::Link) — et recommence depuis là.

    Args:
        obj:           objet FreeCAD de départ (peut être None).
        marker_check:  fonction obj -> bool ; si fournie, la remontée s'arrête
                        dès qu'un objet la satisfait, et None est retourné si
                        aucun objet rencontré ne la satisfait.
        max_depth:     garde-fou contre une boucle de parenté anormale.

    Returns:
        L'objet trouvé (satisfaisant `marker_check` si fourni), sinon :
          - None si `marker_check` est fourni et n'a jamais été satisfait ;
          - `obj` tel quel si aucun `marker_check` n'est fourni.
    """
    if obj is None:
        return None

    def _matches(o) -> bool:
        return marker_check is None or (o is not None and marker_check(o))

    seen: set = set()
    current = obj
    depth = 0

    while current is not None and depth < max_depth:
        key = (getattr(current, "Document", None) and current.Document.Name,
               getattr(current, "Name", id(current)))
        if key in seen:
            break
        seen.add(key)
        depth += 1

        if _matches(current):
            return current

        next_candidate = None

        # 1. _Body : feature interne → son PartDesign::Body
        body = getattr(current, "_Body", None)
        if body is not None and body is not current:
            if _matches(body):
                return body
            next_candidate = body

        # 2. InList : premier parent de type Body/Part
        if next_candidate is None:
            try:
                for parent in getattr(current, "InList", []) or []:
                    if getattr(parent, "TypeId", "") in ("PartDesign::Body", "App::Part"):
                        if _matches(parent):
                            return parent
                        next_candidate = parent
                        break
            except Exception:
                pass

        # 3. getParentGeoFeatureGroup() : conteneur App::Part le cas échéant
        if next_candidate is None:
            try:
                group = current.getParentGeoFeatureGroup()
            except Exception:
                group = None
            if group is not None and group is not current:
                if _matches(group):
                    return group
                next_candidate = group

        # 4. App::Link : continuer la remontée sur l'objet lié
        if next_candidate is None:
            linked = getattr(current, "LinkedObject", None)
            if linked is not None and linked is not current:
                if _matches(linked):
                    return linked
                next_candidate = linked

        if next_candidate is None:
            break
        current = next_candidate

    return None if marker_check is not None else obj


def get_selected_component(families: list):
    """Retourne l'objet sélectionné, remonté si besoin vers le premier
    composant parent qui porte une des propriétés identifiantes de `families`.

    À utiliser à la place de `get_selected_object()` seul quand on cherche à
    détecter une famille : couvre le cas où l'utilisateur a sélectionné une
    face/arête du composant dans la vue 3D plutôt que l'objet racine.
    """
    obj = get_selected_object()
    if obj is None or not families:
        return obj

    # CORRECTIF (01/09/2026) : un LCS sélectionné directement, ou une de ses
    # branches d'axe (App::Line) cliquée en vue 3D, ne doit JAMAIS être
    # remonté automatiquement vers le composant existant qui le porte — même
    # principe déjà appliqué dans SpringFull.FCMacro::getSelectedSpringBody()
    # et StandardPartSelector/sc_props.py::_resolve_selected_sc_component()
    # (Chantier 10 et son addendum, cf. audit_correctif_lcs_typeid.md) : un
    # LCS sert de repère de positionnement pour un NOUVEAU composant, jamais
    # de raccourci silencieux vers l'édition du composant qui le porte.
    #
    # Sans ce test, sélectionner le LCS Local_Top/Local_Bottom d'un ressort
    # déjà présent dans le document était reconnu ici via `_Body` (une
    # feature PartDesign porte cet attribut, résolu en un seul saut par
    # resolve_selected_component ci-dessous) — l'axe A (reconnaissance d'un
    # composant existant) trouvait alors directement le ressort et
    # court-circuitait systématiquement l'axe B (classify_selection_geometry
    # / filtrage par `detection_modes`), qui aurait dû laisser le choix
    # entre TOUTES les familles déclarant accepter le mode "lcs" (Spring ET
    # StandardPartSelector) plutôt que de ne jamais proposer que Spring.
    type_id = getattr(obj, "TypeId", None)
    if type_id in _LCS_TYPES:
        return obj
    if type_id == "App::Line" and _resolve_lcs_from_axis_branch(obj) is not None:
        return obj

    props = {f["property"] for f in families if f.get("property")}
    if not props:
        return obj

    def _marker(o) -> bool:
        try:
            return bool(props.intersection(o.PropertiesList))
        except Exception:
            return False

    resolved = resolve_selected_component(obj, marker_check=_marker)
    return resolved if resolved is not None else obj


# ─────────────────────────────────────────────────────────────────────────────
#  Classification du type géométrique brut de la sélection (modes de
#  détection, pour une CRÉATION — indépendant de la reconnaissance d'un
#  composant existant ci-dessus)
# ─────────────────────────────────────────────────────────────────────────────

DM_BODY_PART: str = "body_part"
DM_ARC_CIRCLE: str = "arc_circle"
DM_LCS: str = "lcs"

ALL_DETECTION_MODES: tuple = (DM_BODY_PART, DM_ARC_CIRCLE, DM_LCS)

# Types LCS reconnus — copie indépendante du même tuple déjà validé dans
# SpringFull.FCMacro et StandardPartSelector/geometry.py (Chantier 10 et son
# addendum, cf. audit_correctif_lcs_typeid.md / audit_correctif_lcs_axe_precis.md).
_LCS_TYPES = (
    "PartDesign::CoordinateSystem",
    "PartDesign::LocalCoordinateSystem",
    "Part::LocalCoordinateSystem",
)

_BODY_PART_TYPES = ("PartDesign::Body", "App::Part")


def _resolve_lcs_from_axis_branch(obj, max_depth: int = 6):
    """Si `obj` est une branche d'axe (`App::Line`, ex. `X_Axis013`) d'un LCS
    cliquée en vue 3D, remonte via `InList` (App::Line → App::Origin → LCS)
    et retourne le LCS trouvé, ou None si `obj` n'en est pas une, ou si aucun
    ancêtre LCS n'est trouvé dans la limite de profondeur.

    Réplique le mécanisme validé côté SpringFull/StandardPartSelector
    (addendum « axe précis », 24/08/2026).
    """
    if obj is None or getattr(obj, "TypeId", "") != "App::Line":
        return None

    seen: set = set()
    current = obj
    depth = 0

    while current is not None and depth < max_depth:
        key = id(current)
        if key in seen:
            break
        seen.add(key)
        depth += 1

        try:
            parents = getattr(current, "InList", []) or []
        except Exception:
            parents = []

        next_candidate = None
        for parent in parents:
            if getattr(parent, "TypeId", "") in _LCS_TYPES:
                return parent
            next_candidate = parent
            break

        if next_candidate is None:
            break
        current = next_candidate

    return None


def _is_circular_subelement(sub) -> bool:
    """True si le sous-objet géométrique `sub` (Part.Edge ou Part.Face,
    obtenu via `SelectionObject.SubObjects`) est circulaire : arête
    circulaire (`Curve.Radius`) ou face cylindrique/conique (`Surface.Radius`).
    Même heuristique que `StandardPartSelector/geometry.py`.
    """
    if sub is None:
        return False
    curve = getattr(sub, "Curve", None)
    if curve is not None and hasattr(curve, "Radius"):
        return True
    surf = getattr(sub, "Surface", None)
    if surf is not None and hasattr(surf, "Radius"):
        return True
    return False


def classify_selection_geometry():
    """Classe le TYPE géométrique brut de la sélection FreeCAD courante —
    à ne pas confondre avec `get_selected_component()` / `detect_all_families()`
    qui cherchent à reconnaître un composant déjà créé.

    Returns:
        - `DM_BODY_PART`  si un `PartDesign::Body` / `App::Part` est
          sélectionné directement (aucun sous-élément ciblé) ;
        - `DM_ARC_CIRCLE` si le sous-élément cliqué en vue 3D (face ou
          arête) est circulaire ;
        - `DM_LCS`        si un LCS, ou une branche d'axe précise (X/Y/Z)
          d'un LCS, est sélectionné ;
        - `"surface_geometry"` si un sous-élément non circulaire (face,
          arête) est sélectionné — ce cas n'est volontairement pas un mode
          déclarable par les familles (voir spec 25/08/2026) ; il sert
          uniquement à distinguer explicitement ce cas de « rien de
          reconnu » pour le contrôleur ;
        - `None` si rien n'est sélectionné ou si le type n'est pas reconnu.
    """
    try:
        sel_ex = FreeCAD.Gui.Selection.getSelectionEx()
    except Exception:
        return None
    if not sel_ex:
        return None

    entry     = sel_ex[0]
    obj       = entry.Object
    sub_names = entry.SubElementNames or ()

    if sub_names:
        # CORRECTIF PORTÉ (01/09/2026) depuis StandardPartSelector/geometry.py
        # (correctif du 31/08-01/09/2026, non porté initialement lors de sa
        # livraison — voir claude/audit_macros_freecad_2026-09-01.md §1.1) :
        # pour un LCS 'PartDesign::CoordinateSystem', cliquer sur une flèche
        # d'axe en vue 3D ne crée pas d'objet séparé — `obj` reste le LCS
        # lui-même, et l'axe cliqué apparaît ici comme un sous-élément
        # 'X'/'Y'/'Z'. Sans ce test, ce cas tombait dans la branche générique
        # ci-dessous et était classé à tort "surface_geometry" au lieu de
        # DM_LCS, empêchant le filtrage par mode de détection de reconnaître
        # ce cas comme un repère.
        if getattr(obj, "TypeId", "") in _LCS_TYPES and sub_names[0] in ("X", "Y", "Z"):
            return DM_LCS
        # Sous-élément précis cliqué en vue 3D (face, arête...).
        try:
            sub = entry.SubObjects[0]
        except Exception:
            sub = None
        return DM_ARC_CIRCLE if _is_circular_subelement(sub) else "surface_geometry"

    # Pas de sous-élément : sélection de l'objet lui-même (arbre, ou clic
    # direct sur un objet sans face/arête ciblée).
    type_id = getattr(obj, "TypeId", "")

    if type_id in _BODY_PART_TYPES:
        return DM_BODY_PART

    if type_id in _LCS_TYPES:
        return DM_LCS

    if type_id == "App::Line" and _resolve_lcs_from_axis_branch(obj) is not None:
        return DM_LCS

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
