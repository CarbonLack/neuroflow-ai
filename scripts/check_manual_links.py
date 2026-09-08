"""Check local pages, images, scripts, styles and fragment links in the manual."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / "docs/site"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        for attribute in ("href", "src"):
            if attributes.get(attribute):
                self.links.append(attributes[attribute])


def main():
    pages = {}
    for path in ROOT.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path.resolve()] = parser
    failures = []
    checked = 0
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target = target / "index.html"
            checked += 1
            if not target.is_file():
                failures.append(f"{path.relative_to(ROOT)}: missing {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                failures.append(f"{path.relative_to(ROOT)}: missing fragment {link}")
    for failure in failures:
        print(failure)
    print(f"{len(pages)} pages, {checked} local links, {len(failures)} errors")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
