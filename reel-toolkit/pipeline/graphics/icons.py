"""Minimal original line icons (24x24 viewBox, stroke = currentColor)."""
from __future__ import annotations

_P = {
    "doc": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/><path d="M10 13h6M10 17h6"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "chart": '<path d="M4 20V4"/><path d="M4 20h16"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/>',
    "bot": '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4"/><circle cx="12" cy="3.5" r="1"/><circle cx="9.5" cy="13" r="1.2"/><circle cx="14.5" cy="13" r="1.2"/><path d="M3 12v4M21 12v4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4.5-6 8-6s7 2 8 6"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "send": '<path d="M21 3L10 14"/><path d="M21 3l-7 18-4-7-7-4z"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5"/><circle cx="12" cy="18" r=".6"/>',
    "spark": '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h1M4 12h1M4 18h1"/>',
    "won": '<path d="M4 6l3.5 12L12 8l4.5 10L20 6"/><path d="M3 11h18M3 14h18"/>',
    "hand": '<path d="M8 13V5.5a1.5 1.5 0 013 0V12"/><path d="M11 11V4.5a1.5 1.5 0 013 0V11"/><path d="M14 11V5.5a1.5 1.5 0 013 0V13"/><path d="M8 13l-1.6-1.8a1.6 1.6 0 00-2.4 2.1L8 19c1.2 1.4 2.6 2 4.5 2H14a5 5 0 005-5v-5.5a1.5 1.5 0 00-2-1.4"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 015 .5c0 1.7-2.5 2-2.5 4"/><circle cx="12" cy="17" r=".6"/>',
    "flag": '<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>',
    "bell": '<path d="M6 16v-5a6 6 0 0112 0v5l2 2H4z"/><path d="M10 20.5a2 2 0 004 0"/>',
    "cart": '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2 3h3l2.5 12h11.5L21 7H6"/>',
}

CURSOR = ('<svg viewBox="0 0 24 24" width="100%" height="100%"><path d="M5 3l14 8-6 1.5L10 19z" '
          'fill="#1E1B1A" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>')


def icon(name: str, size: int = 36, stroke: float = 2.0, color: str = "currentColor") -> str:
    body = _P.get(name, _P["spark"])
    return (f'<svg class="ico" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</svg>')


def names() -> list[str]:
    return sorted(_P)
