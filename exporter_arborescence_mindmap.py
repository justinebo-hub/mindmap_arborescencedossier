"""
exporter_arborescence_mindmap.py
---------------------------------
Génère une mindmap à partir de l'arborescence de dossiers (et optionnellement
des fichiers) d'un répertoire choisi par l'utilisateur.

Formats de sortie disponibles (cumulables) :
  - .html    HTML interactif Markmap  → navigateur web
  - .mm      FreeMind XML             → Freeplane, FreeMind, XMind (import)
  - .drawio  mxGraph XML              → draw.io / diagrams.net
  - .opml    OPML XML                 → XMind, MindManager, Logseq, Obsidian…
  - .md      Mermaid Markdown         → GitHub, GitLab, Notion, VS Code…
  - .xmind   XMind JSON/ZIP           → XMind

Dépendances : bibliothèque standard Python uniquement
              (os, xml, json, zipfile, tkinter, webbrowser)
"""
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Justine Bouwy-Ounnough

import json
import os
import uuid
import webbrowser
import zipfile
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox

# ── Paramètres ──────────────────────────────────────────────────────────────

PROFONDEUR_MAX = 5
DOSSIERS_EXCLUS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "$RECYCLE.BIN", "System Volume Information",
}
# Extensions système/techniques toujours exclues (quelles que soient les options)
EXTENSIONS_SYSTEME = {
    ".tmp", ".lnk", ".ini", ".db", ".DS_Store", ".thumbs",
    ".bak", ".log", ".exe", ".dll", ".sys", ".pyc",
}

# Catégories de fichiers proposées dans la boîte de dialogue.
# Chaque catégorie peut être cochée/décochée indépendamment.
# La catégorie spéciale "autres" capture tout ce qui n'appartient
# à aucune des catégories listées ici.
CATEGORIES_FICHIERS: dict[str, set[str]] = {
    "Documents bureautiques": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".ppt", ".pptx", ".odt", ".ods", ".odp",
    },
    "Texte & données": {
        ".txt", ".md", ".rst", ".csv", ".json", ".xml",
        ".yaml", ".yml", ".toml",
    },
    "Images": {
        ".png", ".jpg", ".jpeg", ".gif", ".svg",
        ".bmp", ".tiff", ".webp",
    },
    "Code source": {
        ".py", ".js", ".ts", ".html", ".css", ".r",
        ".java", ".cpp", ".c", ".sh", ".bat",
    },
    "Archives": {
        ".zip", ".tar", ".gz", ".7z", ".rar",
    },
}

# Sentinel : signifie "afficher tous les fichiers hors EXTENSIONS_SYSTEME"
# (distinct de None qui signifie "aucun fichier")
TOUTES_EXTENSIONS: frozenset[str] = frozenset({"*"})

# Métadonnées des formats (boîte de dialogue + récapitulatif final)
FORMATS = [
    {
        "cle": "html", "ext": ".html", "icone": "🌐",
        "libelle": "HTML interactif  (Markmap)",
        "ouvre_dans": "Navigateur web  —  Chrome, Firefox, Edge…",
    },
    {
        "cle": "mm", "ext": ".mm", "icone": "🧠",
        "libelle": "FreeMind / Freeplane  (.mm)",
        "ouvre_dans": "Freeplane, FreeMind  •  import possible dans XMind",
    },
    {
        "cle": "drawio", "ext": ".drawio", "icone": "📐",
        "libelle": "draw.io / diagrams.net  (.drawio)",
        "ouvre_dans": "draw.io (app.diagrams.net ou application desktop)",
    },
    {
        "cle": "opml", "ext": ".opml", "icone": "🔀",
        "libelle": "OPML  (format pivot universel)",
        "ouvre_dans": "XMind, MindManager, Logseq, Obsidian, OmniOutliner…",
    },
    {
        "cle": "mermaid", "ext": ".md", "icone": "📄",
        "libelle": "Mermaid Markdown  (.md)",
        "ouvre_dans": "GitHub, GitLab, Notion, VS Code (extension Mermaid)…",
    },
    {
        "cle": "xmind", "ext": ".xmind", "icone": "✳️",
        "libelle": "XMind  (.xmind)",
        "ouvre_dans": "XMind (version 2020 et ultérieure)",
    },
]

# ── Utilitaires communs ──────────────────────────────────────────────────────

def lister_sous_dossiers(chemin: str) -> list[str]:
    """Retourne les sous-dossiers triés d'un répertoire (PermissionError ignorée)."""
    try:
        return sorted(
            e for e in os.listdir(chemin)
            if os.path.isdir(os.path.join(chemin, e))
            and e not in DOSSIERS_EXCLUS
            and not e.startswith(".")
        )
    except PermissionError:
        return []


def lister_fichiers(chemin: str,
                    extensions_autorisees: frozenset[str]) -> list[str]:
    """
    Retourne les fichiers triés d'un répertoire selon le filtre d'extensions.

    Args:
        chemin: répertoire à lister.
        extensions_autorisees: extensions à afficher (casse basse, avec point).
            Passer TOUTES_EXTENSIONS pour afficher tout sauf EXTENSIONS_SYSTEME.
            Un frozenset vide retourne une liste vide.
    """
    try:
        resultat = []
        for entree in sorted(os.listdir(chemin)):
            if entree.startswith("."):
                continue
            if not os.path.isfile(os.path.join(chemin, entree)):
                continue
            ext = os.path.splitext(entree)[1].lower()
            if ext in EXTENSIONS_SYSTEME:
                continue
            if (extensions_autorisees is not TOUTES_EXTENSIONS
                    and ext not in extensions_autorisees):
                continue
            resultat.append(entree)
        return resultat
    except PermissionError:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 1 — HTML (Markmap)
# ══════════════════════════════════════════════════════════════════════════════

def construire_markdown(chemin_racine: str,
                        extensions_fichiers: frozenset[str] | None) -> list[str]:
    """Parcourt l'arborescence et retourne les lignes Markdown pour Markmap.

    Args:
        chemin_racine: répertoire racine à cartographier.
        extensions_fichiers: filtre d'extensions (None = tous sauf système).
    """
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    lignes = [f"# 📁 {nom_racine}"]

    def parcourir(chemin: str, niveau: int) -> None:
        if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
            return
        indent = "  " * niveau
        for dossier in lister_sous_dossiers(chemin):
            lignes.append(f"{indent}- 📂 {dossier}")
            parcourir(os.path.join(chemin, dossier), niveau + 1)
        if extensions_fichiers is not None:
            for fichier in lister_fichiers(chemin, extensions_fichiers):
                lignes.append(f"{indent}- 📄 {fichier}")

    parcourir(chemin_racine, 1)
    return lignes


TEMPLATE_HTML = """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mindmap – {titre}</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Segoe UI, sans-serif; background: #f4f6fb; }}
    header {{
      background: #1a3a5c; color: white;
      padding: 12px 20px; font-size: 1rem;
      display: flex; align-items: center; gap: 10px;
    }}
    header span {{ opacity: .7; font-size: .85rem; }}
    #mindmap {{ width: 100vw; height: calc(100vh - 48px); }}
  </style>
</head>
<body>
  <header>🗂️ Mindmap arborescence &nbsp;<span>{titre}</span></header>
  <svg id="mindmap"></svg>
  <script>
    const markdown = `{markdown}`;
    const {{ Transformer }} = window.markmap;
    const transformer = new Transformer();
    const {{ root, features }} = transformer.transform(markdown);
    const {{ styles, scripts }} = transformer.getUsedAssets(features);
    const {{ Markmap, loadCSS, loadJS }} = window.markmap;
    if (styles) loadCSS(styles);
    if (scripts) loadJS(scripts, {{ getMarkmap: () => window.markmap }});

    const COULEUR_RACINE  = "#0A0096";
    const COULEUR_NIVEAU1 = "#0082FF";
    const PALETTE_NIVEAU2 = ["#FFAF96", "#FF735F", "#AFE1FA", "#0082FF", "#0A0096"];

    function couleurAleatoire() {{
      return "#" + Math.floor(Math.random() * 0xFFFFFF).toString(16).padStart(6, "0");
    }}
    const nodeColors = new WeakMap();
    let paletteIdx = 0;

    function assignerCouleurs(n, couleurHeritee) {{
      if (n.depth === 0) {{
        nodeColors.set(n, COULEUR_RACINE);
        (n.children || []).forEach(e => assignerCouleurs(e, COULEUR_NIVEAU1));
      }} else if (n.depth === 1) {{
        nodeColors.set(n, COULEUR_NIVEAU1);
        (n.children || []).forEach(e => assignerCouleurs(e, null));
      }} else if (n.depth === 2) {{
        const c = paletteIdx < PALETTE_NIVEAU2.length
          ? PALETTE_NIVEAU2[paletteIdx++] : couleurAleatoire();
        nodeColors.set(n, c);
        (n.children || []).forEach(e => assignerCouleurs(e, c));
      }} else {{
        nodeColors.set(n, couleurHeritee);
        (n.children || []).forEach(e => assignerCouleurs(e, couleurHeritee));
      }}
    }}
    assignerCouleurs(root, null);
    Markmap.create("#mindmap", {{
      initialExpandLevel: 2,
      color: (n) => nodeColors.get(n) ?? COULEUR_NIVEAU1,
    }}, root);
  </script>
</body>
</html>
"""


def exporter_html(chemin_racine: str, chemin_sortie: str,
                  extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier HTML interactif (Markmap)."""
    lignes_md = construire_markdown(chemin_racine, extensions_fichiers)
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    md_echappe = "\n".join(lignes_md).replace("`", "\\`").replace("$", "\\$")
    contenu = TEMPLATE_HTML.format(titre=nom_racine, markdown=md_echappe)
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(contenu)
    print(f"HTML     : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 2 — FreeMind / Freeplane (.mm)
# ══════════════════════════════════════════════════════════════════════════════

def exporter_mm(chemin_racine: str, chemin_sortie: str,
                extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier FreeMind/Freeplane (.mm)."""
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    racine_xml = ET.Element("map", version="1.0.1")
    noeud_racine = ET.SubElement(racine_xml, "node", TEXT=nom_racine, FOLDED="false")

    def parcourir(parent_xml: ET.Element, chemin: str, niveau: int) -> None:
        if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
            return
        for dossier in lister_sous_dossiers(chemin):
            attrs = {
                "TEXT": dossier,
                "FOLDED": "true" if niveau >= 2 else "false",
            }
            if niveau == 1:
                attrs["POSITION"] = "right"
            enfant_xml = ET.SubElement(parent_xml, "node", **attrs)
            parcourir(enfant_xml, os.path.join(chemin, dossier), niveau + 1)
        if extensions_fichiers is not None:
            for fichier in lister_fichiers(chemin, extensions_fichiers):
                ET.SubElement(parent_xml, "node", TEXT=fichier, FOLDED="false")

    parcourir(noeud_racine, chemin_racine, 1)
    ET.indent(racine_xml, space="  ")
    ET.ElementTree(racine_xml).write(
        chemin_sortie, xml_declaration=True, encoding="unicode"
    )
    print(f".mm      : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 3 — draw.io (.drawio)
# ══════════════════════════════════════════════════════════════════════════════

_NODE_W, _NODE_H, _GAP_X, _GAP_Y = 160, 40, 80, 20


class _NoeudDrawio:
    """Nœud interne pour le calcul de layout du diagramme draw.io."""

    _compteur = 2   # 0 et 1 sont réservés par mxGraph

    @classmethod
    def reinitialiser_compteur(cls) -> None:
        """Réinitialise le compteur d'ID avant chaque export draw.io."""
        cls._compteur = 2

    def __init__(self, label: str, parent: "_NoeudDrawio | None",
                 est_fichier: bool = False):
        self.id = _NoeudDrawio._compteur
        _NoeudDrawio._compteur += 1
        self.label = label
        self.parent = parent
        self.est_fichier = est_fichier
        self.enfants: list["_NoeudDrawio"] = []
        self.x = self.y = 0.0

    def est_feuille(self) -> bool:
        """Retourne True si le nœud n'a aucun enfant."""
        return not self.enfants

    def profondeur(self) -> int:
        """Calcule la profondeur du nœud en remontant vers la racine."""
        d, n = 0, self
        while n.parent:
            d += 1
            n = n.parent
        return d


def _construire_arbre_drawio(chemin_racine: str,
                              extensions_fichiers: frozenset[str] | None
                              ) -> _NoeudDrawio:
    """Construit l'arbre de nœuds _NoeudDrawio à partir du système de fichiers."""
    _NoeudDrawio.reinitialiser_compteur()
    racine = _NoeudDrawio(os.path.basename(chemin_racine) or chemin_racine, None)

    def parcourir(noeud: _NoeudDrawio, chemin: str, niveau: int) -> None:
        if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
            return
        for dossier in lister_sous_dossiers(chemin):
            enfant = _NoeudDrawio(dossier, noeud, est_fichier=False)
            noeud.enfants.append(enfant)
            parcourir(enfant, os.path.join(chemin, dossier), niveau + 1)
        if extensions_fichiers is not None:
            for fichier in lister_fichiers(chemin, extensions_fichiers):
                noeud.enfants.append(_NoeudDrawio(fichier, noeud, est_fichier=True))

    parcourir(racine, chemin_racine, 1)
    return racine


def _assigner_positions(noeud: _NoeudDrawio, x: float, y_debut: float) -> float:
    """Positionne récursivement chaque nœud ; retourne le y_fin du sous-arbre."""
    noeud.x = x
    if noeud.est_feuille():
        noeud.y = y_debut
        return y_debut + _NODE_H + _GAP_Y
    y_courant = y_debut
    premiers_y = []
    for enfant in noeud.enfants:
        premiers_y.append(y_courant)
        y_courant = _assigner_positions(enfant, x + _NODE_W + _GAP_X, y_courant)
    noeud.y = (premiers_y[0] + (y_courant - _GAP_Y - _NODE_H)) / 2
    return y_courant


def _style_drawio(profondeur: int, est_fichier: bool) -> str:
    """Retourne le style mxGraph selon la profondeur et le type du nœud."""
    if est_fichier:
        return (
            "shape=mxgraph.floorplan.area;whiteSpace=wrap;html=1;"
            "fillColor=#f5f5f5;fontColor=#333333;strokeColor=#999999;"
        )
    if profondeur == 0:
        return (
            "rounded=1;whiteSpace=wrap;html=1;"
            "fillColor=#0A0096;fontColor=#ffffff;strokeColor=#0A0096;"
            "fontStyle=1;fontSize=13;"
        )
    if profondeur == 1:
        return (
            "rounded=1;whiteSpace=wrap;html=1;"
            "fillColor=#0082FF;fontColor=#ffffff;strokeColor=#0082FF;"
            "fontStyle=1;"
        )
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        "fillColor=#AFE1FA;fontColor=#000000;strokeColor=#0082FF;"
    )


def exporter_drawio(chemin_racine: str, chemin_sortie: str,
                    extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier draw.io (.drawio) avec layout arborescent."""
    racine = _construire_arbre_drawio(chemin_racine, extensions_fichiers)
    _assigner_positions(racine, 0, 0)

    file_bfs: list[_NoeudDrawio] = [racine]
    tous: list[_NoeudDrawio] = []
    while file_bfs:
        noeud = file_bfs.pop(0)
        tous.append(noeud)
        file_bfs.extend(noeud.enfants)

    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", name="Mindmap")
    model = ET.SubElement(diagram, "mxGraphModel",
                          grid="0", guides="1", tooltips="1",
                          connect="1", arrows="1", fold="1", page="0",
                          pageScale="1", pageWidth="1169", pageHeight="827",
                          math="0", shadow="0")
    root_xml = ET.SubElement(model, "root")
    ET.SubElement(root_xml, "mxCell", id="0")
    ET.SubElement(root_xml, "mxCell", id="1", parent="0")

    for noeud in tous:
        style = _style_drawio(noeud.profondeur(), noeud.est_fichier)
        cell = ET.SubElement(root_xml, "mxCell",
                             id=str(noeud.id), value=noeud.label,
                             style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry",
                      x=str(round(noeud.x)), y=str(round(noeud.y)),
                      width=str(_NODE_W), height=str(_NODE_H),
                      **{"as": "geometry"})
        if noeud.parent:
            edge = ET.SubElement(root_xml, "mxCell",
                                 id=f"e{noeud.id}",
                                 style="edgeStyle=orthogonalEdgeStyle;rounded=0;",
                                 edge="1", source=str(noeud.parent.id),
                                 target=str(noeud.id), parent="1")
            ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})

    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(
        chemin_sortie, xml_declaration=True, encoding="unicode"
    )
    print(f".drawio  : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 4 — OPML
# ══════════════════════════════════════════════════════════════════════════════

def exporter_opml(chemin_racine: str, chemin_sortie: str,
                  extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier OPML (format pivot universel)."""
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = f"Arborescence – {nom_racine}"
    body = ET.SubElement(opml, "body")
    noeud_racine = ET.SubElement(body, "outline", text=nom_racine)

    def parcourir(parent_xml: ET.Element, chemin: str, niveau: int) -> None:
        if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
            return
        for dossier in lister_sous_dossiers(chemin):
            enfant_xml = ET.SubElement(parent_xml, "outline", text=dossier)
            parcourir(enfant_xml, os.path.join(chemin, dossier), niveau + 1)
        if extensions_fichiers is not None:
            for fichier in lister_fichiers(chemin, extensions_fichiers):
                ET.SubElement(parent_xml, "outline",
                               text=fichier, type="fichier")

    parcourir(noeud_racine, chemin_racine, 1)
    ET.indent(opml, space="  ")
    ET.ElementTree(opml).write(
        chemin_sortie, xml_declaration=True, encoding="unicode"
    )
    print(f".opml    : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 5 — Mermaid Markdown (.md)
# ══════════════════════════════════════════════════════════════════════════════

def exporter_mermaid(chemin_racine: str, chemin_sortie: str,
                     extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier Markdown avec bloc Mermaid mindmap."""
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    lignes = [f"# {nom_racine}", "", "```mermaid", "mindmap",
              f"  root(({nom_racine}))"]

    def echapper(texte: str) -> str:
        """Supprime les caractères posant problème dans la syntaxe Mermaid."""
        return texte.replace('"', "'").replace("(", "[").replace(")", "]")

    def parcourir(chemin: str, niveau: int) -> None:
        if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
            return
        indent = "  " * (niveau + 1)
        for dossier in lister_sous_dossiers(chemin):
            lignes.append(f"{indent}{echapper(dossier)}")
            parcourir(os.path.join(chemin, dossier), niveau + 1)
        if extensions_fichiers is not None:
            for fichier in lister_fichiers(chemin, extensions_fichiers):
                lignes.append(f"{indent}{echapper(fichier)}")

    parcourir(chemin_racine, 1)
    lignes.append("```")
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
    print(f".md      : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMAT 6 — XMind (.xmind)
# ══════════════════════════════════════════════════════════════════════════════

def _construire_topic_xmind(chemin: str, label: str, niveau: int,
                             extensions_fichiers: frozenset[str] | None) -> dict:
    """Construit récursivement un topic XMind (dict JSON)."""
    topic: dict = {"id": str(uuid.uuid4()), "class": "topic", "title": label}
    if PROFONDEUR_MAX and niveau > PROFONDEUR_MAX:
        return topic

    sous_dossiers = lister_sous_dossiers(chemin)
    fichiers = (
        lister_fichiers(chemin, extensions_fichiers)
        if extensions_fichiers is not None else []
    )
    enfants = [
        _construire_topic_xmind(
            os.path.join(chemin, d), d, niveau + 1, extensions_fichiers
        )
        for d in sous_dossiers
    ] + [
        {"id": str(uuid.uuid4()), "class": "topic", "title": f}
        for f in fichiers
    ]
    if enfants:
        topic["children"] = {"attached": enfants}
    return topic


def exporter_xmind(chemin_racine: str, chemin_sortie: str,
                   extensions_fichiers: frozenset[str] | None) -> None:
    """Génère et enregistre le fichier XMind (.xmind, ZIP JSON)."""
    nom_racine = os.path.basename(chemin_racine) or chemin_racine
    root_topic = _construire_topic_xmind(
        chemin_racine, nom_racine, 1, extensions_fichiers
    )
    content = [{
        "id": str(uuid.uuid4()), "class": "sheet",
        "title": "Sheet 1", "rootTopic": root_topic,
    }]
    metadata = {"creator": {"name": "exporter_arborescence_mindmap", "version": "1.1"}}
    with zipfile.ZipFile(chemin_sortie, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json",
                    json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json",
                    json.dumps(metadata, ensure_ascii=False))
    print(f".xmind   : {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════════════════
# Boîte de dialogue — sélection des formats et options
# ══════════════════════════════════════════════════════════════════════════════

# Icônes associées à chaque catégorie de fichiers
_ICONES_CATEGORIES: dict[str, str] = {
    "Documents bureautiques": "📑",
    "Texte & données":        "📝",
    "Images":                 "🖼️",
    "Code source":            "💻",
    "Archives":               "📦",
}


def _creer_section_formats(
        fenetre: tk.Toplevel,
) -> dict[str, tk.BooleanVar]:
    """
    Crée la section des cases à cocher de formats dans la fenêtre.

    Retourne le dict {clé_format: BooleanVar}.
    """
    tk.Label(fenetre, text="Formats à générer :",
             font=("Segoe UI", 10, "bold"), pady=8
             ).grid(row=0, column=0, columnspan=2, padx=20, sticky="w")
    tk.Label(fenetre, text="S'ouvre dans…",
             font=("Segoe UI", 9, "italic"), fg="#666666"
             ).grid(row=0, column=2, padx=(0, 20), sticky="e")

    vars_fmt: dict[str, tk.BooleanVar] = {}
    for i, fmt in enumerate(FORMATS, start=1):
        var = tk.BooleanVar(value=True)
        vars_fmt[fmt["cle"]] = var
        tk.Checkbutton(fenetre,
                       text=f"{fmt['icone']}  {fmt['libelle']}",
                       variable=var, font=("Segoe UI", 10), anchor="w"
                       ).grid(row=i, column=0, columnspan=2,
                               padx=24, pady=2, sticky="w")
        tk.Label(fenetre, text=fmt["ouvre_dans"],
                 font=("Segoe UI", 9), fg="#0082FF"
                 ).grid(row=i, column=2, padx=(0, 24), pady=2, sticky="w")
    return vars_fmt


def _creer_section_fichiers(
        fenetre: tk.Toplevel, row_debut: int,
) -> tuple[tk.BooleanVar, dict[str, tk.BooleanVar], tk.BooleanVar]:
    """
    Crée la section "Inclure les fichiers" avec ses catégories.

    Retourne (var_fichiers, vars_cats, var_autres).
    """
    var_fichiers = tk.BooleanVar(value=False)
    tk.Checkbutton(fenetre,
                   text="📄  Inclure les fichiers dans la mindmap",
                   variable=var_fichiers,
                   font=("Segoe UI", 10, "bold"), anchor="w"
                   ).grid(row=row_debut, column=0, columnspan=3,
                           padx=24, pady=(2, 0), sticky="w")

    frame_cats = tk.Frame(fenetre)
    frame_cats.grid(row=row_debut + 1, column=0, columnspan=3,
                    padx=44, pady=(2, 4), sticky="w")

    vars_cats: dict[str, tk.BooleanVar] = {}
    for row_c, nom_cat in enumerate(CATEGORIES_FICHIERS):
        var_c = tk.BooleanVar(value=True)
        vars_cats[nom_cat] = var_c
        icone = _ICONES_CATEGORIES.get(nom_cat, "•")
        tk.Checkbutton(frame_cats, text=f"{icone} {nom_cat}",
                       variable=var_c, font=("Segoe UI", 9), anchor="w"
                       ).grid(row=row_c, column=0, sticky="w", pady=1)

    var_autres = tk.BooleanVar(value=False)
    tk.Checkbutton(frame_cats,
                   text="❓ Autres formats  (tout ce qui ne correspond "
                        "à aucune catégorie ci-dessus)",
                   variable=var_autres,
                   font=("Segoe UI", 9, "italic"), anchor="w"
                   ).grid(row=len(CATEGORIES_FICHIERS), column=0,
                           sticky="w", pady=(4, 1))
    tk.Label(frame_cats,
             text=f"Toujours exclus : {', '.join(sorted(EXTENSIONS_SYSTEME))}",
             font=("Segoe UI", 8), fg="#999999"
             ).grid(row=len(CATEGORIES_FICHIERS) + 1, column=0,
                    sticky="w", pady=(2, 0))

    def basculer_cats(*_args: object) -> None:
        """Active ou désactive les sous-options selon la case principale."""
        etat = "normal" if var_fichiers.get() else "disabled"
        for widget in frame_cats.winfo_children():
            try:
                widget.configure(state=etat)
            except tk.TclError:
                pass

    var_fichiers.trace_add("write", basculer_cats)
    basculer_cats()
    return var_fichiers, vars_cats, var_autres


def _resoudre_extensions(
        var_fichiers: tk.BooleanVar,
        vars_cats: dict[str, tk.BooleanVar],
        var_autres: tk.BooleanVar,
) -> frozenset[str] | None:
    """
    Calcule le frozenset des extensions à afficher depuis les variables tkinter.

    Retourne None si la case principale est décochée (aucun fichier).
    """
    if not var_fichiers.get():
        return None
    if var_autres.get():
        return TOUTES_EXTENSIONS
    exts: set[str] = set()
    for nom_cat, cat_exts in CATEGORIES_FICHIERS.items():
        if vars_cats[nom_cat].get():
            exts |= cat_exts
    return frozenset(exts)


def demander_formats(
        parent: tk.Tk,
) -> tuple[dict[str, bool], frozenset[str] | None]:
    """
    Fenêtre de sélection des formats et des catégories de fichiers.

    Retourne :
        - dict {clé_format: sélectionné}
        - frozenset des extensions autorisées, ou None si aucun fichier inclus.
    """
    selections: dict[str, bool] = {}
    extensions_choisies: frozenset[str] | None = None
    fenetre = tk.Toplevel(parent)
    fenetre.title("Options d'export")
    fenetre.resizable(False, False)
    fenetre.grab_set()

    vars_fmt = _creer_section_formats(fenetre)

    sep1 = len(FORMATS) + 1
    tk.Frame(fenetre, height=1, bg="#cccccc"
             ).grid(row=sep1, column=0, columnspan=3,
                    sticky="ew", padx=20, pady=8)

    var_fichiers, vars_cats, var_autres = _creer_section_fichiers(
        fenetre, row_debut=sep1 + 1
    )

    sep2 = sep1 + 3
    tk.Frame(fenetre, height=1, bg="#cccccc"
             ).grid(row=sep2, column=0, columnspan=3,
                    sticky="ew", padx=20, pady=8)

    def valider() -> None:
        nonlocal extensions_choisies
        for cle, var in vars_fmt.items():
            selections[cle] = var.get()
        extensions_choisies = _resoudre_extensions(
            var_fichiers, vars_cats, var_autres
        )
        fenetre.destroy()

    tk.Button(fenetre, text="  Générer  ", command=valider,
              font=("Segoe UI", 10, "bold"),
              bg="#0082FF", fg="white", padx=16, pady=6
              ).grid(row=sep2 + 1, column=0, columnspan=3, pady=12)

    parent.wait_window(fenetre)
    return selections, extensions_choisies


# ── Registre des exporteurs ──────────────────────────────────────────────────

EXPORTEURS = {
    "html":    exporter_html,
    "mm":      exporter_mm,
    "drawio":  exporter_drawio,
    "opml":    exporter_opml,
    "mermaid": exporter_mermaid,
    "xmind":   exporter_xmind,
}

# ── Point d'entrée ───────────────────────────────────────────────────────────


def main() -> None:
    """Orchestre la sélection du dossier, des formats et l'export des fichiers."""
    root_tk = tk.Tk()
    root_tk.withdraw()

    chemin = filedialog.askdirectory(
        title="Sélectionnez le dossier racine à cartographier"
    )
    if not chemin:
        messagebox.showinfo("Annulé", "Aucun dossier sélectionné.")
        return

    formats, extensions_fichiers = demander_formats(root_tk)
    if not any(formats.values()):
        messagebox.showinfo("Annulé", "Aucun format sélectionné.")
        return

    dossier_sortie = filedialog.askdirectory(
        title="Choisissez le dossier d'enregistrement des fichiers",
        initialdir=os.path.dirname(os.path.abspath(__file__)),
    )
    if not dossier_sortie:
        messagebox.showinfo("Annulé", "Aucun dossier de destination choisi.")
        return

    nom_base = "mindmap_" + os.path.basename(chemin).replace(" ", "_")
    fichiers_crees: list[tuple[str, str]] = []

    for fmt in FORMATS:
        cle = fmt["cle"]
        if not formats.get(cle):
            continue
        chemin_sortie = os.path.join(dossier_sortie, nom_base + fmt["ext"])
        EXPORTEURS[cle](chemin, chemin_sortie, extensions_fichiers)
        fichiers_crees.append((chemin_sortie, fmt["ouvre_dans"]))

    # ── Récapitulatif ────────────────────────────────────────────────────────
    option_fichiers = "  (fichiers inclus)" if extensions_fichiers is not None else ""
    lignes_recap = [f"Enregistrés dans :\n{dossier_sortie}{option_fichiers}\n"]
    for chemin_fichier, ouvre_dans in fichiers_crees:
        lignes_recap.append(f"📄 {os.path.basename(chemin_fichier)}")
        lignes_recap.append(f"   → {ouvre_dans}")
        lignes_recap.append("")
    messagebox.showinfo(
        f"{len(fichiers_crees)} fichier(s) généré(s)",
        "\n".join(lignes_recap).rstrip()
    )

    if formats.get("html"):
        webbrowser.open(os.path.join(dossier_sortie, nom_base + ".html"))


if __name__ == "__main__":
    main()
    