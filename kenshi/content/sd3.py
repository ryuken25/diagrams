"""SDN 3 Mekarsari — Sistem Informasi Manajemen Nilai Siswa (ryuken25/sd3).

A primary-school student-grade system (CodeIgniter 4). The migration history
goes through several consolidations, leaving a few orphan tables that the app no
longer uses (grades folded into ``nilai``, wali into ``siswa``). The authoritative
schema is the set of tables the app's Models actually bind to — 12 tables — so we
reconstruct from the migrations and then keep only those 12.

Only the two diagrams requested are built: DFD Level 0 + ERD Crow's Foot.
"""
from __future__ import annotations

import os

from . import generic
from ..importers import import_ci4_migrations

APP_DIR = os.environ.get(
    "SD3_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "_sd3"))
MIGRATIONS = os.path.join(APP_DIR, "app", "Database", "Migrations")

CF_TITLE = "Entity Relationship Diagram (Crow's Foot) — SI Nilai Siswa SDN 3 Mekarsari"

# The 12 tables the app's Models bind to (the live schema; orphan tables left by
# the consolidation migrations — wali_siswa / nilai_harian / nilai_ujian — are
# excluded).
ACTIVE = ["users", "tahun_ajaran", "kelas", "mata_pelajaran", "mapel_kelas",
          "siswa", "kkm", "nilai", "nilai_aktivitas", "rapor",
          "request_buka_nilai", "master_referensi"]

VERBS = {
    "id_kelas": "berada di", "id_siswa": "milik", "id_mapel": "untuk",
    "id_tahun_ajaran": "pada", "id_user": "dikelola", "id_kkm": "mengacu",
    "id_mapel_kelas": "diampu", "id_referensi": "merujuk",
}


def _schema():
    s = import_ci4_migrations(MIGRATIONS)
    keep = {n: s.tables[n] for n in ACTIVE if n in s.tables}
    return type(s)(tables=keep).prune()


def build_erd_crowsfoot():
    s = _schema()
    return generic.build_erd_crowsfoot(
        "ERD Crow's Foot (SD3)", CF_TITLE, s.entities(), s.relationships(VERBS))


# ── DFD Level 0 (authored from the documented domain, 12-table schema) ───────
SYSTEM = "Sistem Informasi Manajemen Nilai Siswa SDN 3 Mekarsari"

STORE_NAMES = {
    "D1": "D1  users", "D2": "D2  tahun_ajaran", "D3": "D3  kelas",
    "D4": "D4  mata_pelajaran", "D5": "D5  mapel_kelas", "D6": "D6  siswa",
    "D7": "D7  kkm", "D8": "D8  nilai", "D9": "D9  nilai_aktivitas",
    "D10": "D10  rapor", "D11": "D11  request_buka_nilai",
    "D12": "D12  master_referensi",
}


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
            ("P5", "P5.0\nBuka Nilai"),
            ("P6", "P6.0\nGenerate Rapor"),
        ],
        "ext": {
            "P1": [("Admin", [("Data akun pengguna", "to")]),
                   ("Guru", [("Data login", "to"), ("Status sesi", "from")])],
            "P2": [("Admin", [("Data tahun ajaran, kelas, mapel & KKM", "to"),
                              ("Info data master", "from")])],
            "P3": [("Admin", [("Data siswa", "to")]),
                   ("Guru", [("Daftar siswa kelas", "from")])],
            "P4": [("Guru", [("Input nilai & aktivitas", "to"),
                             ("Rekap nilai", "from")])],
            "P5": [("Guru", [("Pengajuan buka nilai", "to")]),
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
                   ("D5", "", [("Data mapel-kelas", "to")]),
                   ("D7", "", [("Data KKM", "to"), ("Info KKM", "from")]),
                   ("D12", "", [("Data referensi", "to"), ("Info referensi", "from")])],
            "P3": [("D6", "", [("Data siswa", "to"), ("Info siswa", "from")])],
            "P4": [("D8", "", [("Simpan nilai", "to"), ("Baca nilai", "from")]),
                   ("D9", "", [("Simpan nilai aktivitas", "to")]),
                   ("D6", "", [("Data siswa", "from")]),
                   ("D7", "", [("Baca KKM", "from")])],
            "P5": [("D11", "", [("Pengajuan buka nilai", "to"),
                                ("Status pengajuan", "from")]),
                   ("D8", "", [("Update status nilai", "to")])],
            "P6": [("D10", "", [("Simpan rapor", "to"), ("Baca rapor", "from")]),
                   ("D8", "", [("Baca nilai", "from")]),
                   ("D9", "", [("Baca nilai aktivitas", "from")])],
        },
    }
    return generic.build_dfd_ortho(data)


def build_all():
    return {
        "dfd_level0": build_dfd0(),
        "erd_crowsfoot": build_erd_crowsfoot(),
    }
