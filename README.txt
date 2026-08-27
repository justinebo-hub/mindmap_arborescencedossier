================================================================================
README — exporter_arborescence_mindmap.py
================================================================================

 Script     : exporter_arborescence_mindmap.py
 Version    : 1.1
 Date       : 26/08/2026
 Auteur     : Justine Bouwy-Ounnough
 Contact    : justine.bwounnough@gmail.com

--------------------------------------------------------------------------------
DESCRIPTION
--------------------------------------------------------------------------------
Script Python générant une mindmap à partir de l'arborescence de dossiers
(et optionnellement des fichiers) d'un répertoire choisi par l'utilisateur.

L'export est multi-format : jusqu'à six fichiers peuvent être produits
simultanément à partir d'un même dossier source. Le script est entièrement
autonome (bibliothèque standard Python uniquement, aucune installation
de paquet tiers requise).


--------------------------------------------------------------------------------
UTILISATION
--------------------------------------------------------------------------------
  python exporter_arborescence_mindmap.py

Le script ouvre trois boîtes de dialogue successives :

  1. Sélection du dossier racine à cartographier.

  2. Sélection des options d'export :
       - Formats à générer (cases à cocher, tous cochés par défaut).
       - Option "Inclure les fichiers" (décochée par défaut) avec sélection
         par catégorie :
           📑 Documents bureautiques   .pdf .doc .docx .xls .xlsx .ppt .pptx…
           📝 Texte & données          .txt .md .csv .json .xml .yaml…
           🖼️ Images                   .png .jpg .jpeg .gif .svg .bmp…
           💻 Code source              .py .js .ts .html .r .java .bat…
           📦 Archives                 .zip .tar .gz .7z .rar
           ❓ Autres formats           tout ce qui ne correspond à aucune
                                       catégorie ci-dessus (catch-all)

  3. Sélection du dossier d'enregistrement des fichiers générés.

En fin d'exécution, une fenêtre récapitule les fichiers créés avec l'outil
recommandé pour chaque format. Le fichier HTML, s'il a été généré, s'ouvre
automatiquement dans le navigateur par défaut.


--------------------------------------------------------------------------------
FORMATS DE SORTIE
--------------------------------------------------------------------------------
  Format   Extension   Outil recommandé
  -------  ----------  -------------------------------------------------------
  HTML     .html       Navigateur web (Chrome, Firefox, Edge…)
                       Mindmap interactive : zoom, déplacement, repli des nœuds
  FreeMind .mm         Freeplane, FreeMind ; import possible dans XMind
  draw.io  .drawio     draw.io (app.diagrams.net ou application desktop)
                       Layout arborescent horizontal calculé automatiquement
  OPML     .opml       XMind, MindManager, Logseq, Obsidian, OmniOutliner…
                       Format pivot XML universel, interopérabilité maximale
  Mermaid  .md         GitHub, GitLab, Notion, VS Code (extension Mermaid)
                       Bloc ```mermaid mindmap``` dans un fichier Markdown
  XMind    .xmind      XMind version 2020 et ultérieure
                       Format ZIP/JSON natif XMind

Les noms de fichiers suivent le schéma : mindmap_<NOM_DOSSIER>.<ext>
Exemple pour un dossier "00_HALASNR" : mindmap_00_HALASNR.html, .mm, etc.


--------------------------------------------------------------------------------
PARAMÈTRES CONFIGURABLES
--------------------------------------------------------------------------------
Les constantes suivantes sont accessibles en tête de script (lignes 30–75) :

  PROFONDEUR_MAX (défaut : 5)
      Profondeur maximale de l'arborescence parcourue.
      Valeur 0 = illimitée (attention aux arborescences très profondes).

  DOSSIERS_EXCLUS
      Noms de dossiers ignorés lors du parcours (défaut : .git, __pycache__,
      node_modules, .venv, venv, $RECYCLE.BIN, System Volume Information).
      Insensible à la casse uniquement si le système de fichiers l'est.

  EXTENSIONS_SYSTEME
      Extensions toujours exclues de l'affichage des fichiers, quelle que soit
      l'option choisie dans la boîte de dialogue (défaut : .tmp, .lnk, .ini,
      .db, .DS_Store, .thumbs, .bak, .log, .exe, .dll, .sys, .pyc).

  CATEGORIES_FICHIERS
      Dictionnaire des catégories de fichiers proposées dans la boîte de
      dialogue. Chaque catégorie peut être cochée/décochée indépendamment.
      Modifiable pour ajouter des extensions ou créer de nouvelles catégories.

  TOUTES_EXTENSIONS
      Sentinel interne (frozenset{"*"}) signifiant "afficher tous les fichiers
      hors EXTENSIONS_SYSTEME". Activé lorsque la case "Autres formats" est
      cochée dans la boîte de dialogue.

  Couleurs HTML (dans TEMPLATE_HTML, section « Paramètres de couleur »)
      COULEUR_RACINE  = "#0A0096"   nœud racine (profondeur 0)
      COULEUR_NIVEAU1 = "#0082FF"   nœuds de profondeur 1 (identiques)
      PALETTE_NIVEAU2 = [...]       couleurs uniques par nœud de profondeur 2
                                    (aléatoire si la palette est épuisée)
      Profondeur 3+ : couleur gelée, héritée du nœud de profondeur 2 parent.

  Couleurs draw.io (fonction _style_drawio)
      Profondeur 0 : #0A0096 (fond bleu foncé, texte blanc)
      Profondeur 1 : #0082FF (fond bleu, texte blanc)
      Profondeur 2+ : #AFE1FA (fond bleu clair, contour #0082FF)
      Fichiers      : #f5f5f5 (fond gris clair, contour gris)


--------------------------------------------------------------------------------
DÉPENDANCES
--------------------------------------------------------------------------------
  Python >= 3.12 (annotations list[str], dict[str, bool], frozenset[str] | None)
  Bibliothèques : os, json, uuid, webbrowser, zipfile,
                  xml.etree.ElementTree, tkinter
  Toutes issues de la bibliothèque standard Python — aucun pip install.

  Pour le format HTML : connexion internet requise à l'ouverture dans le
  navigateur (chargement des librairies Markmap et D3 via CDN jsDelivr).


--------------------------------------------------------------------------------
NOTES PAR FORMAT
--------------------------------------------------------------------------------
  HTML
    - Nécessite une connexion internet pour charger Markmap et D3 (CDN).
    - Fonctionne en lecture seule ; non éditable directement.

  .mm (FreeMind/Freeplane)
    - Les nœuds de profondeur >= 2 sont repliés par défaut à l'ouverture.
    - Importable dans draw.io via Extras > Edit Diagram > import FreeMind.

  .drawio
    - Après ouverture, utiliser Ctrl+Shift+H (Reset View) si le diagramme
      n'est pas centré.
    - Le layout est calculé par le script (arbre horizontal gauche→droite) ;
      il peut être réorganisé manuellement dans draw.io.

  .opml
    - Format le plus interopérable : à privilégier pour partager avec des
      utilisateurs dont l'outil cible n'est pas connu à l'avance.

  .md (Mermaid)
    - Rendu automatique sur GitHub, GitLab et Notion sans plugin.
    - Sous VS Code : installer l'extension "Markdown Preview Mermaid Support".
    - Les parenthèses dans les noms de dossiers/fichiers sont remplacées par
      des crochets (contrainte de syntaxe Mermaid).

  .xmind
    - Compatible XMind 2020+ uniquement (format JSON/ZIP).
    - Les versions antérieures utilisent un format XML différent (non pris
      en charge par ce script).


--------------------------------------------------------------------------------
STRUCTURE DU SCRIPT
--------------------------------------------------------------------------------
  lister_sous_dossiers()          Utilitaire : listage des sous-dossiers
  lister_fichiers()               Utilitaire : listage des fichiers filtrés
  construire_markdown()           Génération Markdown pour Markmap (HTML)
  exporter_html()                 Export HTML interactif
  exporter_mm()                   Export FreeMind/Freeplane (.mm)
  _NoeudDrawio (classe)           Modèle de nœud pour le layout draw.io
  _construire_arbre_drawio()      Construction de l'arbre draw.io
  _assigner_positions()           Calcul du layout arborescent (draw.io)
  _style_drawio()                 Styles mxGraph par profondeur et type
  exporter_drawio()               Export draw.io (.drawio)
  exporter_opml()                 Export OPML
  exporter_mermaid()              Export Mermaid Markdown (.md)
  _construire_topic_xmind()       Construction récursive du topic XMind
  exporter_xmind()                Export XMind (.xmind)
  demander_formats()              Boîte de dialogue : formats + catégories
  main()                          Point d'entrée principal


--------------------------------------------------------------------------------
QUALITÉ
--------------------------------------------------------------------------------
  Score pylint : 10.00/10
  Vérification : python -m pylint exporter_arborescence_mindmap.py


--------------------------------------------------------------------------------
HISTORIQUE DES VERSIONS
--------------------------------------------------------------------------------
  1.1  2026-06-11  Ajout de l'inclusion des fichiers (catégories sélectionnables,
                   sentinel TOUTES_EXTENSIONS, catch-all "Autres formats").
                   Correction du bug sentinel None ambigu.
  1.0  2026-06-11  Version initiale. Export multi-format (HTML, .mm, .drawio,
                   .opml, .md Mermaid, .xmind). Sélection du dossier de
                   destination. Palette de couleurs ASNR.


--------------------------------------------------------------------------------
LICENCE
--------------------------------------------------------------------------------
Ce logiciel est publie en open source sous licence MIT (SPDX : MIT).

Copyright (c) 2026 Justine Bouwy-Ounnough

L'autorisation est accordee, gracieusement, a toute personne obtenant une copie
de ce logiciel d'en faire ce que bon lui semble (utiliser, copier, modifier,
fusionner, publier, distribuer), sous reserve de conserver la mention de
copyright et la presente notice. Le texte integral figure dans le fichier
LICENSE a la racine du depot.

LE LOGICIEL EST FOURNI « EN L'ETAT », SANS GARANTIE D'AUCUNE SORTE.

================================================================================