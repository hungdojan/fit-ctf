"""Tests for volume ``src_path`` Jinja and ``*.template`` rendering."""

from pathlib import Path

import pytest

from fit_ctf.models.utils.exceptions import (
    InvalidDynamicSecretKeyException,
    MissingJinjaVariableException,
)
from fit_ctf.templates import (
    build_volume_file_template_context,
    materialize_volume_src_for_compose,
    merge_secrets_into_volume_template_context,
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


def test_merge_secrets_into_volume_template_context():
    ctx = build_volume_file_template_context("web", "cfg", {"x": "1"})
    merge_secrets_into_volume_template_context(ctx, {"flag": "F"})
    assert ctx["secret_map__flag"] == "F"
    assert ctx["web__volume_map__cfg__x"] == "1"


def test_merge_secrets_rejects_double_underscore_in_name():
    ctx = {}
    with pytest.raises(InvalidDynamicSecretKeyException, match="must not contain '__'"):
        merge_secrets_into_volume_template_context(ctx, {"bad__key": "v"})


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
    ctx = build_volume_file_template_context("template_service", "readonly_file", {"secret": "abc"})
    assert render_volume_file_template(body, ctx) == "FLAGabc"


def test_render_volume_file_template_with_secret_map():
    body = "TOKEN={{ secret_map__api_key }}"
    ctx = build_volume_file_template_context("web", "cfg", {})
    merge_secrets_into_volume_template_context(ctx, {"api_key": "secret123"})
    assert render_volume_file_template(body, ctx) == "TOKEN=secret123"


def test_materialize_volume_src_for_compose_passes_secret_map_to_template(
    tmp_path: Path,
):
    scenario_root = tmp_path / "scen"
    vol_dir = scenario_root / "volumes"
    vol_dir.mkdir(parents=True)
    tpl = vol_dir / "out.template"
    tpl.write_text("value={{ secret_map__k }}", encoding="utf-8")
    compile_dst = tmp_path / "dst"
    out = materialize_volume_src_for_compose(
        str(tpl.resolve()),
        scenario_root=scenario_root,
        compile_dst_root=compile_dst,
        service_name="svc",
        volume_name="data",
        template_params={},
        secrets={"k": "v9"},
    )
    assert Path(out).read_text(encoding="utf-8") == "value=v9"
