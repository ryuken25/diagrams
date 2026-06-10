"""SDN 3 Mekarsari — Sistem Informasi Manajemen Nilai Siswa (ryuken25/sd3).

A third real CodeIgniter-4 app driven straight through the importer: a primary
school student-grade system (multi-role auth, tahun ajaran / kelas / siswa /
guru / mapel / KKM, input nilai, remedial, rapor, dashboard orang tua). The ERD
is reconstructed from the migrations; the DFD context / Level-0 are authored from
the documented domain.
"""
from __future__ import annotations

import os

from . import generic
from ..importers import import_ci4_migrations

APP_DIR = os.environ.get(
    "SD3_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "_sd3"))
MIGRATIONS = os.path.join(APP_DIR, "app", "Database", "Migrations")

CHEN_TITLE = "Entity Relationship Diagram (Chen) — SI Nilai Siswa SDN 3 Mekarsari"
CF_TITLE = "Entity Relationship Diagram (Crow's Foot) — SI Nilai Siswa SDN 3 Mekarsari"

# nicer Indonesian verbs for the relationship diamonds (parent -verb-> child)
VERBS = {
    "kelas": "memiliki", "siswa": "terdaftar di",
    "id_kelas": "berada di", "id_siswa": "milik",
    "id_mapel": "untuk", "id_tahun_ajaran": "pada",
    "id_user": "dikelola", "id_wali_siswa": "diwakili",
    "id_nilai_akhir": "diremedial", "id_master_cp": "mengacu",
}


def _schema():
    s = import_ci4_migrations(MIGRATIONS)
    # drop dead tables left empty by the consolidation migrations
    for name in [n for n, t in s.tables.items() if not t.cols]:
        s.tables.pop(name, None)
    return s.prune()


# Core academic entities for a readable ERD. The radial Chen layout stays legible
# with <=10 entities (which also matches the ordering model's range); the
# master/junction/secondary tables are carried by the full crow's-foot ERD.
_CORE = ["users", "tahun_ajaran", "kelas", "mata_pelajaran", "siswa", "kkm",
         "wali_siswa", "nilai_siswa", "rapor"]


def _subset(schema, names):
    keep = {n: schema.tables[n] for n in names if n in schema.tables}
    sub = type(schema)(tables=keep)
    return sub.prune()


def build_erd_chen(order_fn=None, full=False):
    s = _schema() if full else _subset(_schema(), _CORE)
    return generic.build_erd_chen(
        "ERD Chen (SD3)", CHEN_TITLE, s.entities(),
        s.relationships(VERBS), order_fn=order_fn)


def build_erd_crowsfoot(full=True):
    s = _schema() if full else _subset(_schema(), _CORE)
    return generic.build_erd_crowsfoot(
        "ERD Crow's Foot (SD3)", CF_TITLE, s.entities(), s.relationships(VERBS))


# ── DFD content (authored from the documented domain) ────────────────────────
SYSTEM = "Sistem Informasi Manajemen Nilai Siswa SDN 3 Mekarsari"

STORE_NAMES = {
    "D1": "D1  users", "D2": "D2  tahun_ajaran", "D3": "D3  kelas",
    "D4": "D4  mata_pelajaran", "D5": "D5  siswa", "D6": "D6  kkm",
    "D7": "D7  nilai", "D8": "D8  rapor", "D9": "D9  remedial",
    "D10": "D10  request_buka_nilai",
}


def build_context():
    flows = [
        ("Admin", "SYS", "Data master & akun"),
        ("Admin", "SYS", "Atur tahun ajaran & kelas"),
        ("SYS", "Admin", "Laporan & rekap nilai"),
        ("Guru", "SYS", "Login & input nilai"),
        ("Guru", "SYS", "Pengajuan buka nilai"),
        ("SYS", "Guru", "Daftar siswa & KKM"),
        ("SYS", "Guru", "Status nilai & rapor"),
        ("Orang_Tua", "SYS", "Login wali siswa"),
        ("SYS", "Orang_Tua", "Rapor & nilai anak"),
    ]
    return generic.build_context(
        "Diagram Konteks (SD3)",
        "Diagram Konteks (Diagram 0) — SI Nilai Siswa SDN 3 Mekarsari",
        "0\n" + SYSTEM, ["Admin", "Guru", "Orang_Tua"], flows)


def build_dfd0():
    data = {
        "id": "sd3-dfd-level0", "name": "DFD Level 0 (SD3)",
        "type": "dfd-level0",
        "title": "DFD Level 0 (Overview) — SI Nilai Siswa SDN 3 Mekarsari",
        "store_names": STORE_NAMES,
        "procs": [
            ("P1", "P1.0\nAutentikasi &\nKelola Akun"),
            ("P2", "P2.0\nKelola Data Master"),
            ("P3", "P3.0\nKelola Data Siswa"),
            ("P4", "P4.0\nInput & Kelola Nilai"),
            ("P5", "P5.0\nRemedial &\nBuka Nilai"),
            ("P6", "P6.0\nGenerate Rapor"),
        ],
        "ext": {
            "P1": [("Admin", [("Data akun pengguna", "to")]),
                   ("Guru", [("Data login", "to"), ("Status sesi", "from")])],
            "P2": [("Admin", [("Data tahun ajaran, kelas, mapel & KKM", "to"),
                              ("Info data master", "from")])],
            "P3": [("Admin", [("Data siswa & wali", "to")]),
                   ("Guru", [("Daftar siswa kelas", "from")])],
            "P4": [("Guru", [("Input nilai harian & ujian", "to"),
                             ("Rekap nilai", "from")])],
            "P5": [("Guru", [("Data remedial & pengajuan buka nilai", "to")]),
                   ("Admin", [("Persetujuan buka nilai", "to")])],
            "P6": [("Guru", [("Validasi rapor", "to")]),
                   ("Orang_Tua", [("Permintaan rapor", "to"),
                                  ("Rapor & nilai anak", "from")])],
        },
        "store": {
            "P1": [("D1", "", [("Data akun", "to"), ("Verifikasi kredensial", "from")])],
            "P2": [("D2", "", [("Data tahun ajaran", "to"), ("Info tahun ajaran", "from")]),
                   ("D3", "", [("Data kelas", "to")]),
                   ("D4", "", [("Data mapel", "to")]),
                   ("D6", "", [("Data KKM", "to"), ("Info KKM", "from")])],
            "P3": [("D5", "", [("Data siswa", "to"), ("Info siswa", "from")])],
            "P4": [("D7", "", [("Simpan nilai", "to"), ("Baca nilai", "from")]),
                   ("D5", "", [("Data siswa", "from")]),
                   ("D6", "", [("Baca KKM", "from")])],
            "P5": [("D9", "", [("Data remedial", "to")]),
                   ("D10", "", [("Pengajuan buka nilai", "to"),
                                ("Status pengajuan", "from")]),
                   ("D7", "", [("Update nilai", "to")])],
            "P6": [("D8", "", [("Simpan rapor", "to"), ("Baca rapor", "from")]),
                   ("D7", "", [("Baca nilai akhir", "from")])],
        },
    }
    return generic.build_dfd_ortho(data)


def build_all():
    return {
        "diagram_konteks": build_context(),
        "dfd_level0": build_dfd0(),
        "erd_chen": build_erd_chen(),
        "erd_crowsfoot": build_erd_crowsfoot(),
    }
