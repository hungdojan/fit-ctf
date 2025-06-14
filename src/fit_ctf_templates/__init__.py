import os
from pathlib import Path
from fit_ctf_templates.template_registry import template_registry

from jinja2 import Environment, FileSystemLoader, Template

TEMPLATE_DIRNAME = os.path.dirname(os.path.realpath(__file__))
JINJA_TEMPLATE_DIRPATHS = {"v1": Path(TEMPLATE_DIRNAME) / "v1" / "jinja_templates"}


def get_template(
    template_filename: str, template_dir: str = TEMPLATE_DIRNAME
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
    loader = FileSystemLoader(template_dir)
    env = Environment(loader=loader)

    return env.get_template(template_filename)


__all__ = [
    "TEMPLATE_DIRNAME",
    "JINJA_TEMPLATE_DIRPATHS",
    "get_template",
    "template_registry",
]
