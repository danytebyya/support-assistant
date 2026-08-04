"""Download Lime FAQ and atomically replace the JSON knowledge base.

The parser accepts common accordion/FAQ markup and JSON-LD FAQPage data. It
refuses to overwrite a working knowledge base when the site returns an anti-bot
page or an unexpectedly small result.
"""
import ipaddress
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

URL = os.getenv("FAQ_URL", "https://limehd.tv/faq/0")
OUTPUT = Path(os.getenv("KNOWLEDGE_PATH", "data/knowledge/faq.json"))


def is_url_safe(url_str: str) -> bool:
    parsed = urllib.parse.urlparse(url_str)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except ValueError:
        pass
    return True


def clean(value: str) -> str:
    return " ".join(value.split())


def parse(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "{}")
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if node.get("@type") == "FAQPage":
                    for i, entity in enumerate(node.get("mainEntity", [])):
                        items.append({"id": f"faq-{i}", "question": clean(entity["name"]),
                                      "answer": clean(entity["acceptedAnswer"]["text"]), "url": URL})
        except (ValueError, KeyError, TypeError):
            continue
    if items:
        return items
    selectors = [
        (".faq-item", ".faq-question", ".faq-answer"),
        ("[data-faq]", "button, h2, h3", ".answer, [role=region]"),
        ("details", "summary", ":scope > :not(summary)"),
    ]
    for container, question, answer in selectors:
        for node in soup.select(container):
            q, a = node.select_one(question), node.select_one(answer)
            if q and a and clean(q.get_text()) and clean(a.get_text()):
                items.append({"id": f"faq-{len(items)}", "question": clean(q.get_text()),
                              "answer": clean(a.get_text()), "url": URL})
        if items:
            break
    return items


def main() -> None:
    if not is_url_safe(URL):
        sys.exit(f"FAQ sync aborted: Invalid or unsafe URL '{URL}'")
    request = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 LimeFAQSync/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    items = parse(html)
    if len(items) < 5:
        sys.exit("FAQ sync aborted: page is protected or parser found fewer than 5 entries")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Saved {len(items)} FAQ entries to {OUTPUT}.")


if __name__ == "__main__":
    main()
