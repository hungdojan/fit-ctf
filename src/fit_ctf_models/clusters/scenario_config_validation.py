"""
Compare :class:`ScenarioConfig` to template-derived scaffolds (missing → error, extra → warning).
"""

from __future__ import annotations

from typing import Any

from fit_ctf_models.clusters.config_models import ServiceConfig, VolumeConfig


def validate_secrets_vs_templates(
    required_secret_names: frozenset[str],
    configured_secrets: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for secret keys vs ``secret_map__*`` template usage."""
    errors: list[str] = []
    warnings: list[str] = []
    configured = set(configured_secrets.keys())
    for name in sorted(required_secret_names - configured):
        errors.append(f"missing secrets['{name}'] (templates use secret_map__{name})")
    for name in sorted(configured - required_secret_names):
        warnings.append(
            f"unused secrets['{name}'] (no secret_map__{name} in scenario templates)"
        )
    return errors, warnings


def _warn_unused_map_keys(
    warnings: list[str],
    *,
    svc: str,
    label: str,
    user_keys: Any,
    scaffold_keys: Any,
) -> None:
    """Emit warnings for keys present in user config but not in the template scaffold."""
    for k in set(user_keys) - set(scaffold_keys):
        warnings.append(f"service '{svc}' has unused {label} key '{k}'")


def _validate_env_map(
    errors: list[str],
    warnings: list[str],
    svc: str,
    scm_env: dict[str, Any],
    cfg: ServiceConfig,
) -> None:
    for ek in scm_env:
        if ek not in cfg.env_map:
            errors.append(
                f"service '{svc}' missing env_map key '{ek}' required by templates"
            )
        elif not str(cfg.env_map.get(ek, "")).strip():
            errors.append(
                f"service '{svc}' env_map['{ek}'] is empty but required by templates"
            )
    _warn_unused_map_keys(
        warnings, svc=svc, label="env_map", user_keys=cfg.env_map, scaffold_keys=scm_env
    )


def _validate_port_map(
    errors: list[str],
    warnings: list[str],
    svc: str,
    scm_ports: dict[str, Any],
    cfg: ServiceConfig,
) -> None:
    for pk in scm_ports:
        if pk not in cfg.port_map:
            errors.append(
                f"service '{svc}' missing port_map key '{pk}' required by templates"
            )
            continue
        try:
            pv = int(cfg.port_map[pk])
        except (TypeError, ValueError):
            errors.append(f"service '{svc}' port_map['{pk}'] must be an integer port")
        else:
            if not (1 <= pv <= 65_535):
                errors.append(
                    f"service '{svc}' port_map['{pk}'] must be in range 1-65535"
                )
    _warn_unused_map_keys(
        warnings,
        svc=svc,
        label="port_map",
        user_keys=cfg.port_map,
        scaffold_keys=scm_ports,
    )


def _validate_volume_map(
    errors: list[str],
    warnings: list[str],
    svc: str,
    scm_vols: dict[str, Any],
    vol_map: dict[str, VolumeConfig],
) -> None:
    for vk, vv in scm_vols.items():
        # ``fetch_variables`` only builds dict-shaped volume entries.
        if not isinstance(vv, dict):
            continue
        if vk not in vol_map:
            errors.append(
                f"service '{svc}' missing volume_map volume '{vk}' required by templates"
            )
            continue
        uv = vol_map[vk]
        if "src_path" in vv and not str(uv.src_path).strip():
            errors.append(
                f"service '{svc}' volume '{vk}' src_path is empty but required by templates"
            )
        scm_tpl = vv.get("template_params", {})
        for tk in scm_tpl:
            if tk not in uv.template_params:
                errors.append(
                    f"service '{svc}' volume '{vk}' missing template_params key '{tk}' "
                    "required by templates"
                )
            elif not str(uv.template_params.get(tk, "")).strip():
                errors.append(
                    f"service '{svc}' volume '{vk}' template_params['{tk}'] is empty "
                    "but required by templates"
                )
        for tk in uv.template_params:
            if tk not in scm_tpl:
                warnings.append(
                    f"service '{svc}' volume '{vk}' has unused template_params key '{tk}'"
                )
    for vk in vol_map:
        if vk not in scm_vols:
            warnings.append(f"service '{svc}' has unused volume_map volume '{vk}'")


def validate_service_configs_vs_scaffold(
    scaffold: dict[str, Any],
    service_configs: dict[str, ServiceConfig],
) -> tuple[list[str], list[str]]:
    """Compare ``fetch_variables`` scaffold to configured services."""
    errors: list[str] = []
    warnings: list[str] = []

    for svc, sc_data in scaffold.items():
        if svc not in service_configs:
            errors.append(f"missing service '{svc}' required by scenario templates")
            continue
        cfg = service_configs[svc]
        _validate_env_map(errors, warnings, svc, sc_data.get("env_map", {}), cfg)
        _validate_port_map(errors, warnings, svc, sc_data.get("port_map", {}), cfg)
        _validate_volume_map(
            errors, warnings, svc, sc_data.get("volume_map", {}), cfg.volume_map
        )

    for svc in service_configs:
        if svc not in scaffold:
            warnings.append(
                f"unused service '{svc}' not referenced by scenario templates"
            )

    return errors, warnings
