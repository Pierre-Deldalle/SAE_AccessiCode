"""Décisions RGAA thème 1. DOM en priorité, preuves sémantiques vérifiées sinon revue.

Aucun appel IA: un audit ne doit pas générer 2 appels Ollama par image et par test.
"""
from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from accessi_code.analysis.image_rgaa import (
    alternative,
    captcha_marker,
    caption,
    has_caption,
    has_description_mechanism,
    has_detailed_description,
    identifier,
    image_elements,
    is_decorative,
    is_functional,
    proof,
    role,
    semantic_alternatives,
    text_attr,
    text_refs,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import Finding, TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest

# Une classe concrète par numéro de test est déclarée dans criterion_1_X.py.
KINDS = {
    '1.1': ('img','area','input','img','svg','object','embed','canvas'),
    '1.2': ('img','area','object','svg','canvas','embed'),
    '1.3': ('img','area','input','object','embed','svg','canvas','canvas','all'),
    '1.4': ('img','area','input','object','embed','svg','canvas'),
    '1.5': ('all','input'),
    '1.6': ('img','object','embed','input','svg','svg','canvas','canvas','all','img'),
    '1.7': ('img','input','object','embed','svg','canvas'),
    '1.8': ('img','input','object','embed','canvas','svg'),
    '1.9': ('img','object','embed','svg','canvas'),
}


class ImageThemeTest(RGAATest):
    required_capabilities = frozenset({Capability.DOM})

    async def run(self, context: AuditContext, services: Any | None = None) -> TestResult:
        # Le service IA est intentionnellement inutilisé: seuls des faits DOM ou
        # des preuves externes documentées permettent de trancher.
        soup: BeautifulSoup = context.dom
        section, number = self.criterion_id, int(self.test_id.rsplit('.', 1)[1])
        kind = KINDS[section][number - 1]
        elements = image_elements(soup, kind)
        if section == '1.1' and number == 4:
            elements = [e for e in soup.find_all('img') if e.has_attr('ismap')]
        if section == '1.2' and number == 2:
            elements = [e for e in elements if not e.has_attr('href')]
        if section == '1.3' and number == 9:
            elements = [e for e in elements if semantic_alternatives(e, soup, _kind(e))]
        if section == '1.5' and number == 1:
            elements = [e for e in elements if e.name != 'input']
        if section == '1.3' and number == 8:
            elements = [e for e in elements if e.get_text(' ', strip=True)]
        if section == '1.6' and number in {6, 8}:
            elements = [e for e in elements if has_detailed_description(e, soup)]
        if section == '1.6' and number == 9:
            elements = [e for e in elements if text_attr(e, 'aria-describedby')]
        if section == '1.6' and number == 10:
            elements = [e for e in elements if e.get('role') == 'img' and e.name not in {'svg','canvas','object','embed','img','area','input'}]
        if section == '1.7':
            elements = [e for e in elements if has_detailed_description(e, soup)]
        if section == '1.9':
            elements = [e for e in elements if has_caption(e)]
        if section == '1.4' or section == '1.5':
            elements = [e for i, e in enumerate(elements) if captcha_marker(e) or proof(context, e, i).get('is_captcha') is True]
        if section == '1.4':
            elements = [e for e in elements if semantic_alternatives(e, soup, _kind(e))]
        if section == '1.2':
            elements = [e for i, e in enumerate(elements) if (
                is_decorative(e) or (e.name in {'img','area'} and e.has_attr('alt') and not text_attr(e, 'alt'))
                or proof(context, e, i).get('information_bearing') is False
            )]
        if section == '1.8' and number == 6:
            elements = [e for e in elements if not (e.find('text') and not e.find(['path','image']))]

        if not elements:
            return TestResult(self.test_id, section, TestStatus.NOT_APPLICABLE,
                              'Aucun élément dans le périmètre du test.', tested_elements=0)
        findings: list[Finding] = []
        counts = {s: 0 for s in ('pass','fail','needs_review','not_applicable')}
        for index, element in enumerate(elements):
            kind_here = _kind(element)
            evidence = proof(context, element, index)
            status, explanation = self._check(section, number, kind_here, element, soup, evidence)
            counts[status.value] += 1
            if status not in {TestStatus.PASS, TestStatus.NOT_APPLICABLE}:
                findings.append(Finding(
                    element=identifier(element, index), message=explanation,
                    recommendation='Corriger la structure ou documenter une vérification réelle (image_evidence).',
                    evidence={'test_id': self.test_id, 'verified_evidence': bool(evidence)},
                ))
        final = (TestStatus.FAIL if counts['fail'] else
                 TestStatus.NEEDS_REVIEW if counts['needs_review'] else
                 TestStatus.PASS if counts['pass'] else TestStatus.NOT_APPLICABLE)
        return TestResult(
            test_id=self.test_id, criterion_id=section, status=final,
            summary=f"{len(elements)} élément(s) : {counts['pass']} conforme(s), {counts['fail']} non conforme(s), {counts['needs_review']} à vérifier, {counts['not_applicable']} hors périmètre.",
            findings=findings, tested_elements=len(elements), metadata={'checks': counts, 'method': 'DOM + preuves vérifiées, sans appel IA'},
        )

    def _check(self, section: str, number: int, kind: str, element: Tag,
               soup: BeautifulSoup, ev: dict) -> tuple[TestStatus, str]:
        p, f, r = TestStatus.PASS, TestStatus.FAIL, TestStatus.NEEDS_REVIEW
        information = role(element, kind, ev)
        alts = alternative(element, soup, kind)
        if section == '1.1':
            if number == 4:
                if ev.get('equivalent_destinations') is True: return p, ''
                if ev.get('equivalent_destinations') is False: return f, 'Les destinations ne sont pas accessibles par un autre mécanisme.'
                return r, 'Les destinations réelles de la carte ismap ne sont pas vérifiables dans le DOM.'
            if number == 2 and not is_functional(element):
                return TestStatus.NOT_APPLICABLE, ''  # Zone non cliquable.
            if number == 5:
                if information is False: return TestStatus.NOT_APPLICABLE, ''
                if information is None: return r, 'Le rôle informationnel du SVG est inconnu.'
                if text_attr(element, 'role') != 'img': return f, 'SVG informatif sans role="img".'
                return (p, '') if alts else (f, 'SVG informatif sans alternative autorisée.')
            if information is False: return TestStatus.NOT_APPLICABLE, ''
            if information is None:
                # L'existence d'une alternative suffit pour 1.1 même si la pertinence relève de 1.3.
                if alts: return p, ''
                return r, 'Impossible de déterminer si cet élément sans alternative est informatif.'
            if number in {6,7,8}:
                if text_attr(element, 'role') == 'img' and alts: return p, ''
                if kind == 'canvas' and element.get_text(' ', strip=True): return p, ''
                if kind == 'canvas' and element.get_text(' ', strip=True): return p, ''
                if has_description_mechanism(element, soup, kind):
                    return r, 'Mécanisme alternatif présent, son équivalence et son accès doivent être vérifiés.'
                if ev.get('replacement_equivalent') is True: return p, ''
                return f, 'Image informative sans mécanisme alternatif RGAA valide.'
            return (p, '') if alts else (f, 'Image informative sans alternative textuelle autorisée.')

        if section == '1.2':
            if kind in {'img','area'}:
                no_extra = not any(text_attr(element, x) for x in ('title','aria-label','aria-labelledby'))
                okay = no_extra and ((element.has_attr('alt') and not text_attr(element, 'alt')) or is_decorative(element))
            elif kind == 'svg':
                descendants = [element, *element.find_all(True)]
                okay = text_attr(element, 'aria-hidden') == 'true' and not any(
                    text_attr(n, x) for n in descendants for x in ('aria-label','aria-labelledby','title'))
                okay = okay and not any(t.get_text(' ', strip=True) for t in element.find_all(['title','desc']))
            else:
                okay = text_attr(element, 'aria-hidden') == 'true' and not any(
                    text_attr(element, x) for x in ('title','aria-label','aria-labelledby'))
                if kind in {'object','canvas'}:
                    okay = okay and not element.get_text(' ', strip=True)
            return (p, '') if okay else (f, 'L’image déclarée décorative expose une alternative ou n’est pas masquée conformément au test.')

        if section == '1.3':
            if number == 8:
                return _verified(ev, 'correctly_exposed', 'Restitution du contenu canvas par technologie d’assistance non vérifiée.')
            if information is False: return TestStatus.NOT_APPLICABLE, ''
            if number != 9 and not semantic_alternatives(element, soup, kind) and not has_detailed_description(element, soup):
                return r, 'Aucune alternative à évaluer ; vérifier également le critère 1.1.'
            key = 'concise' if number == 9 else 'alternative_relevant'
            return _verified(ev, key, 'La pertinence / concision de l’alternative nécessite une comparaison avec le visuel.')

        if section == '1.4':
            if ev.get('captcha_alternative_relevant') is not None:
                return _verified(ev, 'captcha_alternative_relevant', 'Pertinence CAPTCHA non prouvée.')
            if not semantic_alternatives(element, soup, kind): return f, 'CAPTCHA explicite sans alternative indiquant sa nature/fonction.'
            return r, 'La pertinence de l’alternative CAPTCHA doit être vérifiée.'

        if section == '1.5':
            return _verified(ev, 'accessible_captcha_alternative', 'Une alternative non graphique ou une autre voie d’accès au CAPTCHA doit être testée.')

        if section == '1.6':
            if information is False: return TestStatus.NOT_APPLICABLE, ''
            if number == 9 and not text_refs(element, soup, 'aria-describedby'):
                return f, 'aria-describedby ne référence pas un texte existant et non vide.'
            if number in {6,8,9}:
                if number in {6,8} and not has_detailed_description(element, soup):
                    return r, 'Présence et restitution de la description non établies.'
                return _verified(ev, 'correctly_exposed', 'Restitution de la description par technologie d’assistance non vérifiée.')
            needed = ev.get('requires_detailed_description')
            if needed is False: return TestStatus.NOT_APPLICABLE, ''
            if needed is None and not has_detailed_description(element, soup):
                return r, 'Le besoin d’une description détaillée ne peut pas être déduit du DOM.'
            if has_description_mechanism(element, soup, kind):
                if number == 10 and text_refs(element, soup, 'aria-describedby'):
                    return p, ''
                if kind == 'img' and text_attr(element, 'longdesc'):
                    return _verified(ev, 'description_accessible', 'La ressource longdesc doit être vérifiée.')
                if kind in {'object','embed','canvas','svg'} and not ev.get('description_accessible'):
                    return r, 'Description trouvée, accès effectif et adéquation à vérifier.'
                if kind in {'img','input'} and not ev.get('description_accessible'):
                    return r, 'La description est associée, mais son mécanisme doit être vérifié.'
                return p, ''
            return f, 'Description détaillée requise mais aucun mécanisme reconnu n’a été trouvé.'

        if section == '1.7':
            if information is False: return TestStatus.NOT_APPLICABLE, ''
            return _verified(ev, 'description_relevant', 'La pertinence de la description détaillée nécessite une comparaison visuelle.')

        if section == '1.8':
            if information is False: return TestStatus.NOT_APPLICABLE, ''
            text_image = ev.get('is_text_image')
            if text_image is False: return TestStatus.NOT_APPLICABLE, ''
            if text_image is None: return r, 'Impossible de savoir si l’image contient du texte depuis le DOM.'
            if ev.get('special_case') is True: return TestStatus.NOT_APPLICABLE, ''
            return _verified(ev, 'text_replacement_valid', 'La possibilité de remplacer l’image texte par du texte CSS doit être vérifiée.')

        if section == '1.9':
            fig = element.find_parent('figure')
            cap = caption(element)
            if not isinstance(fig, Tag) or not isinstance(cap, Tag) or cap.parent != fig:
                return f, 'L’image et sa légende ne sont pas dans le même <figure>/<figcaption>.'
            if text_attr(fig, 'role') not in {'figure','group'}:
                return f, 'La balise figure doit posséder role="figure" ou role="group" selon le texte fourni.'
            if text_attr(fig, 'aria-label') != cap.get_text(' ', strip=True):
                return f, 'aria-label de figure ne correspond pas exactement à figcaption.'
            return p, ''
        return r, 'Test non traité.'


def _verified(ev: dict, key: str, message: str) -> tuple[TestStatus, str]:
    value = ev.get(key)
    if value is True: return TestStatus.PASS, ''
    if value is False: return TestStatus.FAIL, message
    return TestStatus.NEEDS_REVIEW, message


def _kind(element: Tag) -> str:
    if element.name == 'input': return 'input'
    if element.name in {'img','area','object','embed','svg','canvas'}: return element.name
    return 'img'
