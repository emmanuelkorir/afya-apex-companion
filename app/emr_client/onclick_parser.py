"""
Parses the Ward Management grid's `showMenu(event, 'a', 'b', ...)` onclick
attribute.

The ward grid has no dedicated <span id="...lblUMR"> the way the UMR-search
grid does (see search_page.py's `_lblRegistrationNo`) - UMR, visit number,
and consultant are only present as positional string-literal arguments to
the JS `showMenu(...)` call. This module is the single place that decodes
that positional contract, so a change to the EMR's markup only needs a
field-index fix here.

Known argument layout (0-indexed within the parenthesized arg list, after
the leading bare `event` token):
    0  menu client id
    1  registration_no
    2  (unnamed)
    3  umr
    4  visit_no
    5  patient_name
    6  consultant
    7  admission_time
    8  (unnamed)
    9  bed_code
    10 (unnamed)
    11 ward_short
    12 (unnamed - blank in observed samples)
    13 ward_full_name
    14 payer
    15 age_gender
    ... remaining args are booleans/numeric flags not currently used.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_CALL_RE = re.compile(r"showMenu\s*\(\s*event\s*,\s*(.*)\)\s*$", re.DOTALL)
# Matches a single '...' quoted argument, allowing the arg to be empty.
_ARG_RE = re.compile(r"'([^']*)'")

_MIN_ARGS = 16  # highest named index (15) + 1


@dataclass(slots=True)
class ShowMenuArgs:
    """Named view over the subset of showMenu(...) args we currently use."""

    registration_no: str
    umr: str
    visit_no: str
    patient_name: str
    consultant: str
    admission_time: str
    bed_code: str
    ward_short: str
    payer: str
    age_gender: str
    raw_args: list[str] = field(default_factory=list)


def parse_show_menu_onclick(onclick: str) -> ShowMenuArgs:
    """
    Parse a `showMenu(event, 'a', 'b', ...)` onclick string.

    Args:
        onclick: The raw onclick attribute value.

    Returns:
        ShowMenuArgs with named fields for the args we rely on, plus the
        full raw positional list for any future menu action that needs a
        field we don't name yet.

    Raises:
        ValueError: If the string isn't a showMenu(...) call, or has fewer
            quoted arguments than the fields we need to extract.
    """
    if not onclick:
        raise ValueError("onclick string is empty")

    match = _CALL_RE.search(onclick)
    if not match:
        raise ValueError(
            "onclick string is not a showMenu(event, ...) call: "
            f"{onclick[:80]!r}"
        )

    args = _ARG_RE.findall(match.group(1))

    if len(args) < _MIN_ARGS:
        raise ValueError(
            f"showMenu(...) onclick had {len(args)} quoted args, "
            f"expected at least {_MIN_ARGS}: {onclick[:120]!r}"
        )

    return ShowMenuArgs(
        registration_no=args[1],
        umr=args[3],
        visit_no=args[4],
        patient_name=args[5],
        consultant=args[6],
        admission_time=args[7],
        bed_code=args[9],
        ward_short=args[11],
        payer=args[14],
        age_gender=args[15],
        raw_args=args,
    )


def extract_umr_and_visit_no(onclick: str, strict: bool = False) -> tuple[str, str]:
    """
    Convenience wrapper for the one thing wardmanagement_page.py needs:
    UMR and visit number, without the caller having to import ShowMenuArgs.

    Args:
        onclick: The raw onclick attribute value.
        strict: If True, propagate parse failures. If False (default),
            swallow parse errors and return ("", "") so a single malformed
            row doesn't break the whole /ward search - the caller can
            surface "unknown UMR" in the UI instead of a hard failure.

    Returns:
        (umr, visit_no) tuple, possibly ("", "") if strict=False and
        parsing failed.
    """
    try:
        parsed = parse_show_menu_onclick(onclick)
    except ValueError:
        if strict:
            raise
        return "", ""
    return parsed.umr, parsed.visit_no