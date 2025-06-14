import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from fit_ctf_templates.exceptions import TemplateNotFound


class TemplateRegistry:

    __CURR_DIR = os.path.dirname(os.path.realpath(__file__))
    DEFAULT_JINJA_TEMPLATE_DIRPATH = {"v1": Path(__CURR_DIR) / "v1" / "jinja_templates"}

    def __init__(self) -> None:
        self._registry: dict[str, tuple[str | Path, str]] = {}

    def register_template(
        self, name: str, template_dir: str | Path, template_name: str
    ) -> None:
        self._registry[name] = (template_dir, template_name)

    def get_template_path(self, name: str) -> tuple[str | Path, str] | None:
        return self._registry.get(name)

    def get_template(self, name: str) -> Template:
        """Return a Jinja template for rendering.

        Params:
            template_filename (str): A template's filename.
            template_dir (str, optional):
                A source directory that contains `template_filename`.
                Defaults to TEMPLATE_DIRNAME.

        Returns:
            Template: A retrieved template.
        """
        template_info = self._registry.get(name)
        if not template_info:
            raise TemplateNotFound(f"The template {name} is not registered.")
        loader = FileSystemLoader(template_info[0])
        env = Environment(loader=loader)

        return env.get_template(template_info[1])

    def load_defaults(self) -> None:
        for file in self.DEFAULT_JINJA_TEMPLATE_DIRPATH["v1"].iterdir():
            self.register_template(file.name, file.parent.resolve(), file.name)


template_registry = TemplateRegistry()
