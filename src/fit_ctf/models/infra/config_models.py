"""Configuration models for scenarios and services."""

from typing import Any, Self

from pydantic import BaseModel, Field


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
            return VolumeConfig(src_path=self._src_path, template_params=self._template_params)


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
