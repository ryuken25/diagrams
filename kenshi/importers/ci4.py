"""CodeIgniter 4 migration importer.

Replays a folder of CI4 migrations (in filename order) to reconstruct the final
schema: ``forge->addField / addKey / addForeignKey / createTable`` plus the
``addColumn / dropColumn / dropTable`` and raw ``ALTER TABLE`` statements that
later migrations use. Produces a neutral :class:`Schema` the diagram builders
consume — proof the engine works on a real external app, not just hand data.
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field


@dataclass
class Table:
    name: str
    cols: list[str] = field(default_factory=list)
    pk: str = "id"
    fks: list[tuple] = field(default_factory=list)   # (col, ref_table, ref_col)


@dataclass
class Schema:
    tables: dict[str, Table] = field(default_factory=dict)

    def entities(self) -> dict:
        """{Name: (pk, [other cols])} for the ERD builders."""
        out = {}
        for t in self.tables.values():
            others = [c for c in t.cols if c != t.pk]
            out[t.name] = (t.pk, others)
        return out

    def prune(self):
        """Drop FKs (and their orphan columns) that point at dropped tables."""
        names = set(self.tables)
        for t in self.tables.values():
            dead = [fk for fk in t.fks if fk[1] not in names]
            t.fks = [fk for fk in t.fks if fk[1] in names]
            for (col, _rt, _rc) in dead:
                if col in t.cols:
                    t.cols.remove(col)
        return self

    def relationships(self, verbs=None) -> list:
        """FK -> (verb, parent(1), '1', child(N), 'N')."""
        verbs = verbs or {}
        rels = []
        for t in self.tables.values():
            for (col, ref_t, _rc) in t.fks:
                if ref_t not in self.tables:
                    continue
                verb = verbs.get((t.name, ref_t)) or verbs.get(col) or "memiliki"
                rels.append((verb, ref_t, "1", t.name, "N"))
        return rels


_FIELD = re.compile(r"'(\w+)'\s*=>\s*\[")
# CI4 column-attribute keys that are not column names (ENUM/SET use 'constraint'
# => [...] which would otherwise look like a column).
_ATTR_KEYS = {"constraint", "type", "null", "default", "unsigned",
              "auto_increment", "comment", "first", "after", "collation"}


def _parse_field_block(text: str) -> list[str]:
    """Field names from an addField/addColumn array literal (top-level keys only)."""
    return [f for f in _FIELD.findall(text) if f not in _ATTR_KEYS]


def _bracket_after(text: str, start: int) -> str:
    """Return the [...] array literal beginning at/after ``start``."""
    i = text.find("[", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]


def _up_body(src: str) -> str:
    """Extract just the up() method body (ignore down())."""
    m = re.search(r"function\s+up\s*\(\s*\)\s*\{", src)
    if not m:
        return src
    i = m.end()
    depth = 1
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j]
    return src[i:]


def _apply(schema: Schema, src: str):
    body = _up_body(src)
    # collect events with their position so we apply in source order
    events = []

    for m in re.finditer(r"addField\s*\(", body):
        events.append((m.start(), "addField", _bracket_after(body, m.end())))
    for m in re.finditer(r"addKey\s*\(\s*'(\w+)'\s*,\s*true", body):
        events.append((m.start(), "pk", m.group(1)))
    for m in re.finditer(
            r"addForeignKey\s*\(\s*'(\w+)'\s*,\s*'(\w+)'\s*,\s*'(\w+)'", body):
        events.append((m.start(), "fk", (m.group(1), m.group(2), m.group(3))))
    for m in re.finditer(r"createTable\s*\(\s*'(\w+)'", body):
        events.append((m.start(), "create", m.group(1)))
    for m in re.finditer(r"dropTable\s*\(\s*'(\w+)'", body):
        events.append((m.start(), "drop", m.group(1)))
    for m in re.finditer(r"addColumn\s*\(\s*'(\w+)'\s*,", body):
        events.append((m.start(), "addcol",
                       (m.group(1), _bracket_after(body, m.end()))))
    for m in re.finditer(
            r"dropColumn\s*\(\s*'(\w+)'\s*,\s*(\[[^\]]*\]|'[^']*')", body):
        cols = re.findall(r"'(\w+)'", m.group(2))
        events.append((m.start(), "dropcol", (m.group(1), cols)))
    # raw ALTER TABLE statements inside $db->query("...")
    for m in re.finditer(
            r"ALTER TABLE\s+`?(\w+)`?\s+ADD COLUMN\s+`?(\w+)`?", body):
        events.append((m.start(), "rawadd", (m.group(1), m.group(2))))
    for m in re.finditer(
            r"ALTER TABLE\s+`?(\w+)`?\s+DROP COLUMN\s+`?(\w+)`?", body):
        events.append((m.start(), "rawdrop", (m.group(1), m.group(2))))
    for m in re.finditer(
            r"ADD CONSTRAINT\s+`?\w+`?\s+FOREIGN KEY\s*\(`?(\w+)`?\)\s*"
            r"REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)", body):
        events.append((m.start(), "rawfk",
                       (m.group(1), m.group(2), m.group(3))))

    events.sort(key=lambda e: e[0])

    buf_fields: list[str] = []
    buf_pk = "id"
    buf_fks: list[tuple] = []
    for _pos, kind, payload in events:
        if kind == "addField":
            buf_fields = _parse_field_block(payload)
        elif kind == "pk":
            buf_pk = payload
        elif kind == "fk":
            buf_fks.append(payload)
        elif kind == "create":
            schema.tables[payload] = Table(payload, list(buf_fields), buf_pk,
                                           list(buf_fks))
            buf_fields, buf_pk, buf_fks = [], "id", []
        elif kind == "drop":
            schema.tables.pop(payload, None)
        elif kind in ("addcol", "rawadd"):
            tname = payload[0]
            cols = (_parse_field_block(payload[1]) if kind == "addcol"
                    else [payload[1]])
            t = schema.tables.get(tname)
            if t:
                for c in cols:
                    if c not in t.cols:
                        t.cols.append(c)
        elif kind in ("dropcol", "rawdrop"):
            tname = payload[0]
            cols = payload[1] if kind == "dropcol" else [payload[1]]
            t = schema.tables.get(tname)
            if t:
                t.cols = [c for c in t.cols if c not in cols]
                t.fks = [fk for fk in t.fks if fk[0] not in cols]
        elif kind == "rawfk":
            # attach to the most recently relevant table once it exists
            col, ref_t, ref_c = payload
            for t in schema.tables.values():
                if col in t.cols and (col, ref_t, ref_c) not in t.fks:
                    t.fks.append((col, ref_t, ref_c))
                    break


def import_ci4_migrations(folder: str) -> Schema:
    schema = Schema()
    files = sorted(glob.glob(os.path.join(folder, "*.php")))
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            _apply(schema, fh.read())
    return schema.prune()
