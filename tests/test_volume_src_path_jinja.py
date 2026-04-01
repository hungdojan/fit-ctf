"""Tests for volume ``src_path`` Jinja and ``*.template`` rendering."""

import pytest

from fit_ctf_models.utils.exceptions import MissingJinjaVariableException
from fit_ctf_templates import (
    build_volume_file_template_context,
    render_volume_file_template,
    resolve_volume_src_path,
)


def test_resolve_volume_src_path_plain_unchanged():
    assert resolve_volume_src_path("/abs/host/path", {}) == "/abs/host/path"


def test_resolve_volume_src_path_jinja():
    ctx = {"scenario_dir": "/global/scen"}
    assert (
        resolve_volume_src_path("{{ scenario_dir }}/volumes/data", ctx)
        == "/global/scen/volumes/data"
    )


def test_resolve_volume_src_path_paths_scenarios():
    ctx = {"paths__scenarios": "/global/scen", "scenario_dir": "/global/scen"}
    assert (
        resolve_volume_src_path("{{ paths__scenarios }}/volumes/data", ctx)
        == "/global/scen/volumes/data"
    )


def test_resolve_volume_src_path_missing_variable():
    with pytest.raises(MissingJinjaVariableException, match="missing context keys"):
        resolve_volume_src_path("{{ unknown }}", {"scenario_dir": "/x"})


def test_build_volume_file_template_context():
    ctx = build_volume_file_template_context(
        "template_service",
        "readonly_file",
        {"secret": "X", "other": "Y"},
    )
    assert ctx["template_service__volume_map__readonly_file__secret"] == "X"
    assert ctx["template_service__volume_map__readonly_file__other"] == "Y"


def test_build_volume_file_template_context_rejects_preexpanded_key():
    with pytest.raises(ValueError, match="only short keys"):
        build_volume_file_template_context(
            "template_service",
            "readonly_file",
            {"template_service__volume_map__readonly_file__other": "Y"},
        )


def test_render_volume_file_template():
    body = "FLAG{{ template_service__volume_map__readonly_file__secret }}"
    ctx = build_volume_file_template_context(
        "template_service", "readonly_file", {"secret": "abc"}
    )
    assert render_volume_file_template(body, ctx) == "FLAGabc"
