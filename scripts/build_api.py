#!/usr/bin/env python3
"""Build the JSON API from the TSV tables (Python 3 standard library only).

    python3 scripts/build_api.py               # add api/<date>/ if the tables changed since the newest version
    python3 scripts/build_api.py --check       # read and build everything; write nothing
    python3 scripts/build_api.py --site _site  # assemble what GitHub Pages serves: every version, latest/ and index.json

A version is named for the day it is built (UTC), such as 2026-11-04. A second change on
the same day gets 2026-11-04.2, so a published version never changes. Each version holds
units.json, sets.json and point_systems.json, all.json with all three, and index.json
describing the version.

The tables follow datapackage.json: tab-separated, one header row, an empty cell is null,
list columns join items with ";", backslash escapes \\n, \\t and \\\\, and a cell containing
a double quote is wrapped in double quotes with the quotes inside doubled.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "api")
VERSION = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\.(\d+))?$")
DATA_FILES = ("units.json", "sets.json", "point_systems.json")
NOTICE = ("Images are hotlinked from their owners: show each image's credit wherever you show the image. "
          "HEROSCAPE is a trademark of Hasbro, used under license by Renegade Game Studios. "
          "This is a fan project, not affiliated with Hasbro, Wizards of the Coast or Renegade Game Studios.")


# ------------------------------------------------------------------ reading the tables

def cell(text):
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1].replace('""', '"')
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "\\": "\\"}[m.group(1)], text)


def typed(field, raw):
    if raw == "":
        return None
    v = cell(raw)
    kind = field.get("type", "string")
    if kind == "integer":
        return int(v)
    if kind == "boolean":
        return v == "true"
    if kind == "list":
        return v.split(";")
    return v


def read(path, resource):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        lines = f.read().split("\n")
    fields = resource["schema"]["fields"]
    header = lines[0].split("\t")
    if header != [f["name"] for f in fields]:
        raise SystemExit("%s: columns %s do not match datapackage.json" % (path, header))
    rows = []
    for n, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        cells = line.split("\t")
        if len(cells) != len(fields):
            raise SystemExit("%s:%d: %d cells, expected %d" % (path, n, len(cells), len(fields)))
        rows.append({f["name"]: typed(f, c) for f, c in zip(fields, cells)})
    return rows


def load():
    with open(os.path.join(ROOT, "datapackage.json"), encoding="utf-8") as f:
        res = {r["name"]: r for r in json.load(f)["resources"]}
    T = {name: read(r["path"], r) for name, r in res.items() if name != "points"}
    T["points"] = {}
    for rel in T["point_releases"]:
        path = res["points"]["path"].format(system_id=rel["system_id"], release_id=rel["id"])
        T["points"][rel["system_id"]] = {p["unit_id"]: p["points"] for p in read(path, res["points"])}
    return T


# ------------------------------------------------------------------ the JSON

def build(T):
    """{file name: document} for one version, without the version name."""
    abilities, images = {}, {}
    for a in sorted(T["abilities"], key=lambda a: (a["unit_id"], a["seq"])):
        abilities.setdefault(a["unit_id"], []).append({"name": a["name"], "text": a["text"]})
    for i in sorted(T["images"], key=lambda i: (i["subject_id"], i["seq"])):
        images.setdefault(i["subject_id"], []).append({"kind": i["kind"], "url": i["url"], "credit": i["credit"], "alt": i["alt"]})
    systems = sorted(s["id"] for s in T["point_systems"])
    units = []
    for u in sorted(T["units"], key=lambda u: u["id"]):
        points = {s: T["points"].get(s, {}).get(u["id"]) for s in systems}
        units.append({
            "id": u["id"], "name": u["name"], "version_label": u["version_label"],
            "display_name": u["name"] + (" (%s)" % u["version_label"] if u["version_label"] else ""),
            "character_id": u["character_id"], "origin": u["origin"], "publisher": u["publisher"], "era": u["era"],
            "general": u["general"], "type": "%s-%s" % (u["rarity"], u["kind"]), "rarity": u["rarity"], "kind": u["kind"],
            "species": u["species"] or [], "classes": u["classes"] or [], "personality": u["personality"],
            "size": u["size"], "height": u["height"], "homeworld": u["homeworld"],
            "life": u["life"], "move": u["move"], "range": u["range"], "attack": u["attack"], "defense": u["defense"],
            "figures": u["figures"], "hexes": u["hexes"], "set_id": u["set_id"],
            "contemporary_legal": u["contemporary_legal"], "aliases": u["aliases"] or [],
            "points": {s: p for s, p in points.items() if p is not None},
            "abilities": abilities.get(u["id"], []),
            "images": images.get(u["id"], []),
            "notes": u["notes"],
        })
    sets = [{k: s[k] for k in ("id", "name", "abbreviation", "publisher", "era", "line", "kind", "wave_number", "release_date")}
            | {"aliases": s["aliases"] or []}
            for s in sorted(T["sets"], key=lambda s: (s["release_date"] or "9999", s["id"]))]
    releases = {r["id"]: r for r in T["point_releases"]}
    point_systems = []
    for s in sorted(T["point_systems"], key=lambda s: s["id"]):
        r = releases[s["active_release"]]
        point_systems.append({"id": s["id"], "name": s["name"], "kind": s["kind"], "url": s["url"], "notes": s["notes"],
                              "release": {k: r[k] for k in ("id", "version", "effective_date", "captured_at", "coverage",
                                                            "rules_basis", "source_url")}})
    return {"units.json": units, "sets.json": sets, "point_systems.json": point_systems}


def render(doc):
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


def version_files(name, docs, T):
    """Every file of version `name`, as text."""
    as_of = max(r["captured_at"] for r in T["point_releases"] if r["captured_at"])
    files = {k: render(v) for k, v in docs.items()}
    files["all.json"] = render({"version": name, "data_as_of": as_of, "units": docs["units.json"],
                                "sets": docs["sets.json"], "point_systems": docs["point_systems.json"]})
    files["index.json"] = render({
        "version": name, "data_as_of": as_of,
        "files": {k[:-5]: k for k in DATA_FILES + ("all.json",)},
        "counts": {"units": len(docs["units.json"]), "sets": len(docs["sets.json"]),
                   "point_systems": len(docs["point_systems.json"])},
        "notice": NOTICE,
    })
    return files


# ------------------------------------------------------------------ versions

def versions():
    """Version folder names in api/, oldest first."""
    names = [n for n in os.listdir(API) if VERSION.match(n)] if os.path.isdir(API) else []
    return sorted(names, key=lambda n: (VERSION.match(n).group(1), int(VERSION.match(n).group(2) or 1)))


def unchanged(newest, docs):
    for name in DATA_FILES:
        try:
            with open(os.path.join(API, newest, name), encoding="utf-8") as f:
                if f.read() != render(docs[name]):
                    return False
        except FileNotFoundError:
            return False
    return True


def next_name(today, names):
    same = [VERSION.match(n) for n in names if VERSION.match(n).group(1) == today]
    if not same:
        return today
    return "%s.%d" % (today, max(int(m.group(2) or 1) for m in same) + 1)


def site(out):
    """api/ plus latest/ (a copy of the newest version) and a top-level index.json."""
    names = versions()
    if not names:
        raise SystemExit("no versions in api/ yet")
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(API, out)
    shutil.copytree(os.path.join(API, names[-1]), os.path.join(out, "latest"))
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render({"latest": names[-1], "versions": names[::-1], "notice": NOTICE}))
    print("assembled %s: latest is %s, %d version(s)" % (out, names[-1], len(names)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="build in memory only")
    mode.add_argument("--site", metavar="DIR", help="assemble the Pages site in DIR")
    ap.add_argument("--today", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    args = ap.parse_args()
    if args.site:
        site(args.site)
        return 0
    if not os.path.exists(os.path.join(ROOT, "datapackage.json")):
        print("no tables yet; nothing to build")
        return 0
    T = load()
    docs = build(T)
    names = versions()
    if args.check:
        print("ok: %d units, %d sets, %d point systems" % (len(docs["units.json"]), len(docs["sets.json"]),
                                                          len(docs["point_systems.json"])))
        return 0
    if names and unchanged(names[-1], docs):
        print("unchanged: %s already has these tables" % names[-1])
        return 0
    name = next_name(args.today, names)
    os.makedirs(os.path.join(API, name))
    for fname, text in version_files(name, docs, T).items():
        with open(os.path.join(API, name, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("new version: %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
