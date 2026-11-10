from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_04_multimedia.criterion_4_13 import (
    Test4131,
    Test4132,
)


def test_4131_without_media_is_not_applicable(context_factory, run_rgaa):
    context = context_factory("<p>Contenu sans média.</p>")

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_4131_native_video_controls_pass(context_factory, run_rgaa):
    context = context_factory('<video controls src="video.mp4"></video>')

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings[0].evidence["native_controls"] is True


def test_4131_unlabelled_non_temporal_media_fails(context_factory, run_rgaa):
    context = context_factory('<svg id="map"></svg>')

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


def test_4131_accessible_svg_pass(context_factory, run_rgaa):
    context = context_factory('<svg role="img" aria-label="Carte des pistes"></svg>')

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.PASS
    assert result.findings[0].evidence["accessible_name"] is True


def test_4131_mixed_media_fails(context_factory, run_rgaa):
    context = context_factory('<video controls></video><canvas id="graphique"></canvas>')

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert result.metadata["accessible_media"] == 1


def test_4132_without_alternative_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory('<video controls src="video.mp4"></video>')

    result = run_rgaa(Test4132(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_4132_adjacent_transcript_pass(context_factory, run_rgaa):
    context = context_factory('<video controls src="video.mp4"></video><p>Transcription : présentation du projet.</p>')

    result = run_rgaa(Test4132(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings[0].evidence["alternative_adjacent"] is True


def test_4132_adjacent_transcript_link_pass(context_factory, run_rgaa):
    context = context_factory(
        '<video id="video" controls></video>'
        '<a href="#transcription">Lire la transcription</a>'
        '<p id="transcription">Texte de la vidéo.</p>'
    )

    result = run_rgaa(Test4132(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_4132_remote_referenced_alternative_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<video aria-describedby="transcription" controls></video>'
        "<div></div>"
        '<main><p id="transcription">Texte de la vidéo.</p></main>'
    )

    result = run_rgaa(Test4132(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert result.findings[0].evidence["referenced_alternative"] is True
    assert result.findings[0].evidence["alternative_adjacent"] is False


def test_4131_adjacent_alternative_passes_without_native_controls(
    context_factory,
    run_rgaa,
):
    context = context_factory('<video src="video.mp4"></video><p>Transcription de la vidéo.</p>')

    result = run_rgaa(Test4131(), context)

    assert result.status == Status.PASS
    assert result.findings[0].evidence["accessible_alternative"] is True
