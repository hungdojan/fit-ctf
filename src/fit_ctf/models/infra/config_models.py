"""Configuration models for scenarios and services."""

from typing import Any, Self

from pydantic import BaseModel, Field

from fit_ctf.models.utils.exceptions import (
    CTFModelException,
    InvalidDynamicSecretKeyException,
)

CANONICAL_SCENARIO_YAML_KEYS = frozenset({"secrets", "service_configs"})


def validate_canonical_scenario_yaml_dict(raw: dict) -> dict:
    """Require exactly ``secrets`` and ``service_configs`` (add-scenario / vars-template shape)."""
    if set(raw.keys()) != CANONICAL_SCENARIO_YAML_KEYS:
        raise CTFModelException(
            "Scenario YAML must have exactly top-level keys "
            f"{sorted(CANONICAL_SCENARIO_YAML_KEYS)!r}, got {sorted(raw.keys())!r}"
        )
    sec = raw["secrets"]
    svc = raw["service_configs"]
    if not isinstance(sec, dict):
        raise CTFModelException("'secrets' must be a mapping")
    if not isinstance(svc, dict):
        raise CTFModelException("'service_configs' must be a mapping")
    for name in sec:
        if "__" in str(name):
            raise InvalidDynamicSecretKeyException(
                f"secrets key {name!r} must not contain '__' "
                "(Jinja uses secret_map__<name>)."
            )
    return raw


class VolumeConfig(BaseModel):
    src_path: str
    template_params: dict[str, Any] = Field(default_factory=dict)

    class Builder:
        def __init__(self, src_path: str):
            self._src_path = src_path
            self._template_params = {}

        def add_template_param(self, param_name: str, param_value: Any) -> Self:
            self._template_params[param_name] = param_value
            return self

        def build(self) -> "VolumeConfig":
            return VolumeConfig(
                src_path=self._src_path, template_params=self._template_params
            )


class ServiceConfig(BaseModel):
    env_map: dict[str, str] = Field(default_factory=dict)
    port_map: dict[str, int] = Field(default_factory=dict)
    volume_map: dict[str, VolumeConfig] = Field(default_factory=dict)

    class Builder:
        def __init__(self):
            self._env_map: dict[str, str] = {}
            self._port_map: dict[str, int] = {}
            self._volume_map: dict[str, VolumeConfig] = {}

        def add_env(self, env_name: str, value: str) -> Self:
            self._env_map[env_name] = value
            return self

        def add_port(self, port_name: str, port_value: int) -> Self:
            if not (1 <= port_value <= 65_535):
                raise ValueError("Port number must be in range <1;65_535>")
            self._port_map[port_name] = port_value
            return self

        def add_volume(self, volume_name: str, volume_config: VolumeConfig) -> Self:
            self._volume_map[volume_name] = volume_config
            return self

        def build(self) -> "ServiceConfig":
            return ServiceConfig(
                env_map=self._env_map,
                port_map=self._port_map,
                volume_map=self._volume_map,
            )


class ScenarioConfig(BaseModel):
    scenario_name: str
    secrets: dict[str, str] = Field(default_factory=dict)
    service_configs: dict[str, ServiceConfig] = Field(default_factory=dict)
    config_params: dict[str, Any] = Field(default_factory=dict)

    class Builder:
        def __init__(self, scenario_name: str):
            self._scenario_name = scenario_name
            self._secrets: dict[str, str] = {}
            self._service_configs: dict[str, ServiceConfig] = {}
            self._config_params: dict[str, Any] = {}

        def add_secret(self, key: str, value: str) -> Self:
            self._secrets[key] = value
            return self

        def add_service(self, service_name: str, service_config: ServiceConfig) -> Self:
            self._service_configs[service_name] = service_config
            return self

        def add_config_param(self, key: str, value: Any) -> Self:
            self._config_params[key] = value
            return self

        def build(self) -> "ScenarioConfig":
            return ScenarioConfig(
                scenario_name=self._scenario_name,
                secrets=self._secrets,
                service_configs=self._service_configs,
                config_params=self._config_params,
            )


def service_config_from_dict(raw: dict) -> ServiceConfig:
    """Build ServiceConfig from a YAML/dump dict (setup.yaml / database_dump)."""
    volume_map: dict[str, VolumeConfig] = {}
    for k, v in raw.get("volume_map", {}).items():
        if isinstance(v, VolumeConfig):
            volume_map[k] = v
        else:
            volume_map[k] = VolumeConfig(**v)
    return ServiceConfig(
        env_map=dict(raw.get("env_map", {})),
        port_map=dict(raw.get("port_map", {})),
        volume_map=volume_map,
    )


def scenario_config_from_dict(scenario_name: str, raw: dict) -> ScenarioConfig:
    """Build ScenarioConfig from a YAML/dump dict (per setup.yaml scenario_configs)."""
    builder = ScenarioConfig.Builder(scenario_name)
    for name, value in raw.get("secrets", {}).items():
        if "__" in str(name):
            raise InvalidDynamicSecretKeyException(
                f"secrets key {name!r} must not contain '__' "
                "(Jinja uses secret_map__<name>)."
            )
        builder.add_secret(name, value if isinstance(value, str) else str(value))
    for service_name, svc_raw in raw.get("service_configs", {}).items():
        if not isinstance(svc_raw, dict):
            continue
        builder.add_service(service_name, service_config_from_dict(svc_raw))
    for name, value in raw.get("config_params", {}).items():
        builder.add_config_param(name, value)
    return builder.build()
