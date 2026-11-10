"""Extraction des propriétés CSS calculées avec Playwright."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright


@dataclass
class ComputedStyle:
    """Propriétés CSS calculées d'un élément HTML."""

    element: str
    text: str
    color: str
    background_color: str
    font_size: str
    font_weight: str
    display: str
    visibility: str


@dataclass
class TextStyleObservation:
    """
    Observation d'un fragment de texte rendu.

    background_color vaut None lorsque le fond visible
    ne peut pas être déterminé suffisamment sûrement.

    review_reason explique les éventuelles incertitudes.

    Une observation ne constitue pas un verdict RGAA.
    """

    element: str
    text: str
    color: str
    background_color: str | None
    font_size_px: float
    font_weight: int
    review_reason: str | None = None


async def _extract_from_page(
    html_path: Path,
    javascript: str,
) -> list[dict[str, Any]]:
    """
    Charge une page HTML locale et exécute une extraction JavaScript.

    Réservé pour l'instant aux pages locales de confiance.
    Le navigateur n'est pas encore isolé pour l'analyse
    de contenus HTML/JavaScript non fiables.
    """

    html_path = Path(html_path).resolve()

    if not html_path.is_file():
        raise FileNotFoundError(f"Document HTML introuvable : {html_path}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
        )

        try:
            page = await browser.new_page(
                viewport={
                    "width": 1280,
                    "height": 900,
                }
            )

            await page.goto(
                html_path.as_uri(),
                wait_until="load",
                timeout=15000,
            )

            return await page.evaluate(javascript)

        finally:
            await browser.close()


async def extract_computed_styles(
    html_path: Path,
) -> list[ComputedStyle]:
    """
    Extrait les styles calculés des éléments HTML.

    Cette fonction reste compatible avec les anciens
    scripts de débogage AccessiCode.
    """

    javascript = """
    () => {
        return Array.from(
            document.querySelectorAll("body *")
        ).map((element, index) => {
            const style = window.getComputedStyle(element);

            return {
                element: element.id
                    ? `${element.tagName.toLowerCase()}#${element.id}`
                    : `${element.tagName.toLowerCase()}[${index}]`,
                text: element.innerText || "",
                color: style.color,
                background_color: style.backgroundColor,
                font_size: style.fontSize,
                font_weight: style.fontWeight,
                display: style.display,
                visibility: style.visibility
            };
        });
    }
    """

    extracted = await _extract_from_page(
        html_path,
        javascript,
    )

    return [ComputedStyle(**item) for item in extracted]


async def extract_text_styles(
    html_path: Path,
) -> list[TextStyleObservation]:
    """
    Extrait les propriétés CSS des fragments de texte.

    V3.1 :
    - conserve les fragments de texte directs ;
    - identifie les fonds complexes ;
    - fait défiler les éléments avant le contrôle géométrique ;
    - recalcule les rectangles après le défilement ;
    - signale les superpositions potentielles ;
    - conserve les observations incertaines pour vérification.

    L'extraction reste partielle et ne garantit pas une
    couverture exhaustive des contrastes de la page.
    """

    javascript = r"""
    async () => {
        const observations = [];

        const excludedTags = new Set([
            "script",
            "style",
            "noscript",
            "template",
            "head",
            "svg",
            "canvas"
        ]);

        function labelOf(element) {
            if (element.id) {
                return `${element.tagName.toLowerCase()}#${element.id}`;
            }

            const parts = [];
            let current = element;

            while (
                current &&
                current.nodeType === Node.ELEMENT_NODE
            ) {
                let part = current.tagName.toLowerCase();
                const parent = current.parentElement;

                if (parent) {
                    const siblings = Array.from(
                        parent.children
                    ).filter(
                        child => child.tagName === current.tagName
                    );

                    if (siblings.length > 1) {
                        part += `:nth-of-type(${
                            siblings.indexOf(current) + 1
                        })`;
                    }
                }

                parts.unshift(part);
                current = parent;
            }

            return parts.join(" > ");
        }

        function isVisible(element) {
            let current = element;

            while (current) {
                const style = getComputedStyle(current);

                if (
                    style.display === "none" ||
                    style.visibility === "hidden" ||
                    style.visibility === "collapse" ||
                    current.hasAttribute("hidden") ||
                    current.hasAttribute("inert")
                ) {
                    return false;
                }

                current = current.parentElement;
            }

            return element.getClientRects().length > 0;
        }

        function parseColor(value) {
            const match = value.match(
                /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/
            );

            if (!match) {
                return null;
            }

            const red = Number(match[1]);
            const green = Number(match[2]);
            const blue = Number(match[3]);

            const alpha = match[4] === undefined
                ? 1
                : Number(match[4]);

            if (
                red > 255 ||
                green > 255 ||
                blue > 255 ||
                alpha < 0 ||
                alpha > 1
            ) {
                return null;
            }

            return {
                red,
                green,
                blue,
                alpha
            };
        }

        function hasPseudoContent(element) {
            for (const pseudo of ["::before", "::after"]) {
                const style = getComputedStyle(element, pseudo);

                if (style.display === "none") {
                    continue;
                }

                const content = style.content;

                if (
                    content &&
                    content !== "none" &&
                    content !== "normal" &&
                    content !== '""' &&
                    content !== "''"
                ) {
                    return true;
                }

                const color = parseColor(
                    style.backgroundColor
                );

                if (
                    style.backgroundImage !== "none" ||
                    (color !== null && color.alpha > 0)
                ) {
                    return true;
                }
            }

            return false;
        }

        function hasComplexEffect(style) {
            return (
                Number(style.opacity) !== 1 ||
                style.mixBlendMode !== "normal" ||
                style.filter !== "none" ||
                style.backdropFilter !== "none" ||
                style.backgroundImage !== "none" ||
                style.maskImage !== "none" ||
                style.clipPath !== "none"
            );
        }

        function resolveBackground(element) {
            let current = element;

            while (current) {
                const style = getComputedStyle(current);

                if (hasComplexEffect(style)) {
                    return {
                        color: null,
                        reason: "Effet CSS ou arrière-plan complexe",
                        backgroundElement: null
                    };
                }

                if (hasPseudoContent(current)) {
                    return {
                        color: null,
                        reason: (
                            "Pseudo-élément susceptible "
                            + "de modifier le rendu"
                        ),
                        backgroundElement: null
                    };
                }

                const parsed = parseColor(
                    style.backgroundColor
                );

                if (parsed === null) {
                    return {
                        color: null,
                        reason: "Couleur de fond non interprétable",
                        backgroundElement: null
                    };
                }

                if (parsed.alpha === 1) {
                    return {
                        color: (
                            `rgb(${parsed.red}, `
                            + `${parsed.green}, ${parsed.blue})`
                        ),
                        reason: null,
                        backgroundElement: current
                    };
                }

                if (parsed.alpha > 0) {
                    return {
                        color: null,
                        reason: "Arrière-plan translucide",
                        backgroundElement: null
                    };
                }

                current = current.parentElement;
            }

            return {
                color: null,
                reason: "Aucun fond opaque identifié",
                backgroundElement: null
            };
        }

        function textRects(textNode) {
            const range = document.createRange();
            range.selectNodeContents(textNode);

            return Array.from(
                range.getClientRects()
            ).filter(
                rect => rect.width > 0 && rect.height > 0
            );
        }

        function rectInsideViewport(rect) {
            return (
                rect.left >= 0 &&
                rect.top >= 0 &&
                rect.right <= window.innerWidth &&
                rect.bottom <= window.innerHeight
            );
        }

        function rectInsideBackground(rect, backgroundRect) {
            return (
                rect.left >= backgroundRect.left &&
                rect.top >= backgroundRect.top &&
                rect.right <= backgroundRect.right &&
                rect.bottom <= backgroundRect.bottom
            );
        }

        function nextFrame() {
            return new Promise(
                resolve => requestAnimationFrame(resolve)
            );
        }

        async function scrollTextIntoView(element, textNode) {
            /*
             * Défilement initial de l'élément.
             * On utilise "instant" pour éviter d'attendre
             * une animation CSS de défilement.
             */
            element.scrollIntoView({
                block: "center",
                inline: "nearest",
                behavior: "instant"
            });

            await nextFrame();

            /*
             * Si le texte se trouve dans une grande boîte,
             * on tente de centrer le premier rectangle textuel.
             */
            const rects = textRects(textNode);

            if (!rects.length) {
                return;
            }

            const rect = rects[0];

            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;

            const outsideViewport = (
                centerX < 0 ||
                centerX >= window.innerWidth ||
                centerY < 0 ||
                centerY >= window.innerHeight
            );

            if (outsideViewport) {
                window.scrollBy({
                    top: centerY - window.innerHeight / 2,
                    left: centerX - window.innerWidth / 2,
                    behavior: "instant"
                });

                await nextFrame();
            }
        }

        function inspectTextGeometry(
            element,
            textNode,
            backgroundElement
        ) {
            /*
             * IMPORTANT :
             * Les rectangles doivent être recalculés APRES
             * le défilement de la page.
             */
            const rects = textRects(textNode);

            if (!rects.length) {
                return "Aucune zone de texte mesurable";
            }

            if (!backgroundElement) {
                return "Aucun élément de fond identifié";
            }

            const backgroundRect =
                backgroundElement.getBoundingClientRect();

            for (const rect of rects) {
                /*
                 * Si l'ensemble d'un rectangle textuel
                 * ne rentre pas dans le viewport, on ne
                 * peut pas valider toute sa géométrie avec
                 * un seul contrôle.
                 */
                if (!rectInsideViewport(rect)) {
                    return (
                        "Fragment de texte partiellement "
                        + "hors du viewport après défilement"
                    );
                }

                if (
                    !rectInsideBackground(
                        rect,
                        backgroundRect
                    )
                ) {
                    return (
                        "Texte hors de la zone "
                        + "du fond identifié"
                    );
                }

                /*
                 * Plusieurs points de contrôle :
                 * centre, quart gauche, quart droit.
                 *
                 * Cela réduit certains faux négatifs,
                 * sans garantir l'absence de recouvrement.
                 */
                const points = [
                    [
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                    ],
                    [
                        rect.left + rect.width * 0.25,
                        rect.top + rect.height / 2
                    ],
                    [
                        rect.left + rect.width * 0.75,
                        rect.top + rect.height / 2
                    ]
                ];

                for (const [x, y] of points) {
                    const topElement =
                        document.elementFromPoint(x, y);

                    if (!topElement) {
                        return (
                            "Zone de texte non détectable"
                        );
                    }

                    /*
                     * L'élément du texte ou un de ses
                     * descendants est accepté.
                     * Un élément extérieur reste suspect.
                     */
                    if (
                        topElement !== element &&
                        !element.contains(topElement)
                    ) {
                        return (
                            "Superposition possible "
                            + "devant le texte"
                        );
                    }
                }
            }

            return null;
        }

        for (
            const element of document.querySelectorAll("body *")
        ) {
            if (
                excludedTags.has(
                    element.tagName.toLowerCase()
                ) ||
                !isVisible(element)
            ) {
                continue;
            }

            const textNodes = Array.from(
                element.childNodes
            ).filter(
                node =>
                    node.nodeType === Node.TEXT_NODE &&
                    node.textContent.trim()
            );

            if (!textNodes.length) {
                continue;
            }

            const background = resolveBackground(element);

            /*
             * Les observations d'un même élément
             * réutilisent le style calculé.
             */
            const style = getComputedStyle(element);

            for (const textNode of textNodes) {
                const text = textNode.textContent.trim();

                if (!text) {
                    continue;
                }

                /*
                 * En V3.1, on fait défiler la page
                 * avant le contrôle de superposition.
                 */
                await scrollTextIntoView(
                    element,
                    textNode
                );

                let reviewReason = background.reason;

                if (!reviewReason) {
                    reviewReason = inspectTextGeometry(
                        element,
                        textNode,
                        background.backgroundElement
                    );
                }

                if (
                    !reviewReason &&
                    style.textShadow !== "none"
                ) {
                    reviewReason = "Ombre de texte présente";
                }

                observations.push({
                    element: labelOf(element),
                    text,
                    color: style.color,
                    background_color: reviewReason
                        ? null
                        : background.color,
                    font_size_px: parseFloat(
                        style.fontSize
                    ),
                    font_weight: parseInt(
                        style.fontWeight,
                        10
                    ) || 400,
                    review_reason: reviewReason
                });
            }
        }

        return observations;
    }
    """

    extracted = await _extract_from_page(
        html_path,
        javascript,
    )

    return [TextStyleObservation(**item) for item in extracted]


@dataclass
class NonTextStyleObservation:
    """
    Observation d'un composant visuel par Playwright.

    Les couleurs décrivent une comparaison CSS candidate.
    Elles ne prouvent pas, à elles seules, que cette comparaison
    est suffisante pour conclure au critère RGAA 3.3.

    review_reason est renseigné lorsque la comparaison doit
    être confirmée avant de produire un verdict.
    """

    element: str
    kind: str
    comparison: str
    foreground_color: str | None
    background_color: str | None
    state: str | None = None
    review_reason: str | None = None


async def extract_non_text_styles(
    html_path: Path,
) -> list[NonTextStyleObservation]:
    """
    Observe les bordures visibles des composants de formulaire.

    Périmètre initial :
    - input visibles, hors boutons et contrôles spéciaux ;
    - select ;
    - textarea.

    Seules les bordures uniformes, opaques et d'au moins
    un pixel CSS sont prises en compte.

    Le fond de référence est recherché dans les ancêtres.
    Il ne s'agit pas encore d'une validation géométrique
    exhaustive de toutes les surfaces adjacentes.

    Chaque observation reste soumise à une vérification
    d'applicabilité avant conversion en échantillon RGAA 3.3.
    """

    javascript = r"""
    () => {
        const observations = [];

        const selector = [
            'input:not([type="hidden"])',
            'select',
            'textarea'
        ].join(", ");

        const excludedInputTypes = new Set([
            "button",
            "submit",
            "reset",
            "image",
            "checkbox",
            "radio",
            "range",
            "color",
            "file"
        ]);

        function labelOf(element) {
            if (element.id) {
                return (
                    element.tagName.toLowerCase()
                    + "#"
                    + element.id
                );
            }

            const parts = [];
            let current = element;

            while (
                current &&
                current.nodeType === Node.ELEMENT_NODE
            ) {
                let part = current.tagName.toLowerCase();
                const parent = current.parentElement;

                if (parent) {
                    const siblings = Array.from(
                        parent.children
                    ).filter(
                        child => child.tagName === current.tagName
                    );

                    if (siblings.length > 1) {
                        part += (
                            ":nth-of-type("
                            + (siblings.indexOf(current) + 1)
                            + ")"
                        );
                    }
                }

                parts.unshift(part);
                current = parent;
            }

            return parts.join(" > ");
        }

        function opaqueColor(value) {
            const match = value.match(
                /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/
            );

            if (!match) {
                return null;
            }

            const channels = [
                Number(match[1]),
                Number(match[2]),
                Number(match[3])
            ];

            const alpha = match[4] === undefined
                ? 1
                : Number(match[4]);

            if (
                channels.some(
                    channel =>
                        !Number.isInteger(channel) ||
                        channel < 0 ||
                        channel > 255
                ) ||
                alpha !== 1
            ) {
                return null;
            }

            return (
                "rgb("
                + channels.join(", ")
                + ")"
            );
        }

        function visible(element) {
            let current = element;

            while (current) {
                const style = getComputedStyle(current);

                if (
                    style.display === "none" ||
                    style.visibility !== "visible" ||
                    current.hasAttribute("hidden") ||
                    current.hasAttribute("inert")
                ) {
                    return false;
                }

                current = current.parentElement;
            }

            const rect = element.getBoundingClientRect();

            return rect.width > 0 && rect.height > 0;
        }

        function hasComplexEffects(style) {
            return (
                Number(style.opacity) !== 1 ||
                style.filter !== "none" ||
                style.backdropFilter !== "none" ||
                style.mixBlendMode !== "normal" ||
                style.backgroundImage !== "none" ||
                style.maskImage !== "none" ||
                style.clipPath !== "none"
            );
        }

        function parentBackground(element) {
            let current = element.parentElement;

            while (current) {
                const style = getComputedStyle(current);

                if (hasComplexEffects(style)) {
                    return {
                        color: null,
                        reason: "Effet CSS complexe sur un ancêtre"
                    };
                }

                const color = opaqueColor(
                    style.backgroundColor
                );

                if (color !== null) {
                    return {
                        color,
                        reason: null
                    };
                }

                const transparent = (
                    style.backgroundColor === "transparent" ||
                    style.backgroundColor === "rgba(0, 0, 0, 0)"
                );

                if (!transparent) {
                    return {
                        color: null,
                        reason: "Arrière-plan translucide ou inconnu"
                    };
                }

                current = current.parentElement;
            }

            return {
                color: null,
                reason: "Aucun fond opaque identifié"
            };
        }

        for (
            const element of document.querySelectorAll(selector)
        ) {
            if (!visible(element)) {
                continue;
            }

            if (
                element.tagName.toLowerCase() === "input" &&
                excludedInputTypes.has(
                    (element.type || "").toLowerCase()
                )
            ) {
                continue;
            }

            const style = getComputedStyle(element);

            const borderStyles = [
                style.borderTopStyle,
                style.borderRightStyle,
                style.borderBottomStyle,
                style.borderLeftStyle
            ];

            const borderWidths = [
                style.borderTopWidth,
                style.borderRightWidth,
                style.borderBottomWidth,
                style.borderLeftWidth
            ].map(value => parseFloat(value));

            const borderColors = [
                style.borderTopColor,
                style.borderRightColor,
                style.borderBottomColor,
                style.borderLeftColor
            ];

            const uniformBorder = (
                borderStyles.every(
                    value => value === "solid"
                ) &&
                borderWidths.every(
                    value =>
                        Number.isFinite(value) &&
                        value >= 1 &&
                        value === borderWidths[0]
                ) &&
                borderColors.every(
                    value => value === borderColors[0]
                )
            );

            if (!uniformBorder) {
                continue;
            }

            const foreground = opaqueColor(
                borderColors[0]
            );

            const background = parentBackground(element);

            let reviewReason = (
                "Applicabilité de la bordure et surface "
                + "adjacente à confirmer manuellement"
            );

            if (foreground === null) {
                reviewReason = (
                    "Couleur de bordure non opaque "
                    + "ou non interprétable"
                );
            } else if (hasComplexEffects(style)) {
                reviewReason = (
                    "Effet CSS complexe sur le composant"
                );
            } else if (background.reason !== null) {
                reviewReason = background.reason;
            }

            observations.push({
                element: labelOf(element),
                kind: "component",
                comparison: "background",
                foreground_color: foreground,
                background_color: background.color,
                state: "default",
                review_reason: reviewReason
            });
        }

        return observations;
    }
    """

    extracted = await _extract_from_page(
        html_path,
        javascript,
    )

    return [NonTextStyleObservation(**item) for item in extracted]
