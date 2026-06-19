# Read 2026-06-18 — understand: 50%
"""
data_loader.py — Phase 1, Step 1 of the ingestion pipeline.

WHAT THIS FILE DOES
-------------------
It takes the giant MedlinePlus XML file (~80-150 MB, ~2,000 health-topic entries)
and produces a clean, smaller JSONL file containing only English topics with
just four fields per record: title, url, also_called, text.

PIPELINE POSITION
-----------------
    data/raw/mplus_topics_*.xml          (input - what you downloaded)
              │
              ▼
    data_loader.py  ◄── YOU ARE HERE
              │
              ▼
    data/medlineplus_clean.jsonl         (output - one JSON per line)
              │
              ▼
    chunker.py → vector store + graph    (Phases 2 & 3)

HOW TO RUN
----------
From the project root (the folder containing `backend/` and `frontend/`),
with the backend venv active:

    python -m backend.app.ingestion.data_loader

After it finishes, open `data/medlineplus_clean.jsonl` — you'll see one
JSON object per line, like:

    {"title": "Sore Throat", "url": "https://...", "also_called": [...], "text": "..."}
"""
from __future__ import annotations  # lets us write `list[dict]` on Python 3.9
import json
import re
from pathlib import Path
from typing import Iterator

# Third-party libraries:
#   - BeautifulSoup    → strips HTML tags out of strings.
#   - lxml.etree       → fast XML parser. We use its `iterparse` so we don't
#                        load the entire 100 MB XML into memory at once.
#   - tqdm             → draws a progress bar while we work.
from bs4 import BeautifulSoup
from lxml import etree
from tqdm import tqdm

# These are paths defined in backend/app/config.py:
#   RAW_DIR     = <project>/data/raw/         (where the XML lives)
#   CLEAN_JSONL = <project>/data/medlineplus_clean.jsonl   (our output)
from backend.app.config import CLEAN_JSONL, RAW_DIR


# ---------------------------------------------------------------------------
# Helper 1 — find the XML file the student dropped into data/raw/
# ---------------------------------------------------------------------------
def _find_xml() -> Path:
    """Return the path of the most recent MedlinePlus XML inside `data/raw/`.

    The leading underscore in the name is a Python convention meaning:
    "this is a private helper, not meant to be imported from outside this file".

    Why glob for "mplus_topics_*.xml" instead of a fixed filename?
        MedlinePlus releases a new file each month with the date in its name,
        e.g. mplus_topics_2026-05-12.xml. We don't want to hard-code the date.

    Why `sorted(...)[-1]`?
        sorted() puts filenames in alphabetical order. Because the dates in
        the filename are in YYYY-MM-DD form, alphabetical order == newest last.
        So [-1] (the last element) is the most recent dump.
    """
    candidates = sorted(RAW_DIR.glob("mplus_topics_*.xml"))
    if not candidates:
        # Give the student a clear, actionable error message.
        raise FileNotFoundError(
            f"No MedlinePlus XML found in {RAW_DIR}. "
            "Download one from https://medlineplus.gov/xml.html and place it there."
        )
    return candidates[-1]


# ---------------------------------------------------------------------------
# Helper 2 — strip HTML out of a string and tidy whitespace
# ---------------------------------------------------------------------------
def _strip_html(html: str) -> str:
    """Turn a piece of HTML into plain text.

    Example input:
        '<p>A1C is a <a href="...">blood test</a> for diabetes.</p>'

    Example output:
        'A1C is a blood test for diabetes.'

    Steps:
      1. BeautifulSoup parses the HTML and `.get_text(separator=" ")` returns
         only the visible text, joined by spaces. Tags vanish.
      2. The regex `\\s+` matches any run of whitespace (spaces, tabs,
         newlines) and replaces it with a single space — keeps the output
         compact and tidy.
      3. `.strip()` removes leading/trailing spaces.

    Why `html or ""`?
        If the input is None (missing summary), `None or ""` evaluates to "".
        BeautifulSoup would crash on None — this guards against that.
    """
    text = BeautifulSoup(html or "", "lxml").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Core function — stream-parse the XML one topic at a time
# ---------------------------------------------------------------------------
def iter_topics(xml_path: Path) -> Iterator[dict]:
    """Yield one cleaned dict per English `<health-topic>` element in the XML.

    Why a generator (yield) instead of returning a big list?
        The XML has ~2,000 entries and the file is ~100 MB. If we built a
        full list in memory we'd briefly hold *everything* at once — fine on
        a beefy machine but wasteful. By yielding one record at a time, the
        caller can write each to disk and we never hold the full corpus.

    Why `etree.iterparse`?
        It's a "streaming" XML parser. Instead of reading the whole file into
        a tree (which would also load everything into memory), it fires events
        as it sees them. We listen for "end" events on every `<health-topic>`
        tag — i.e. "the parser just finished reading one whole topic".
    """
    # context is an iterator that fires once per `</health-topic>` closing tag.
    # The `events=("end",)` part means: only tell us when a `</health-topic>`
    # finishes, not when it starts.
    context = etree.iterparse(str(xml_path), events=("end",), tag="health-topic")

    for _, elem in context:
        # `elem` is the just-finished <health-topic> XML element.
        # `_` is the event type ("end"); we don't need it, hence the underscore.

        # ---------- Filter: keep only English topics ----------
        # MedlinePlus also ships Spanish translations of the same articles.
        # We only want English. If `language` is anything else, free the
        # element's memory and skip to the next iteration.
        if elem.get("language", "English") != "English":
            elem.clear()  # release memory used by this XML element
            continue

        # ---------- Extract the 4 fields we care about ----------
        # `.get("attr", default)` reads an XML attribute, e.g. title="A1C".
        # `.strip()` removes leading/trailing whitespace from the value.
        title = elem.get("title", "").strip()
        url = elem.get("url", "").strip()

        # A topic can have 0, 1, or many <also-called> children.
        # `elem.findall("also-called")` gives back all of them as a list.
        # We pull out each one's text content, stripping whitespace.
        # The `if n.text` guard skips empty <also-called/> tags.
        also_called = [n.text.strip() for n in elem.findall("also-called") if n.text]

        # `<full-summary>` is the article body. `elem.find(...)` returns the
        # first matching child element, or None if there isn't one.
        summary_el = elem.find("full-summary")

        # If we found the element, grab its inner text. That text is itself
        # HTML (with `&lt;p&gt;` and friends) — we hand it to _strip_html to
        # clean it down to plain prose.
        summary_html = summary_el.text if summary_el is not None else ""
        text = _strip_html(summary_html)

        # ---------- Yield the cleaned record ----------
        # We only emit topics that have BOTH a title and some body text.
        # A few entries in the wild are just stubs / redirects with empty
        # summaries — we drop those silently.
        if title and text:
            yield {
                "title": title,
                "url": url,
                "also_called": also_called,
                "text": text,
            }

        # ---------- Free memory ----------
        # This is the classic "streaming iterparse" cleanup pattern. Without
        # it, lxml holds onto every element it has seen and memory usage
        # grows linearly with the file size.
        #
        # `elem.clear()` empties the element itself.
        # The while-loop removes already-processed previous siblings from
        # the parent so the parser can garbage-collect them.
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


# ---------------------------------------------------------------------------
# Top-level function — write the cleaned JSONL file to disk
# ---------------------------------------------------------------------------
def build_clean_jsonl() -> Path:
    """Read the raw XML and write one JSON object per line into CLEAN_JSONL.

    Why JSONL (one JSON per line) instead of one big JSON array?
      - You can read it line by line — no need to load everything at once.
      - You can inspect it with `head`, `tail`, `grep` from the command line.
      - Easy to stream / process in parallel later.

    `ensure_ascii=False` keeps Unicode characters (accents, em-dashes,
    medical symbols) human-readable instead of escaping them like "\\u00e9".
    """
    xml_path = _find_xml()
    print(f"Parsing {xml_path.name} ...")

    count = 0
    # `with open(...)` ensures the file is closed automatically when we're done,
    # even if an error happens mid-loop.
    with CLEAN_JSONL.open("w", encoding="utf-8") as f:
        # tqdm wraps the iterator and draws a progress bar in the terminal.
        # `unit="topics"` makes the bar label say "1234 topics" instead of
        # the default "1234 it" (iterations).
        for rec in tqdm(iter_topics(xml_path), unit="topics"):
            # json.dumps turns the Python dict into a JSON string.
            # We append "\n" so each record sits on its own line.
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1

    print(f"Wrote {count} topics to {CLEAN_JSONL}")
    return CLEAN_JSONL


# ---------------------------------------------------------------------------
# Convenience reader — used by chunker.py and the EDA notebook
# ---------------------------------------------------------------------------
def load_records() -> list[dict]:
    """Return all cleaned records as a list of dicts.

    If the JSONL doesn't exist yet, build it first. This makes the function
    safe to call from notebooks without students having to remember to run
    `build_clean_jsonl()` separately.

    Be aware: this loads the whole corpus into memory. That's fine for
    ~1,000 short records (a few MB), but for much larger corpora you'd want
    to stream instead.
    """
    if not CLEAN_JSONL.exists():
        build_clean_jsonl()

    with CLEAN_JSONL.open("r", encoding="utf-8") as f:
        # List comprehension: for each line in the file, parse the JSON and
        # collect the resulting dicts into a list.
        return [json.loads(line) for line in f]


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------
# `if __name__ == "__main__":` is a Python idiom meaning:
# "only run this block when the file is executed directly with `python ...`,
# NOT when it is imported by another file".
#
# So:
#   python -m backend.app.ingestion.data_loader   → runs build_clean_jsonl()
#   from backend.app.ingestion import data_loader → does NOT run anything
if __name__ == "__main__":
    build_clean_jsonl()
