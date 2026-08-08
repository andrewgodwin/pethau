import re

from django.conf import settings

from assets.models import Asset

from .base import LabelItem, ParsedSpec

# A term is a tag (or a range of two tags) optionally followed by a quantity.
TERM_RE = re.compile(
    r"""
    ^
    (?P<start>[a-z]*\d+)
    (?: - (?P<end>[a-z]*\d+) )?
    (?: [#xX] (?P<quantity>\d+) )?
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)

SEPARATOR_RE = re.compile(r"[,\s]+")

MAX_QUANTITY = 99
MAX_RANGE = 500


def canonical_tag(number: int) -> str:
    """
    The tag a bare number refers to, e.g. 345 -> "AER00345".
    """
    return f"{settings.ASSET_TAG_PREFIX}{str(number).zfill(settings.ASSET_TAG_DIGITS)}"


def tag_number(tag: str) -> int | None:
    """
    The numeric part of a tag, whether or not it was written with its prefix.
    """
    tag = tag.strip()
    prefix = settings.ASSET_TAG_PREFIX
    if tag.lower().startswith(prefix.lower()):
        tag = tag[len(prefix) :]
    if tag.isdigit():
        return int(tag)
    return None


def parse_spec(text: str) -> ParsedSpec:
    """
    Parses a label spec such as "345x2,123-125" into resolved assets and quantities.

    Terms are separated by commas and/or whitespace; each is a tag (bare digits or a
    full tag), or an inclusive numeric range of two tags, optionally suffixed with "#N"
    or "xN" to ask for N copies. Repeated references accumulate.
    """
    spec = ParsedSpec()
    if not text or not text.strip():
        return spec

    # Tags in the order first seen, mapped to how many copies were asked for
    wanted: dict[str, int] = {}

    for term in SEPARATOR_RE.split(text.strip()):
        if not term:
            continue
        match = TERM_RE.match(term)
        if not match:
            spec.errors.append(f"Could not understand {term!r}")
            continue

        quantity = int(match["quantity"]) if match["quantity"] else 1
        if not 1 <= quantity <= MAX_QUANTITY:
            spec.errors.append(
                f"Quantity in {term!r} must be between 1 and {MAX_QUANTITY}"
            )
            continue

        start = tag_number(match["start"])
        if start is None:
            spec.errors.append(f"Could not understand the tag in {term!r}")
            continue

        if match["end"] is None:
            _add_single(spec, wanted, match["start"], start, quantity, term)
        else:
            _add_range(spec, wanted, match["end"], start, quantity, term)

    if spec.errors:
        return spec

    assets = {
        asset.tag: asset
        for asset in Asset.objects.filter(
            tag__in=wanted, deleted__isnull=True
        ).select_related("model")
    }
    spec.items = [
        LabelItem(asset=assets[tag], quantity=quantity)
        for tag, quantity in wanted.items()
        if tag in assets
    ]
    return spec


def _add_single(spec, wanted, written_tag, number, quantity, term):
    """
    Resolves a single tag reference, recording an error if it doesn't exist.
    """
    asset = Asset.objects.filter(
        tag__iexact=canonical_tag(number), deleted__isnull=True
    ).first()
    if asset is None:
        # Fall back to the looser lookup the scanner uses, in case of odd historical tags
        asset = Asset.find_by_tag(written_tag)
    if asset is None:
        spec.errors.append(f"No asset found for {term!r}")
        return
    wanted[asset.tag] = wanted.get(asset.tag, 0) + quantity


def _add_range(spec, wanted, written_end, start, quantity, term):
    """
    Resolves an inclusive numeric range, skipping (and noting) members that don't exist.
    """
    end = tag_number(written_end)
    if end is None:
        spec.errors.append(f"Could not understand the end of the range in {term!r}")
        return
    if end < start:
        spec.errors.append(f"Range {term!r} ends before it starts")
        return
    if end - start + 1 > MAX_RANGE:
        spec.errors.append(f"Range {term!r} covers more than {MAX_RANGE} tags")
        return

    tags = [canonical_tag(number) for number in range(start, end + 1)]
    found = set(
        Asset.objects.filter(tag__in=tags, deleted__isnull=True).values_list(
            "tag", flat=True
        )
    )
    missing = [tag for tag in tags if tag not in found]
    if missing:
        spec.notices.append(
            f"Skipped {len(missing)} missing tag(s) in {term!r}: {', '.join(missing)}"
        )
    if not found:
        spec.errors.append(f"No assets found in range {term!r}")
        return
    for tag in tags:
        if tag in found:
            wanted[tag] = wanted.get(tag, 0) + quantity
