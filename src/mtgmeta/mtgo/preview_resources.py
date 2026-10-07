"""Direct renderer references of the MTGO entry; not a runtime dependency graph."""
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit

ENTRY = "index.html"
SELECTION = {"method": "entry-direct-v1", "entry": ENTRY}
SEMANTIC_VISUALS = "assets/js/phase8/archetype-visuals.js"


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paths = []

    def handle_starttag(self, tag, attrs):
        if tag == "base":
            raise ValueError("Preview entry base URLs are not supported")
        if tag == "link" and sum(name == "rel" for name, _ in attrs) > 1:
            raise ValueError("Ambiguous preview stylesheet relation")
        fields = dict(attrs)
        if tag == "script" and "src" in fields:
            key = "src"
        elif tag == "link" and "stylesheet" in (fields.get("rel") or "").lower().split():
            key = "href"
        else:
            return
        if len([name for name, _ in attrs if name == key]) != 1 or not fields.get(key):
            raise ValueError("Preview renderer reference is missing or ambiguous")
        self.paths.append(fields[key])

    handle_startendtag = handle_starttag


def select(root: Path) -> list[str]:
    root = root.resolve()
    parser = References()
    parser.feed((root / ENTRY).read_text(encoding="utf-8"))
    parser.close()
    resources = {ENTRY}
    for reference in parser.paths:
        url = urlsplit(reference)
        path = unquote(url.path)
        parts = PurePosixPath(path)
        if (url.scheme or url.netloc or url.fragment or not path
                or path.startswith("/") or "\\" in path or ":" in path or ".." in parts.parts):
            raise ValueError(f"Unsupported preview renderer reference: {reference}")
        relative = parts.as_posix()
        target = root / relative
        if (not target.is_file() or not target.resolve().is_relative_to(root)
                or any(item.is_symlink() for item in (target, *target.parents) if item != root)):
            raise ValueError(f"Missing or unsafe preview renderer: {reference}")
        if url.query and (not re.fullmatch(r"v=[0-9a-f]{12}", url.query)
                or url.query[2:] != sha256(target.read_bytes()).hexdigest()[:12]):
            raise ValueError(f"Unsupported preview renderer version: {reference}")
        if relative != SEMANTIC_VISUALS:
            resources.add(relative)
    if len(resources) == 1:
        raise ValueError("Preview entry declares no protected renderer resources")
    return sorted(resources)
