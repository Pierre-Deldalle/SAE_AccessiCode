"""Une réponse IA mal formée ne doit jamais produire une erreur ni une conclusion (8.2, 8.7, 8.8)."""

from unittest.mock import AsyncMock, Mock

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_2 import Test821
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_7 import Test871
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_8 import Test881

HTML = '<html lang="fr"><body><p>Bonjour</p><p lang="en">Hello</p></body></html>'


def _context() -> Mock:
    context = Mock(spec=AuditContext)
    context.dom = BeautifulSoup(HTML, "html.parser")
    context.html_source = HTML
    return context


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_class", "service_name", "method_name"),
    [
        (Test821, "html_validator", "validate_html"),
        (Test871, "language_change_analyzer", "analyze_language_changes"),
        (Test881, "language_validity_analyzer", "analyze_language_validity"),
    ],
)
async def test_malformed_ai_response_needs_review(test_class, service_name, method_name):
    analyzer = Mock()
    setattr(analyzer, method_name, AsyncMock(side_effect=ValueError("Le champ is_valid doit être booléen.")))
    services = Mock()
    setattr(services, service_name, analyzer)

    result = await test_class().run(_context(), services)

    assert result.status == TestStatus.NEEDS_REVIEW
    assert "invalide" in result.summary
    assert result.metadata["analysis_error"]
