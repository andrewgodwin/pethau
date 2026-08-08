from .avery_sheets import Avery5160, Avery6467
from .base import LabelItem, LabelTemplate, ParsedSpec
from .parser import parse_spec
from .zebra_roll import Zebra3x1

# Every available label template, keyed by slug. Adding one is a new class plus a line here.
TEMPLATES: dict[str, LabelTemplate] = {
    template.slug: template
    for template in [
        Avery5160(),
        Avery6467(),
        Zebra3x1(),
    ]
}

DEFAULT_TEMPLATE = Avery5160.slug

__all__ = [
    "DEFAULT_TEMPLATE",
    "TEMPLATES",
    "LabelItem",
    "LabelTemplate",
    "ParsedSpec",
    "get_template",
    "parse_spec",
    "template_choices",
]


def get_template(slug: str | None) -> LabelTemplate:
    """
    Looks up a template by slug, falling back to the default for unknown ones.
    """
    return TEMPLATES.get(slug or "", TEMPLATES[DEFAULT_TEMPLATE])


def template_choices() -> list[tuple[str, str]]:
    return [(template.slug, template.name) for template in TEMPLATES.values()]
