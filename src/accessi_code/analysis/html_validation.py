"""
Contrôle déterministe du code source HTML (RGAA 8.2.1).

Couvre les cinq conditions du test, avec le parseur de la bibliothèque standard
(numéros de ligne exacts, aucune dépendance) :

- règles d'écriture : balise auto-fermante sur un élément non vide, balise de
  fermeture sur un élément vide, élément obsolète en HTML5, id vide ou contenant
  un espace ;
- imbrication : élément fermé avant ses enfants ;
- ouverture et fermeture : balise fermante sans ouvrante, élément jamais fermé ;
- id uniques ;
- attributs non doublés.

Les fermetures implicites autorisées par HTML (``p``, ``li``, ``td``…) ne sont
pas des erreurs. Ce contrôle ne remplace pas le validateur du W3C : il ne vérifie
pas le modèle de contenu complet (élément autorisé à tel endroit).
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "param"}
)
# Éléments obsolètes qui étaient vides en HTML 4 : signalés comme obsolètes, pas comme mal fermés.
LEGACY_VOID_ELEMENTS = frozenset({"basefont", "bgsound", "frame", "isindex", "keygen", "command", "spacer"})

# Éléments dont la balise de fermeture peut être omise.
OPTIONAL_END = frozenset(
    {
        "html",
        "head",
        "body",
        "p",
        "li",
        "dt",
        "dd",
        "rt",
        "rp",
        "optgroup",
        "option",
        "colgroup",
        "caption",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
    }
)

# Balises ouvrantes qui ferment implicitement un paragraphe ouvert.
P_CLOSERS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "details",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hgroup",
        "hr",
        "main",
        "menu",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    }
)

# Fermetures implicites : balise ouvrante → éléments ouverts qu'elle ferme, jusqu'à la limite.
IMPLIED_CLOSE: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "li": (frozenset({"li"}), frozenset({"ul", "ol", "menu"})),
    "dt": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "dd": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "tr": (frozenset({"tr", "td", "th"}), frozenset({"table", "thead", "tbody", "tfoot"})),
    "td": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "th": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "thead": (frozenset({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}), frozenset({"table"})),
    "tbody": (frozenset({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}), frozenset({"table"})),
    "tfoot": (frozenset({"thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup"}), frozenset({"table"})),
    "option": (frozenset({"option"}), frozenset({"select", "datalist", "optgroup"})),
    "optgroup": (frozenset({"option", "optgroup"}), frozenset({"select"})),
    "rt": (frozenset({"rt", "rp"}), frozenset({"ruby"})),
    "rp": (frozenset({"rt", "rp"}), frozenset({"ruby"})),
}

OBSOLETE_ELEMENTS = frozenset(
    {
        "acronym",
        "applet",
        "basefont",
        "bgsound",
        "big",
        "blink",
        "center",
        "dir",
        "font",
        "frame",
        "frameset",
        "isindex",
        "listing",
        "marquee",
        "multicol",
        "nextid",
        "nobr",
        "noembed",
        "noframes",
        "plaintext",
        "spacer",
        "strike",
        "tt",
        "xmp",
    }
)

FOREIGN_ROOTS = frozenset({"svg", "math"})


@dataclass(frozen=True)
class ValidationError:
    line: int
    column: int
    condition: str
    message: str


class _Checker(HTMLParser):
    def __init__(self, *, html5: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.html5 = html5
        self.errors: list[ValidationError] = []
        self.stack: list[tuple[str, int]] = []
        self.ids: dict[str, int] = {}

    # -- utilitaires ---------------------------------------------------

    def _error(self, condition: str, message: str) -> None:
        line, column = self.getpos()
        self.errors.append(ValidationError(line, column + 1, condition, message))

    def _in_foreign(self) -> bool:
        return any(name in FOREIGN_ROOTS for name, _ in self.stack)

    def _check_attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        seen: set[str] = set()
        for name, value in attrs:
            if name in seen:
                self._error("attributs", f"L'attribut « {name} » est doublé sur l'élément <{tag}>.")
            seen.add(name)
            if name == "id":
                identifier = value or ""
                if not identifier or any(character.isspace() for character in identifier):
                    self._error(
                        "écriture", f"La valeur d'id « {identifier} » de <{tag}> est vide ou contient un espace."
                    )
                elif identifier in self.ids:
                    self._error(
                        "id",
                        f"L'id « {identifier} » est déjà utilisé ligne {self.ids[identifier]} : il doit être unique.",
                    )
                else:
                    self.ids[identifier] = self.getpos()[0]
        if self.html5 and tag in OBSOLETE_ELEMENTS and not self._in_foreign():
            self._error("écriture", f"L'élément <{tag}> est obsolète en HTML5.")

    def _close_implied(self, tag: str) -> None:
        if tag in P_CLOSERS and self.stack and self.stack[-1][0] == "p":
            self.stack.pop()
        rule = IMPLIED_CLOSE.get(tag)
        if rule is None:
            return
        closed, boundary = rule
        for position in range(len(self.stack) - 1, -1, -1):
            name = self.stack[position][0]
            if name in boundary:
                return
            if name in closed:
                if all(item in OPTIONAL_END for item, _ in self.stack[position:]):
                    del self.stack[position:]
                return

    # -- événements du parseur ------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check_attributes(tag, attrs)
        if tag in VOID_ELEMENTS | LEGACY_VOID_ELEMENTS and not self._in_foreign():
            return
        if not self._in_foreign():
            self._close_implied(tag)
        self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check_attributes(tag, attrs)
        if tag in VOID_ELEMENTS | LEGACY_VOID_ELEMENTS or self._in_foreign() or tag in FOREIGN_ROOTS:
            return
        self._error("écriture", f"<{tag}/> : la syntaxe auto-fermante n'est pas permise pour cet élément en HTML.")
        self._close_implied(tag)
        self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS | LEGACY_VOID_ELEMENTS and not self._in_foreign():
            self._error("fermeture", f"</{tag}> : un élément vide n'a pas de balise de fermeture.")
            return
        if tag == "p" and not any(name == "p" for name, _ in self.stack):
            self._error("fermeture", "</p> ferme un paragraphe déjà fermé implicitement ou jamais ouvert.")
            return
        if not any(name == tag for name, _ in self.stack):
            self._error("fermeture", f"</{tag}> ne correspond à aucune balise ouvrante.")
            return
        while self.stack:
            name, line = self.stack.pop()
            if name == tag:
                return
            if name not in OPTIONAL_END and not self._in_foreign():
                self._error("imbrication", f"<{name}> ouvert ligne {line} n'est pas fermé avant </{tag}>.")

    def close(self) -> None:
        super().close()
        for name, line in self.stack:
            if name not in OPTIONAL_END:
                self.errors.append(
                    ValidationError(line, 1, "fermeture", f"<{name}> ouvert ligne {line} n'est jamais fermé.")
                )
        self.stack.clear()


def validate_html(source: str, *, html5: bool = True) -> list[ValidationError]:
    """Erreurs du code source, dans l'ordre du document."""
    checker = _Checker(html5=html5)
    checker.feed(source)
    checker.close()
    return sorted(checker.errors, key=lambda error: (error.line, error.column))
