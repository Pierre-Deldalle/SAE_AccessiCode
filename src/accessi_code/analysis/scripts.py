"""
Lecture des scripts d'une page : sources, minuteurs et déclencheur d'un appel.

Analyse lexicale volontairement simple (pas d'interpréteur JavaScript) :
- les commentaires sont effacés et les accolades ou parenthèses contenues dans
  les chaînes sont neutralisées, ce qui permet d'apparier les blocs ;
- le déclencheur d'un appel est déduit des blocs qui l'entourent (gestionnaire
  d'événement, chargement de la page, minuteur, fonction nommée…).

Aucune fonction ne décide d'un statut RGAA : les tests interprètent les résultats.
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from accessi_code.models.audit_context import AuditContext

_JS_TYPES = {"", "text/javascript", "application/javascript", "module", "text/ecmascript", "application/ecmascript"}

USER_EVENTS = frozenset(
    {
        "click",
        "dblclick",
        "auxclick",
        "contextmenu",
        "mousedown",
        "mouseup",
        "pointerdown",
        "pointerup",
        "touchstart",
        "touchend",
        "keydown",
        "keyup",
        "keypress",
        "submit",
        "change",
        "input",
    }
)
LOAD_EVENTS = frozenset({"load", "domcontentloaded", "readystatechange", "pageshow"})

_CONTROL = re.compile(r"^\s*(?:else\s+if|if|else|for|while|do|switch|try|catch|finally|with)\b")
_LISTENER = re.compile(r"addEventListener\s*\(\s*['\"`]([\w-]+)['\"`]", re.IGNORECASE)
_ON_PROPERTY = re.compile(r"\.on([a-z]+)\s*=\s*(?:async\s+)?(?:function\b|\(|[\w$]+\s*=>)", re.IGNORECASE)
_JQUERY_ON = re.compile(r"\.on\s*\(\s*['\"]([\w-]+)", re.IGNORECASE)
_JQUERY_SHORTCUT = re.compile(r"\.(click|dblclick|mousedown|mouseup|keydown|keyup|keypress|submit|change)\s*\(")
_JQUERY_READY = re.compile(
    r"\$\s*\(\s*document\s*\)\s*\.\s*ready\s*\(|^\s*\$\s*\(\s*(?:function\b|\()|jQuery\s*\(\s*function"
)
_TIMER = re.compile(r"\b(?:setTimeout|setInterval|requestAnimationFrame)\s*\(")
_IIFE = re.compile(r"^\s*[!(]\s*(?:async\s*)?(?:function\b|\()")
_SYNC_CALLBACK = re.compile(r"\.(?:forEach|map|filter|reduce|some|every|find|then|catch|finally)\s*\(")
_DECLARATION = re.compile(r"\bfunction\s*\*?\s*([\w$]+)\s*\(")
_ASSIGNED_FUNCTION = re.compile(
    r"([\w$]+)\s*[:=]\s*(?:async\s+)?(?:function\b[^(]*\(|(?:\([^()]*\)|[\w$]+)\s*=>)",
)
_METHOD = re.compile(r"^\s*(?:static\s+)?(?:async\s+)?([\w$]+)\s*\([^()]*\)\s*$")
_ANONYMOUS = re.compile(r"\bfunction\b|=>")
_JS_KEYWORDS = frozenset({"if", "for", "while", "switch", "catch", "function", "return", "typeof", "new", "with"})


class Trigger(str, Enum):
    """Ce qui provoque l'exécution d'un morceau de code."""

    USER = "user"  # action de l'utilisateur (clic, touche, soumission…)
    LOAD = "load"  # chargement de la page
    TIMER = "timer"  # minuteur (setTimeout, setInterval…)
    UNKNOWN = "unknown"  # indéterminé (autre événement, fonction appelée ailleurs)


@dataclass
class ScriptSource:
    """Code d'un script de la page (balise script ou fichier fourni)."""

    label: str
    code: str
    masked: str = ""
    # Comme ``masked``, avec tout le contenu des chaînes effacé (recherche d'identifiants).
    bare: str = ""
    pairs: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.masked = mask_code(self.code)
        self.bare = mask_code(self.code, blank_strings=True)
        self.pairs = _brace_pairs(self.masked)

    def snippet(self, position: int, before: int = 120, after: int = 220) -> str:
        return " ".join(self.code[max(0, position - before) : position + after].split())


@dataclass
class TriggerInfo:
    trigger: Trigger
    detail: str = ""
    # Vrai si l'appel est dans un bloc conditionnel (if, boucle, try…).
    conditional: bool = False


@dataclass
class TimerCall:
    """Appel à setTimeout ou setInterval."""

    source: ScriptSource
    position: int
    kind: str
    callback: str
    delay_ms: float | None


# ----------------------------------------------------------------------
# Sources
# ----------------------------------------------------------------------


def mask_code(code: str, blank_strings: bool = False) -> str:
    """
    Code de même longueur où les commentaires sont effacés et où les accolades,
    parenthèses et points-virgules des chaînes sont remplacés par des espaces
    (tout le contenu des chaînes si ``blank_strings``).
    """
    result = list(code)
    index, length = 0, len(code)
    while index < length:
        char = code[index]
        if code.startswith("//", index):
            end = code.find("\n", index)
            end = length if end == -1 else end
            result[index:end] = " " * (end - index)
            index = end
        elif code.startswith("/*", index):
            end = code.find("*/", index + 2)
            end = length if end == -1 else end + 2
            result[index:end] = [c if c == "\n" else " " for c in code[index:end]]
            index = end
        elif char in "'\"`":
            index += 1
            while index < length and code[index] != char:
                if code[index] == "\\":
                    index += 1
                elif code[index] == "\n" and char != "`":
                    break
                elif blank_strings or code[index] in "{}();":
                    result[index] = " "
                index += 1
            index += 1
        else:
            index += 1
    return "".join(result)


def _brace_pairs(masked: str) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    stack: list[int] = []
    for index, char in enumerate(masked):
        if char == "{":
            stack.append(index)
        elif char == "}" and stack:
            pairs.append((stack.pop(), index))
    for start in stack:
        pairs.append((start, len(masked)))
    return pairs


def _is_javascript(script: Tag) -> bool:
    kind = str(script.get("type") or "").strip().lower()
    return kind in _JS_TYPES


def page_scripts(context: AuditContext) -> list[ScriptSource]:
    """
    Scripts de la page : balises script en ligne, puis fichiers JavaScript
    référencés par ``script src`` ou fournis avec l'audit.
    """
    sources: list[ScriptSource] = []
    seen: set[Path] = set()
    soup = context.dom if isinstance(context.dom, BeautifulSoup) else None
    base = context.html_path.parent if context.html_path else context.workspace_path

    if soup is not None:
        for index, script in enumerate(soup.find_all("script")):
            if not _is_javascript(script):
                continue
            src = str(script.get("src") or "").strip()
            if src:
                parsed = urlparse(src)
                if parsed.scheme or parsed.netloc:
                    continue
                path = (base / parsed.path.lstrip("/")).resolve()
                if path.is_file() and path not in seen:
                    seen.add(path)
                    sources.append(ScriptSource(path.name, _read(path)))
                continue
            code = script.string or script.get_text()
            if code and code.strip():
                sources.append(ScriptSource(f"script[index={index}]", code))

    for audit_file in context.files:
        path = Path(audit_file.path).resolve()
        if audit_file.extension == ".js" and path.is_file() and path not in seen:
            seen.add(path)
            sources.append(ScriptSource(path.name, _read(path)))
    return sources


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


@dataclass
class InlineHandler:
    element: Tag
    event: str
    code: str


def inline_handlers(soup: BeautifulSoup) -> list[InlineHandler]:
    """Gestionnaires d'événement écrits en attribut (onclick="…"), dans l'ordre du document."""
    handlers: list[InlineHandler] = []
    for element in soup.find_all(True):
        for name, value in element.attrs.items():
            name = str(name).lower()
            if name.startswith("on") and isinstance(value, str) and value.strip():
                handlers.append(InlineHandler(element, name[2:], value))
    return handlers


# ----------------------------------------------------------------------
# Déclencheur d'un appel
# ----------------------------------------------------------------------


def _header(masked: str, brace: int) -> str:
    start = max(masked.rfind(";", 0, brace), masked.rfind("{", 0, brace), masked.rfind("}", 0, brace))
    return masked[start + 1 : brace][-300:]


def event_trigger(event: str) -> Trigger:
    event = event.lower()
    if event in USER_EVENTS:
        return Trigger.USER
    if event in LOAD_EVENTS:
        return Trigger.LOAD
    return Trigger.UNKNOWN


def _header_event(header: str) -> str | None:
    for pattern in (_LISTENER, _ON_PROPERTY, _JQUERY_ON, _JQUERY_SHORTCUT):
        matches = list(pattern.finditer(header))
        if matches:
            return matches[-1].group(1).lower()
    if _JQUERY_READY.search(header):
        return "load"
    return None


def _function_name(header: str) -> str | None:
    for pattern in (_DECLARATION, _ASSIGNED_FUNCTION):
        matches = list(pattern.finditer(header))
        if matches:
            return matches[-1].group(1)
    match = _METHOD.match(header)
    if match and match.group(1) not in _JS_KEYWORDS:
        return match.group(1)
    return None


def trigger_at(
    sources: list[ScriptSource],
    source: ScriptSource,
    position: int,
    soup: BeautifulSoup | None = None,
    _depth: int = 0,
    _visited: frozenset[str] = frozenset(),
) -> TriggerInfo:
    """
    Déclencheur du code situé à ``position`` dans ``source`` : on remonte les
    blocs englobants jusqu'au premier qui détermine l'exécution.
    """
    conditional = False
    enclosing = sorted((pair for pair in source.pairs if pair[0] < position < pair[1]), reverse=True)
    # Fonction fléchée sans accolades (« () => appel() ») : le début de l'instruction sert d'en-tête.
    statement = _header(source.masked, position)
    headers = [statement] if "=>" in statement else []
    headers += [_header(source.masked, brace) for brace, _end in enclosing]
    for header in headers:
        if _CONTROL.match(header):
            conditional = True
            continue
        event = _header_event(header)
        if event is not None:
            return TriggerInfo(event_trigger(event), f"événement {event}", conditional)
        if _TIMER.search(header):
            return TriggerInfo(Trigger.TIMER, "minuteur", conditional)
        if _IIFE.match(header) or _SYNC_CALLBACK.search(header):
            continue
        name = _function_name(header)
        if name:
            info = function_trigger(sources, name, soup, _depth + 1, _visited | {name})
            info.conditional = info.conditional or conditional
            return info
        if _ANONYMOUS.search(header):
            return TriggerInfo(Trigger.UNKNOWN, "fonction transmise à un autre code", conditional)
    return TriggerInfo(Trigger.LOAD, "exécuté au chargement du script", conditional)


def function_trigger(
    sources: list[ScriptSource],
    name: str,
    soup: BeautifulSoup | None = None,
    _depth: int = 1,
    _visited: frozenset[str] = frozenset(),
) -> TriggerInfo:
    """Déclencheur d'une fonction nommée, d'après tous les endroits où elle est utilisée."""
    if _depth > 4:
        return TriggerInfo(Trigger.UNKNOWN, f"fonction {name} : appels trop indirects")
    infos: list[TriggerInfo] = []
    reference = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
    for source in sources:
        for match in reference.finditer(source.bare):
            before = source.masked[max(0, match.start() - 200) : match.start()]
            after = source.masked[match.end() : match.end() + 40]
            if re.search(r"(?:\bfunction\s*\*?\s*|\b(?:const|let|var)\s+)$", before) or re.match(
                r"\s*[:=](?!=)", after
            ):
                continue  # déclaration de la fonction elle-même
            listener = re.search(r"addEventListener\s*\(\s*['\"`]([\w-]+)['\"`]\s*,\s*$", before)
            on_property = re.search(r"\.on([a-z]+)\s*=\s*$", before, re.IGNORECASE)
            if listener or on_property:
                event = (listener or on_property).group(1)
                infos.append(TriggerInfo(event_trigger(event), f"{name} : événement {event.lower()}"))
            elif re.search(r"\b(?:setTimeout|setInterval|requestAnimationFrame)\s*\(\s*$", before):
                infos.append(TriggerInfo(Trigger.TIMER, f"{name} : minuteur"))
            elif re.match(r"\s*\(", after):
                opening = source.masked.find("(", match.end())
                closing = matching_paren(source.masked, opening)
                if source.masked[closing + 1 : closing + 40].lstrip().startswith("{"):
                    continue  # définition de méthode : name(…) { … }
                if _inside_function(source, match.start(), name):
                    continue  # appel récursif
                info = trigger_at(sources, source, match.start(), soup, _depth, _visited)
                infos.append(TriggerInfo(info.trigger, f"{name} : {info.detail}", info.conditional))
            else:
                infos.append(TriggerInfo(Trigger.UNKNOWN, f"{name} : transmise à un autre code"))
    if soup is not None:
        call = re.compile(rf"(?<![\w$.]){re.escape(name)}\s*\(")
        for handler in inline_handlers(soup):
            if call.search(handler.code):
                infos.append(TriggerInfo(event_trigger(handler.event), f"{name} : attribut on{handler.event}"))
    return merge_triggers(infos, name)


def _inside_function(source: ScriptSource, position: int, name: str) -> bool:
    return any(
        brace < position < end and _function_name(_header(source.masked, brace)) == name for brace, end in source.pairs
    )


def merge_triggers(infos: list[TriggerInfo], name: str = "") -> TriggerInfo:
    """Chargement s'il y en a un, utilisateur si tous les appels le sont, sinon indéterminé."""
    if not infos:
        return TriggerInfo(Trigger.UNKNOWN, f"fonction {name} : aucun appel trouvé")
    for info in infos:
        if info.trigger is Trigger.LOAD:
            return info
    if all(info.trigger is Trigger.USER for info in infos):
        return TriggerInfo(Trigger.USER, infos[0].detail, any(info.conditional for info in infos))
    other = next(info for info in infos if info.trigger is not Trigger.USER)
    return TriggerInfo(
        other.trigger if other.trigger is Trigger.TIMER else Trigger.UNKNOWN, other.detail, other.conditional
    )


# ----------------------------------------------------------------------
# Appels, fonctions et minuteurs
# ----------------------------------------------------------------------


def matching_paren(masked: str, opening: int) -> int:
    """Position de la parenthèse fermante associée à ``opening`` (ou fin du texte)."""
    depth = 0
    for index in range(opening, len(masked)):
        char = masked[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                return index
    return len(masked)


def split_arguments(masked: str, opening: int, closing: int) -> list[tuple[int, int]]:
    """Positions (début, fin) des arguments d'un appel."""
    parts: list[tuple[int, int]] = []
    depth, start = 0, opening + 1
    for index in range(opening + 1, closing):
        char = masked[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append((start, index))
            start = index + 1
    if masked[start:closing].strip():
        parts.append((start, closing))
    return parts


def function_body(sources: list[ScriptSource], name: str) -> str | None:
    """Corps d'une fonction nommée (déclaration, affectation ou méthode)."""
    patterns = (
        re.compile(rf"\bfunction\s*\*?\s*{re.escape(name)}\s*\("),
        re.compile(
            rf"(?<![\w$.]){re.escape(name)}\s*[:=]\s*(?:async\s+)?(?:function\b[^(]*\(|(?:\([^()]*\)|[\w$]+)\s*=>)"
        ),
    )
    for source in sources:
        for pattern in patterns:
            match = pattern.search(source.masked)
            if match:
                brace = source.masked.find("{", match.end())
                if brace != -1:
                    end = next((close for open_, close in source.pairs if open_ == brace), len(source.code))
                    return source.code[brace + 1 : end]
    return None


def callable_code(sources: list[ScriptSource], source: ScriptSource, start: int, end: int) -> str:
    """Code d'un argument « fonction » : son texte, ou le corps de la fonction nommée qu'il désigne."""
    text = source.code[start:end].strip()
    if re.fullmatch(r"[\w$.]+", text):
        body = function_body(sources, text.split(".")[-1])
        return body if body is not None else text
    return text


_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def numeric_value(expression: str) -> float | None:
    """Valeur d'une expression numérique littérale simple (``5000``, ``30 * 1000``)."""
    expression = expression.strip().replace("_", "")
    if not re.fullmatch(r"[\d.eE\s+\-*/()]+", expression or "x"):
        return None
    try:
        return _evaluate(ast.parse(expression, mode="eval").body)
    except SyntaxError, ValueError, ZeroDivisionError, TypeError:
        return None


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand)
    raise ValueError("expression non numérique")


_TIMER_CALL = re.compile(r"(?<![\w$.])(?:window\.)?(setTimeout|setInterval)\s*\(")


def timer_calls(sources: list[ScriptSource]) -> list[TimerCall]:
    """Appels à setTimeout / setInterval avec le code rappelé et le délai (ms) s'il est littéral."""
    calls: list[TimerCall] = []
    for source in sources:
        for match in _TIMER_CALL.finditer(source.masked):
            opening = match.end() - 1
            closing = matching_paren(source.masked, opening)
            arguments = split_arguments(source.masked, opening, closing)
            if not arguments:
                continue
            callback = callable_code(sources, source, *arguments[0])
            delay = numeric_value(source.code[arguments[1][0] : arguments[1][1]]) if len(arguments) > 1 else 0.0
            calls.append(TimerCall(source, match.start(), match.group(1), callback, delay))
    return calls


@dataclass
class ListenerCall:
    """Écoute d'un événement : addEventListener, propriété on…, ou attribut HTML."""

    event: str
    code: str
    label: str
    source: ScriptSource | None = None
    position: int = 0
    element: Tag | None = None


def event_listeners(sources: list[ScriptSource], soup: BeautifulSoup | None, events: set[str]) -> list[ListenerCall]:
    """Écoutes des événements ``events`` (noms en minuscules, sans « on »)."""
    listeners: list[ListenerCall] = []
    pattern = re.compile(r"addEventListener\s*\(\s*['\"`]([\w-]+)['\"`]\s*,", re.IGNORECASE)
    for source in sources:
        for match in pattern.finditer(source.masked):
            event = match.group(1).lower()
            if event not in events:
                continue
            opening = source.masked.rfind("(", 0, match.end())
            closing = matching_paren(source.masked, opening)
            arguments = split_arguments(source.masked, opening, closing)
            code = callable_code(sources, source, *arguments[1]) if len(arguments) > 1 else ""
            listeners.append(ListenerCall(event, code, source.label, source, match.start()))
        for match in re.finditer(r"\.on([a-z]+)\s*=(?!=)", source.masked, re.IGNORECASE):
            event = match.group(1).lower()
            if event not in events:
                continue
            end = source.masked.find(";", match.end())
            brace = source.masked.find("{", match.end())
            if brace != -1 and (end == -1 or brace < end):
                close = next((c for o, c in source.pairs if o == brace), len(source.code))
                code = source.code[brace + 1 : close]
            else:
                code = callable_code(sources, source, match.end(), end if end != -1 else len(source.code))
            listeners.append(ListenerCall(event, code, source.label, source, match.start()))
    if soup is not None:
        for handler in inline_handlers(soup):
            if handler.event in events:
                listeners.append(
                    ListenerCall(handler.event, handler.code, f"attribut on{handler.event}", element=handler.element)
                )
    return listeners
