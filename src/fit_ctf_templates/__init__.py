from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, meta

from fit_ctf_models.utils.exceptions import MissingJinjaVariableException

TEMPLATE_DIRNAME = Path(__file__).parent
TEMPLATE_PATH_MAP = {
    "jinja_template": TEMPLATE_DIRNAME / "v1" / "jinja_templates",
    "volumes": TEMPLATE_DIRNAME / "v1" / "volumes",
    "modules": TEMPLATE_DIRNAME / "v1" / "modules",
    "scenarios": TEMPLATE_DIRNAME / "v1" / "scenarios",
}


def get_template(
    template_filename: str,
    template_dir: str = str(TEMPLATE_PATH_MAP["jinja_template"].resolve()),
) -> Template:
    """Return a Jinja template for rendering.

    Params:
        template_filename (str): A template's filename.
        template_dir (str, optional):
            A source directory that contains `template_filename`.
            Defaults to TEMPLATE_DIRNAME.

    Returns:
        Template: A retrieved template.
    """
    env = get_jinja_env(template_dir)
    return env.get_template(template_filename)


def get_jinja_env(template_dir: str | Path = TEMPLATE_DIRNAME) -> Environment:
    loader = FileSystemLoader(template_dir)
    return Environment(loader=loader)


def validate_variable_parse(
    template_name: str, template_dir: Path, variables: dict[str, Any]
):
    vars_to_map = get_jinja_variables(template_name, template_dir)
    missing = vars_to_map - set(variables.keys())
    if missing:
        raise MissingJinjaVariableException(
            f"Template '{template_name}' is missing required variables: {', '.join(sorted(missing))}"
        )


def get_jinja_variables(template_name: str, template_dir: Path) -> set[str]:
    env = Environment(loader=FileSystemLoader(template_dir))
    template_source = env.loader.get_source(env, template_name)
    parsed_content = env.parse(template_source)
    return meta.find_undeclared_variables(parsed_content)


def get_jinja_variables_from_string(source: str) -> set[str]:
    """Undeclared variable names in a Jinja string (e.g. volume `src_path`)."""
    env = Environment()
    ast = env.parse(source)
    return meta.find_undeclared_variables(ast)


def validate_volume_src_path_variables(
    src_path: str, variables: dict[str, Any]
) -> None:
    """Ensure all variables referenced in `src_path` are present in `variables`."""
    if "{{" not in src_path and "{%" not in src_path:
        return
    needed = get_jinja_variables_from_string(src_path)
    missing = needed - set(variables.keys())
    if missing:
        raise MissingJinjaVariableException(
            f"volume_map src_path is missing context keys: {', '.join(sorted(missing))}"
        )


def resolve_volume_src_path(
    src_path: str,
    context: dict[str, Any],
    *,
    validate_variables: bool = True,
) -> str:
    """Render Jinja in `src_path` when it contains template syntax; otherwise return as-is.

    `context` should include `paths__*`, `scenario_dir`, optional
    `user_scenario_dir` / `project_scenario_dir`, `project_name`, and `username` (user clusters).
    When built by :class:`ScenarioCompiler`, `paths__scenarios` is the current scenario
    template directory (same as `scenario_dir`) for this resolution step only.
    Per-volume `template_params` are not applied here; they are only for `*.template` files
    (see :func:`materialize_volume_src_for_compose`).
    """
    if "{{" not in src_path and "{%" not in src_path:
        return src_path
    if validate_variables:
        validate_volume_src_path_variables(src_path, context)
    env = Environment()
    return env.from_string(src_path).render(**context)


def build_volume_file_template_context(
    service_name: str,
    volume_name: str,
    template_params: dict[str, Any],
) -> dict[str, Any]:
    """Build Jinja context for a scenario `volumes/*.template` file.

    Only short keys (e.g. `secret`, `my_token`) are allowed. Each maps to
    `{service}__volume_map__{volume}__{key}`. Keys must not contain `__`.
    """
    out: dict[str, Any] = {}
    for k, v in template_params.items():
        if "__" in k:
            raise ValueError(
                f"template_params key {k!r}: only short keys are allowed "
                "(no '__'); do not pass pre-expanded compose variable names."
            )
        out[f"{service_name}__volume_map__{volume_name}__{k}"] = v
    return out


def render_volume_file_template(
    source: str,
    context: dict[str, Any],
    *,
    label: str = "volume file template",
) -> str:
    """Render a `*.template` body; validates that all referenced variables are in `context`."""
    env = Environment()
    ast = env.parse(source)
    needed = meta.find_undeclared_variables(ast)
    missing = needed - set(context.keys())
    if missing:
        raise MissingJinjaVariableException(
            f"{label} is missing template_params keys (after mapping): "
            f"{', '.join(sorted(missing))}"
        )
    return env.from_string(source).render(**context)


def materialize_volume_src_for_compose(
    resolved_src_path: str,
    *,
    scenario_root: Path,
    compile_dst_root: Path,
    service_name: str,
    volume_name: str,
    template_params: dict[str, Any],
) -> str:
    """If `resolved_src_path` is a `*.template` file under `scenario_root`, render it into
    `compile_dst_root` (same relative path without `.template`) and return that path for
    compose bind mounts. Otherwise return `resolved_src_path` unchanged.
    """
    p = Path(resolved_src_path)
    if not (p.is_file() and p.name.endswith(".template")):
        return resolved_src_path

    ctx = build_volume_file_template_context(service_name, volume_name, template_params)
    text = p.read_text(encoding="utf-8")
    rendered = render_volume_file_template(
        text,
        ctx,
        label=f"volume file template ({service_name}/{volume_name})",
    )
    rel = p.resolve().relative_to(scenario_root.resolve())
    out_path = (compile_dst_root / rel).with_suffix("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    tpl_at_dst = compile_dst_root / rel
    if tpl_at_dst.is_file():
        tpl_at_dst.unlink()
    return str(out_path.resolve())


__all__ = [
    "TEMPLATE_DIRNAME",
    "build_volume_file_template_context",
    "get_template",
    "get_jinja_variables_from_string",
    "materialize_volume_src_for_compose",
    "render_volume_file_template",
    "resolve_volume_src_path",
    "validate_volume_src_path_variables",
]
