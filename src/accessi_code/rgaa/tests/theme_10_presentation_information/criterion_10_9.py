from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Patterns de détection de références aux caractéristiques sensorielles
# Ces patterns détectent les phrases qui font référence à la forme, taille ou position
# On utilise (?<!\w) et (?!\w) au lieu de \b pour mieux gérer les accents
_SENSORY_SHAPE_PATTERNS = [
    r"(?<!\w)(rond(?:e?s?)?|circulaire(?:s?)?|carré(?:e?s?)?|rectangulaire(?:s?)?)(?!\w)",
    r"(?<!\w)(triangle(?:s?)?|oval(?:e?s?)?|losange(?:s?)?)(?!\w)",
    r"(?<!\w)(flèche(?:s?)?|fléché(?:e?s?)?)(?!\w)",
    r"(?<!\w)(étoile(?:s?)?|coeur|cœur|diamant(?:s?)?)(?!\w)",
    r"(?<!\w)(forme|formes)\s+(?:de|du|des)\s+(rond|carré|triangle|oval|cercle)(?!\w)",
]

_SENSORY_SIZE_PATTERNS = [
    r"(?<!\w)(gros(?:se)?|grands?|grandes?|petits?|petites?)(?!\w)",
    r"(?<!\w)(grand|grande|large|étroit|haut|basse?)(?!\w)",
    r"(?<!\w)(énorme|minuscule|gigantesque|microscopique)(?!\w)",
    r"(?<!\w)(taille|dimension|dimensions)\s+(?:de|du|des)",
    r"(?<!\w)(plus\s+grand|plus\s+petit|plus\s+large|plus\s+haut|plus\s+bas)(?!\w)",
    r"(?<!\w)(grossir|rapetisser|agrandir|rétrécir)(?!\w)",
]

_SENSORY_POSITION_PATTERNS = [
    r"(?<!\w)(gauche|droite|haut|bas|haut-gauche|haut-droite|bas-gauche|bas-droite)(?!\w)",
    r"(?<!\w)(à\s+gauche|à\s+droite|en\s+haut|en\s+bas)(?!\w)",
    r"(?<!\w)(au\s+centre|au\s+milieu|centré(?:e?s?)?)(?!\w)",
    r"(?<!\w)(sur\s+la\s+gauche|sur\s+la\s+droite|dans\s+le\s+coin)(?!\w)",
    r"(?<!\w)(avant|après|avant-dernier|dernier|premier)(?!\w)",
    r"(?<!\w)(du\s+côté\s+(?:gauche|droit|haut|bas))(?!\w)",
    r"(?<!\w)(à\s+côté\s+de|à\s+proximité\s+de|près\s+de|loin\s+de)(?!\w)",
    r"(?<!\w)(au-dessus|au-dessous|dessus|dessous|entre)(?!\w)",
    r"(?<!\w)(position|emplacement|localisation|place)(?!\w)",
    r"(?<!\w)(aligné(?:e?s?)?)(?!\w)",
]

_SENSORY_COLOR_PATTERNS = [
    r"(?<!\w)(rouge|bleu|vert|jaune|orange|violet|rose|noir|blanc|gris)(?!\w)",
    r"(?<!\w)(couleur|couleurs)\s+(?:de|du|des|est)",
    r"(?<!\w)(vert\s+clair|bleu\s+foncé|rouge\s+vif|jaune\s+pâle)(?!\w)",
]

# Combinaison de tous les patterns
_ALL_SENSORY_PATTERNS = (
    _SENSORY_SHAPE_PATTERNS + _SENSORY_SIZE_PATTERNS + _SENSORY_POSITION_PATTERNS + _SENSORY_COLOR_PATTERNS
)

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _ALL_SENSORY_PATTERNS]

# Mots-clés qui indiquent une référence à un élément UI
_UI_ELEMENT_KEYWORDS = {
    "bouton",
    "button",
    "lien",
    "link",
    "menu",
    "onglet",
    "tab",
    "champ",
    "field",
    "zone",
    "area",
    "boîte",
    "box",
    "fenêtre",
    "window",
    "dialogue",
    "dialog",
    "modale",
    "modal",
    "popup",
    "pop-up",
    "tooltip",
    "infobulle",
    "icône",
    "icon",
    "image",
    "img",
    "photo",
    "illustration",
    "figure",
    "vidéo",
    "video",
    "audio",
    "média",
    "media",
    "film",
    "clip",
    "animation",
    "graphique",
    "graph",
    "chart",
    "diagram",
    "diagramme",
    "carte",
    "map",
    "document",
    "pdf",
    "fichier",
    "file",
    "tableau",
    "table",
    "liste",
    "list",
    "ligne",
    "row",
    "colonne",
    "column",
    "cellule",
    "cell",
    "en-tête",
    "header",
    "pied",
    "footer",
    "barre",
    "bar",
    "navigation",
    "nav",
    "sidebar",
    "aside",
    "section",
    "article",
    "paragraphe",
    "paragraph",
    "titre",
    "heading",
    "sous-titre",
    "subtitle",
    "texte",
    "text",
    "contenu",
    "content",
    "élément",
    "element",
    "composant",
    "component",
    "contrôle",
    "control",
}


def _selector_for(soup: BeautifulSoup, element: Tag) -> str:
    """Construit un sélecteur lisible pour un élément."""
    element_id = element.get("id")
    if isinstance(element_id, str) and element_id:
        return f"#{element_id}"
    classes = element.get("class", [])
    if isinstance(classes, list) and classes:
        return f"{element.name}.{'.'.join(str(c) for c in classes[:2])}"
    same_tag = soup.find_all(element.name)
    if len(same_tag) > 1:
        try:
            return f"{element.name}[index={same_tag.index(element)}]"
        except ValueError:
            pass
    return element.name or "élément inconnu"


def _get_text_content(element: Tag) -> str:
    """Récupère le contenu textuel d'un élément."""
    return element.get_text(" ", strip=True)


def _has_sensory_reference(text: str) -> tuple[bool, list[str]]:
    """
    Vérifie si un texte contient des références aux caractéristiques sensorielles.
    Retourne (a_référence, liste_des_types_trouvés).
    """
    if not text or len(text.strip()) < 3:
        return False, []

    found_types = []
    text_lower = text.lower()

    # Vérifier forme
    for pattern in _SENSORY_SHAPE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_types.append("forme")
            break

    # Vérifier taille
    for pattern in _SENSORY_SIZE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_types.append("taille")
            break

    # Vérifier position
    for pattern in _SENSORY_POSITION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_types.append("position")
            break

    # Vérifier couleur (souvent liée à la forme/taille/position pour l'info)
    for pattern in _SENSORY_COLOR_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_types.append("couleur")
            break

    return len(found_types) > 0, found_types


def _references_ui_element(text: str) -> bool:
    """Vérifie si le texte fait référence à un élément d'interface."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _UI_ELEMENT_KEYWORDS)


def _extract_text_nodes(soup: BeautifulSoup) -> list[Tag]:
    """Extrait tous les nœuds de texte pertinents (pas seulement les balises)."""
    text_nodes = []
    for element in soup.find_all(True):  # Tous les éléments
        # On cherche les éléments qui contiennent du texte direct
        if element.string and element.string.strip():
            # Exclure script, style, etc.
            if element.name not in {"script", "style", "noscript", "template"}:
                text_nodes.append(element)
    return text_nodes


def _analyze_text_for_sensory_info(
    soup: BeautifulSoup,
    text_nodes: list[Tag],
    test_id: str,
) -> list[Finding]:
    """
    Analyse les nœuds de texte pour détecter les informations
    données uniquement par la forme, taille ou position.
    """
    findings: list[Finding] = []
    sensory_elements = 0

    for element in text_nodes:
        text = _get_text_content(element)
        if len(text) < 10:  # Ignorer les textes trop courts
            continue

        has_sensory, sensory_types = _has_sensory_reference(text)
        if not has_sensory:
            continue

        # Vérifier si ça référence un élément UI
        if not _references_ui_element(text):
            continue

        sensory_elements += 1
        selector = _selector_for(soup, element)

        # Vérifier s'il y a une alternative textuelle évidente
        # Par exemple, un label, aria-label, title, etc. sur l'élément référencé
        # Pour l'instant, on signale comme NEEDS_REVIEW car l'analyse complète
        # nécessiterait de retrouver l'élément référencé et vérifier son étiquetage

        findings.append(
            Finding(
                element=selector,
                message=(
                    f"Texte détecté faisant référence à des caractéristiques sensorielles "
                    f'({", ".join(sensory_types)}) : "{text[:150]}{"..." if len(text) > 150 else ""}". '
                    f"Ce texte semble désigner un élément d'interface par sa forme, taille ou position."
                ),
                recommendation=(
                    "Vérifier que l'information transmise par la forme, taille ou position "
                    "est également disponible sous forme textuelle (label, aria-label, "
                    "texte alternatif, description adjacente, etc.). "
                    "Exemple : au lieu de 'cliquez sur le bouton rond à droite', utiliser "
                    "'cliquez sur le bouton \"Valider\" (bouton rond à droite)'."
                ),
                evidence={
                    "text_content": text[:500],
                    "sensory_types": sensory_types,
                    "references_ui_element": True,
                    "test_id": test_id,
                    "needs_manual_check": True,
                    "condition": "sensory_reference_without_text_alternative",
                },
            )
        )

    return findings, sensory_elements


def _get_image_context_text(img: Tag) -> str:
    """
    Récupère le texte de contexte pertinent pour une image.
    Regarde le texte du précédent frère, du parent (si court), ou figure/figcaption.
    """
    return _get_media_context_text(img)


def _get_media_context_text(media: Tag) -> str:
    """
    Récupère le texte de contexte pertinent pour un média (image, video, audio, canvas, etc.).
    Regarde le texte du précédent frère significatif, figure/figcaption, ou parent limité.
    """
    context_parts = []

    # 1. Chercher un figcaption associé (dans un figure parent)
    figure = media.find_parent("figure")
    if figure:
        figcaption = figure.find("figcaption")
        if figcaption:
            context_parts.append(_get_text_content(figcaption))

    # 2. Texte du précédent frère significatif
    prev = media.previous_sibling
    while prev:
        if isinstance(prev, Tag):
            text = _get_text_content(prev)
            if text and len(text) > 5:
                context_parts.append(text)
                break
        elif isinstance(prev, str) and prev.strip():
            context_parts.append(prev.strip())
            break
        prev = prev.previous_sibling

    # 3. Si pas de contexte trouvé, regarder le parent mais limiter
    if not context_parts and media.parent:
        parent_text = _get_text_content(media.parent)
        # Ne prendre que les 500 premiers caractères pour éviter le bruit
        if len(parent_text) <= 500:
            context_parts.append(parent_text)
        else:
            # Essayer de trouver le texte le plus proche dans le parent
            # En regardant les frères précédents dans le parent
            for sibling in media.parent.children:
                if sibling is media:
                    break
                if isinstance(sibling, Tag):
                    text = _get_text_content(sibling)
                    if text and len(text) > 10:
                        context_parts.append(text[-200:])  # Fin du texte précédent
                        break

    return " ".join(context_parts)


def _analyze_images_for_sensory_info(
    soup: BeautifulSoup,
    test_id: str,
) -> list[Finding]:
    """
    Analyse les images pour détecter si elles transmettent de l'information
    par leur forme, taille ou position sans alternative textuelle.
    """
    findings: list[Finding] = []
    sensory_images = 0

    images = soup.find_all("img")
    for img in images:
        alt = img.get("alt", "")
        src = img.get("src", "")
        selector = _selector_for(soup, img)

        # Vérifier si l'image a un attribut alt
        has_alt_attr = img.has_attr("alt")
        alt_text = alt.strip() if has_alt_attr else ""
        # has_alt = True si l'attribut alt existe ET n'est pas vide (décoratif)
        # alt="" signifie intentionnellement décoratif, ne pas signaler
        has_alt = has_alt_attr and len(alt_text) > 0

        # Analyser le contexte de l'image (texte adjacent, caption, etc.)
        # Pour détecter si l'image est référencée par sa forme/taille/position
        context_text = _get_image_context_text(img)

        # Vérifier les patterns sensoriels dans le contexte
        context_has_sensory, sensory_types = _has_sensory_reference(context_text)
        context_refs_ui = _references_ui_element(context_text)

        # Si l'image semble transmettre de l'info sensorielle sans alt adéquat
        # On ne signale PAS si alt="" (décoratif intentionnel)
        if context_has_sensory and context_refs_ui and not has_alt_attr:
            # Pas d'attribut alt du tout
            sensory_images += 1
            findings.append(
                Finding(
                    element=selector,
                    message=(
                        f"Image (src: {src[:100]}) référencée par ses caractéristiques "
                        f"sensorielles ({', '.join(sensory_types)}) dans le contexte "
                        f"mais sans attribut alt."
                    ),
                    recommendation=(
                        "Ajouter un attribut alt descriptif qui transmet l'information "
                        "visuelle (forme, taille, position) si elle est porteuse de sens. "
                        'Si l\'image est purement décorative, utiliser alt="".'
                    ),
                    evidence={
                        "src": src[:200],
                        "alt": alt_text,
                        "context_text": context_text[:300],
                        "sensory_types": sensory_types,
                        "has_alt": False,
                        "test_id": test_id,
                        "needs_manual_check": True,
                        "condition": "image_sensory_info_without_alt",
                    },
                )
            )
        elif has_alt and context_has_sensory and context_refs_ui:
            # L'image a un alt non-vide, vérifier s'il décrit bien l'info sensorielle
            alt_has_sensory, alt_sensory_types = _has_sensory_reference(alt_text)
            if not alt_has_sensory:
                sensory_images += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Image (src: {src[:100]}) référencée par ses caractéristiques "
                            f"sensorielles ({', '.join(sensory_types)}) dans le contexte "
                            f"mais l'attribut alt ne décrit pas ces caractéristiques : "
                            f'"{alt_text[:100]}".'
                        ),
                        recommendation=(
                            "S'assurer que l'attribut alt décrit l'information visuelle "
                            "portée par la forme, taille ou position de l'image, "
                            "si cette information est nécessaire à la compréhension."
                        ),
                        evidence={
                            "src": src[:200],
                            "alt": alt_text,
                            "context_text": context_text[:300],
                            "context_sensory_types": sensory_types,
                            "alt_sensory_types": alt_sensory_types,
                            "has_alt": True,
                            "test_id": test_id,
                            "needs_manual_check": True,
                            "condition": "image_alt_missing_sensory_description",
                        },
                    )
                )

    return findings, sensory_images


async def _analyze_with_ai_page_analyzer(
    context: AuditContext,
    services: Any | None,
    test_id: str,
    sensory_findings: list[Finding],
) -> tuple[list[Finding], int]:
    """
    Utilise l'analyseur de page IA pour une analyse sémantique plus poussée
    des références sensorielles détectées.
    """
    if not sensory_findings:
        return [], 0

    page_analyzer = getattr(services, "page_analyzer", None) if services is not None else None

    if page_analyzer is None:
        return sensory_findings, 0

    # Pour l'instant, on n'utilise pas l'IA car il n'y a pas d'analyzer spécifique
    # pour les caractéristiques sensorielles. On retourne les findings déterministes.
    # TODO: Créer un analyzer dédié pour le critère 10.9 si nécessaire.
    return sensory_findings, 0


class Test1091(RGAATest):
    """Test 10.9.1 : Dans chaque page web, pour chaque texte ou ensemble de textes,
    l'information ne doit pas être donnée uniquement par la forme, taille ou position."""

    test_id = "10.9.1"
    criterion_id = "10.9"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.9.1 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Extraire les nœuds de texte
        text_nodes = _extract_text_nodes(soup)

        if not text_nodes:
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.PASS,
                summary="Aucun contenu textuel dans la page.",
                tested_elements=0,
            )

        # Analyser les textes pour détecter les références sensorielles
        findings, sensory_count = _analyze_text_for_sensory_info(soup, text_nodes, self.test_id)

        # Analyser avec IA si disponible (pour analyse sémantique plus fine)
        findings, ai_count = await _analyze_with_ai_page_analyzer(context, services, self.test_id, findings)

        # Déterminer le statut
        # Les findings déterministes sont des NEEDS_REVIEW (vérification manuelle requise)
        needs_review_findings = [f for f in findings if f.evidence.get("needs_manual_check")]

        if needs_review_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {sensory_count} texte(s) faisant référence à des "
                f"caractéristiques sensorielles (forme, taille, position) détecté(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s) "
                "pour confirmer l'existence d'alternatives textuelles."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun texte faisant référence à des caractéristiques sensorielles "
                "(forme, taille, position) pour désigner des éléments d'interface "
                "sans alternative textuelle détecté."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=sensory_count,
            metadata={
                "text_nodes_analyzed": len(text_nodes),
                "sensory_references_found": sensory_count,
                "needs_review_count": len(needs_review_findings),
                "ai_analyzed_count": ai_count,
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que chaque référence à la forme/taille/position "
                    "a une alternative textuelle (label, aria-label, texte adjacent)",
                    "vérifier que l'information n'est pas transmise uniquement visuellement",
                ],
                "manual_check_for": "critère 10.9.1 - information par forme/taille/position (textes)",
            },
        )


class Test1092(RGAATest):
    """Test 10.9.2 : Dans chaque page web, pour chaque image ou ensemble d'images,
    l'information ne doit pas être donnée uniquement par la forme, taille ou position."""

    test_id = "10.9.2"
    criterion_id = "10.9"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.9.2 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Analyser les images pour détecter les infos sensorielles sans alt adéquat
        findings, sensory_count = _analyze_images_for_sensory_info(soup, self.test_id)

        # Déterminer le statut
        needs_review_findings = [f for f in findings if f.evidence.get("needs_manual_check")]

        if needs_review_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {sensory_count} image(s) potentiellement porteuse(s) "
                f"d'information par forme/taille/position détectée(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s) "
                "pour confirmer l'adéquation des alternatives textuelles (alt)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucune image transmettant de l'information uniquement par sa forme, "
                "taille ou position sans alternative textuelle adéquate détectée."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=sensory_count,
            metadata={
                "images_analyzed": len(soup.find_all("img")),
                "sensory_images_found": sensory_count,
                "needs_review_count": len(needs_review_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier que chaque image porteuse d'info sensorielle a un alt descriptif",
                    "vérifier que l'alt décrit bien la forme/taille/position si porteuse de sens",
                    'vérifier alt="" pour les images purement décoratives',
                ],
                "manual_check_for": "critère 10.9.2 - information par forme/taille/position (images)",
            },
        )


class Test1093(RGAATest):
    """Test 10.9.3 : Dans chaque page web, pour chaque média temporel,
    l'information ne doit pas être donnée uniquement par la forme, taille ou position."""

    test_id = "10.9.3"
    criterion_id = "10.9"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.9.3 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Rechercher les médias temporels (video, audio)
        time_based_media = soup.find_all(["video", "audio"])
        findings: list[Finding] = []
        sensory_count = 0

        for media in time_based_media:
            selector = _selector_for(soup, media)
            media_type = media.name

            # Vérifier les attributs d'accessibilité
            has_track = bool(media.find("track", kind="captions") or media.find("track", kind="subtitles"))
            has_aria_label = bool(media.get("aria-label", "").strip())
            has_aria_describedby = bool(media.get("aria-describedby", "").strip())
            has_title = bool(media.get("title", "").strip())

            # Vérifier le contexte textuel pour références sensorielles
            context_text = _get_media_context_text(media)

            context_has_sensory, sensory_types = _has_sensory_reference(context_text)
            context_refs_ui = _references_ui_element(context_text)

            # Si le média est référencé par caractéristiques sensorielles sans alternative
            if context_has_sensory and context_refs_ui and not (has_track or has_aria_label or has_aria_describedby):
                sensory_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Média temporel <{media_type}> référencé par ses caractéristiques "
                            f"sensorielles ({', '.join(sensory_types)}) dans le contexte "
                            f"mais sans alternative textuelle détectée (track, aria-label, "
                            f"aria-describedby)."
                        ),
                        recommendation=(
                            "Fournir une alternative textuelle équivalente : sous-titres (track), "
                            "transcription, description audio, ou aria-label/aria-describedby "
                            "décrivant l'information visuelle portée par la forme, taille ou position."
                        ),
                        evidence={
                            "media_type": media_type,
                            "src": media.get("src", "")[:200],
                            "context_text": context_text[:300],
                            "sensory_types": sensory_types,
                            "has_track": has_track,
                            "has_aria_label": has_aria_label,
                            "has_aria_describedby": has_aria_describedby,
                            "has_title": has_title,
                            "test_id": self.test_id,
                            "needs_manual_check": True,
                            "condition": "time_media_sensory_info_without_alternative",
                        },
                    )
                )

        # Déterminer le statut
        needs_review_findings = [f for f in findings if f.evidence.get("needs_manual_check")]

        if needs_review_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {sensory_count} média(s) temporel(s) potentiellement "
                f"porteur(s) d'information par forme/taille/position détecté(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun média temporel transmettant de l'information uniquement par sa forme, "
                "taille ou position sans alternative textuelle détecté."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=sensory_count,
            metadata={
                "time_based_media_found": len(time_based_media),
                "sensory_media_found": sensory_count,
                "needs_review_count": len(needs_review_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier la présence de sous-titres, transcription ou description audio",
                    "vérifier aria-label/aria-describedby pour l'info sensorielle",
                    "vérifier que l'info forme/taille/position est disponible en texte",
                ],
                "manual_check_for": "critère 10.9.3 - information par forme/taille/position (médias temporels)",
            },
        )


class Test1094(RGAATest):
    """Test 10.9.4 : Dans chaque page web, pour chaque média non temporel,
    l'information ne doit pas être donnée uniquement par la forme, taille ou position."""

    test_id = "10.9.4"
    criterion_id = "10.9"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        soup = getattr(context, "dom", None)

        if not isinstance(soup, BeautifulSoup):
            return TestResult(
                test_id=self.test_id,
                criterion_id=self.criterion_id,
                status=TestStatus.NOT_TESTED,
                summary="Le DOM n'est pas disponible ; le test 10.9.4 nécessite l'analyse de la page.",
                tested_elements=0,
                metadata={"reason": "missing_dom"},
            )

        # Rechercher les médias non temporels (canvas, svg, object, embed, iframe)
        non_time_media = soup.find_all(["canvas", "svg", "object", "embed", "iframe"])
        findings: list[Finding] = []
        sensory_count = 0

        for media in non_time_media:
            selector = _selector_for(soup, media)
            media_type = media.name

            # Vérifier les attributs d'accessibilité
            has_aria_label = bool(media.get("aria-label", "").strip())
            has_aria_describedby = bool(media.get("aria-describedby", "").strip())
            has_title = bool(media.get("title", "").strip())
            has_role_img = media.get("role", "").lower() == "img"

            # Pour canvas, vérifier s'il a un contenu de fallback
            canvas_fallback = ""
            if media_type == "canvas":
                canvas_fallback = _get_text_content(media)

            # Vérifier le contexte textuel pour références sensorielles
            context_text = _get_media_context_text(media)

            context_has_sensory, sensory_types = _has_sensory_reference(context_text)
            context_refs_ui = _references_ui_element(context_text)

            # Déterminer s'il y a une alternative
            has_alternative = (
                has_aria_label
                or has_aria_describedby
                or has_title
                or has_role_img
                or (media_type == "canvas" and canvas_fallback.strip())
            )

            # Si le média est référencé par caractéristiques sensorielles sans alternative
            if context_has_sensory and context_refs_ui and not has_alternative:
                sensory_count += 1
                findings.append(
                    Finding(
                        element=selector,
                        message=(
                            f"Média non temporel <{media_type}> référencé par ses caractéristiques "
                            f"sensorielles ({', '.join(sensory_types)}) dans le contexte "
                            f"mais sans alternative textuelle détectée "
                            f"(aria-label, aria-describedby, title, role=img, fallback)."
                        ),
                        recommendation=(
                            "Fournir une alternative textuelle équivalente : aria-label, "
                            'aria-describedby, title, role="img" avec description, '
                            "ou contenu de fallback (pour canvas) décrivant l'information "
                            "visuelle portée par la forme, taille ou position."
                        ),
                        evidence={
                            "media_type": media_type,
                            "src": media.get("src", media.get("data", ""))[:200],
                            "context_text": context_text[:300],
                            "sensory_types": sensory_types,
                            "has_aria_label": has_aria_label,
                            "has_aria_describedby": has_aria_describedby,
                            "has_title": has_title,
                            "has_role_img": has_role_img,
                            "canvas_fallback": canvas_fallback[:200] if canvas_fallback else "",
                            "test_id": self.test_id,
                            "needs_manual_check": True,
                            "condition": "non_time_media_sensory_info_without_alternative",
                        },
                    )
                )

        # Déterminer le statut
        needs_review_findings = [f for f in findings if f.evidence.get("needs_manual_check")]

        if needs_review_findings:
            status = TestStatus.NEEDS_REVIEW
            summary = (
                f"Analyse terminée : {sensory_count} média(s) non temporel(s) potentiellement "
                f"porteur(s) d'information par forme/taille/position détecté(s). "
                f"{len(needs_review_findings)} vérification(s) manuelle(s) requise(s)."
            )
        else:
            status = TestStatus.PASS
            summary = (
                "Aucun média non temporel transmettant de l'information uniquement par sa forme, "
                "taille ou position sans alternative textuelle détecté."
            )

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=status,
            summary=summary,
            findings=findings,
            tested_elements=sensory_count,
            metadata={
                "non_time_media_found": len(non_time_media),
                "sensory_media_found": sensory_count,
                "needs_review_count": len(needs_review_findings),
                "browser_check_required": True,
                "required_manual_checks": [
                    "vérifier aria-label/aria-describedby/title pour l'info sensorielle",
                    'vérifier role="img" avec description pour canvas/svg',
                    "vérifier contenu de fallback pour canvas",
                    "vérifier que l'info forme/taille/position est disponible en texte",
                ],
                "manual_check_for": "critère 10.9.4 - information par forme/taille/position (médias non temporels)",
            },
        )
