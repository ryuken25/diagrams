"""MellogangVisuals semantic content + diagram builders.

Content (entities/attributes/relationships, processes/externals/stores/flows)
was reconstructed from the thesis reference diagrams and the project SQL schema.
Each builder produces a neutral :class:`Diagram`, runs the matching layout
engine, and returns a clean, overlap-free, fully-editable diagram.
"""
from __future__ import annotations

import os

from . import generic
from ..importers import import_ci4_migrations

CHEN_TITLE = "Entity Relationship Diagram (Chen) — MellogangVisuals"
CF_TITLE = "Entity Relationship Diagram (Crow's Foot) — MellogangVisuals"

SYSTEM = "Sistem Informasi Manajemen Jasa Foto & Video"

# Real CI4 app (github.com/ryuken25/mellogangvisuals), cloned next to the repo.
APP_DIR = os.environ.get(
    "MELLOGANG_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "_mellogang"))
_MIGRATIONS = os.path.join(APP_DIR, "app", "Database", "Migrations")

# table -> ERD display name (matches the thesis reference diagrams)
_DISPLAY = {
    "user": "User", "pemesanan": "Pemesanan", "paket": "Paket",
    "portofolio": "Portofolio", "jadwal_produksi": "Jadwal_Produksi",
    "pembayaran": "Pembayaran",
    "pengeluaran_operasional": "Pengeluaran_Operasional",
}

# Fallback (reconstructed from the reference drawio + SQL) if the repo is absent.
_FALLBACK_ENTITIES = {
    "User": ("id_user", ["nama_lengkap", "email", "no_telepon", "password",
                         "role", "created_at", "updated_at"]),
    "Pemesanan": ("id_pemesanan", ["kode_pemesanan", "id_user", "id_paket",
                  "tanggal_pemesanan", "tanggal_acara", "lokasi_acara",
                  "status_pemesanan", "total_biaya", "catatan_pelanggan",
                  "catatan_admin"]),
    "Paket": ("id_paket", ["nama_paket", "kategori", "deskripsi", "durasi_jam",
              "harga", "is_active", "created_at", "updated_at"]),
    "Portofolio": ("id_portfolio", ["id_paket", "judul", "deskripsi", "kategori",
                   "url_media", "tanggal_publikasi", "created_at", "updated_at"]),
    "Jadwal_Produksi": ("id_jadwal", ["id_pemesanan", "id_editor",
                        "tanggal_shooting", "jam_mulai_shooting",
                        "jam_selesai_shooting", "tanggal_mulai_editing",
                        "tanggal_selesai_editing", "status_produksi",
                        "catatan_produksi"]),
    "Pembayaran": ("id_pembayaran", ["id_pemesanan", "jenis_pembayaran",
                   "tanggal_bayar", "metode_pembayaran", "jumlah_bayar",
                   "bukti_bayar", "status_verifikasi", "catatan_verifikasi"]),
    "Pengeluaran_Operasional": ("id_pengeluaran", ["id_pemesanan",
                                "nama_pengeluaran", "nominal",
                                "tanggal_pengeluaran", "created_at",
                                "updated_at"]),
}


def _load_entities():
    """Use the real ryuken25/mellogangvisuals CI4 schema; fall back if absent."""
    try:
        schema = import_ci4_migrations(_MIGRATIONS)
        ents = schema.entities()
        if not ents:
            return _FALLBACK_ENTITIES
        out = {}
        for table, (pk, attrs) in ents.items():
            out[_DISPLAY.get(table, table)] = (pk, attrs)
        # keep a stable, reference-matching entity order
        order = list(_DISPLAY.values())
        return {k: out[k] for k in order if k in out} or _FALLBACK_ENTITIES
    except Exception:
        return _FALLBACK_ENTITIES


ENTITIES = _load_entities()

# (name, entity_one[card], entity_many[card])  parent(1) — child(N)
RELATIONSHIPS = [
    ("Melakukan",      "User",       "1", "Pemesanan",       "N"),
    ("Menjadi Editor", "User",       "1", "Jadwal_Produksi", "N"),
    ("Termasuk",       "Paket",      "1", "Pemesanan",       "N"),
    ("Memiliki",       "Paket",      "1", "Portofolio",      "N"),
    ("Membutuhkan",    "Pemesanan",  "1", "Jadwal_Produksi", "N"),
    ("Melakukan ",     "Pemesanan",  "1", "Pembayaran",      "N"),
    ("Mencatat",       "Pembayaran", "1", "Pengeluaran_Operasional", "N"),
]


def build_erd_chen(order_fn=None) -> Diagram:
    return generic.build_erd_chen("ERD Chen", CHEN_TITLE, ENTITIES,
                                  RELATIONSHIPS, order_fn=order_fn)


def build_erd_crowsfoot() -> Diagram:
    return generic.build_erd_crowsfoot("ERD Crow's Foot", CF_TITLE, ENTITIES,
                                       RELATIONSHIPS)


# ── DFD content ──────────────────────────────────────────────────────────────
def build_context() -> Diagram:
    flows = [
        ("Pelanggan", "SYS", "Data registrasi & login"),
        ("Pelanggan", "SYS", "Data pemesanan"),
        ("Pelanggan", "SYS", "Data pembayaran & bukti bayar"),
        ("SYS", "Pelanggan", "Informasi paket & portofolio"),
        ("SYS", "Pelanggan", "Konfirmasi & status pemesanan"),
        ("Admin", "SYS", "Data user, paket & portofolio"),
        ("Admin", "SYS", "Verifikasi pembayaran"),
        ("Admin", "SYS", "Data pengeluaran & permintaan laporan"),
        ("SYS", "Admin", "Laporan pemesanan, pendapatan & pengeluaran"),
        ("Editor", "SYS", "Login & update progres editing"),
        ("SYS", "Editor", "Jadwal produksi & daftar tugas"),
    ]
    return generic.build_context(
        "Diagram Konteks", "Diagram Konteks (Diagram 0) — MellogangVisuals",
        "0\n" + SYSTEM, ["Pelanggan", "Admin", "Editor"], flows)


STORE_NAMES = {
    "D1": "D1  user", "D2": "D2  pemesanan", "D3": "D3  paket",
    "D4": "D4  portofolio", "D5": "D5  pembayaran",
    "D6": "D6  jadwal_produksi", "D7": "D7  pengeluaran_operasional",
    "D8": "D8  detail_pemesanan",
}


def _materialize_dfd(data) -> Diagram:
    """Inject MellogangVisuals store labels and build via the generic engine."""
    data = {**data, "store_names": STORE_NAMES}
    return generic.build_dfd(data)


def build_dfd0() -> Diagram:
    data = {
        "id": "dfd-level0", "name": "DFD Level 0", "type": "dfd-level0",
        "title": "DFD Level 0 (Overview) — MellogangVisuals",
        "procs": [
            ("P1", "P1.0\nKelola User"),
            ("P2", "P2.0\nKelola Pesanan"),
            ("P3", "P3.0\nKelola Paket & Portofolio"),
            ("P4", "P4.0\nKelola Pembayaran"),
            ("P5", "P5.0\nPenjadwalan Produksi\n& Progres Editing"),
            ("P6", "P6.0\nPelaporan"),
        ],
        "ext": {
            "P1": [("Pelanggan", [("Data registrasi/login", "to"),
                                  ("Data user baru/ubah", "to"),
                                  ("Konfirmasi & status pemesanan", "from")])],
            "P2": [("Pelanggan", [("Data pemesanan baru/ubah", "to"),
                                  ("Informasi pemesanan jasa", "from")]),
                   ("Admin", [("Kelola data pemesanan", "to")])],
            "P3": [("Admin", [("Data paket baru/ubah/hapus", "to"),
                              ("Data portofolio baru/ubah/hapus", "to")]),
                   ("Pelanggan", [("Informasi paket & portofolio", "from")])],
            "P4": [("Pelanggan", [("Data pembayaran & bukti bayar", "to"),
                                  ("Informasi pembayaran", "from")]),
                   ("Admin", [("Verifikasi pembayaran", "to")])],
            "P5": [("Admin", [("Atur jadwal produksi", "to")]),
                   ("Editor", [("Login & update progres editing", "to"),
                               ("Daftar tugas & jadwal produksi", "from")])],
            "P6": [("Admin", [("Permintaan laporan", "to"),
                              ("Laporan pemesanan, pendapatan & pengeluaran", "from")])],
        },
        "store": {
            "P1": [("D1", "", [("Data user", "to"), ("Info user", "from")])],
            "P2": [("D2", "", [("Data pemesanan", "to"), ("Info pemesanan", "from")]),
                   ("D8", "", [("Data detail pemesanan", "to")]),
                   ("D3", "", [("Data paket", "from")])],
            "P3": [("D3", "", [("Data paket", "to"), ("Info paket", "from")]),
                   ("D4", "", [("Data portofolio", "to"), ("Info portofolio", "from")])],
            "P4": [("D5", "", [("Data pembayaran", "to"), ("Info pembayaran", "from")]),
                   ("D2", "", [("Update status pemesanan", "to"),
                               ("Data pemesanan terkait", "from")])],
            "P5": [("D6", "", [("Data jadwal produksi baru/ubah", "to"),
                               ("Data jadwal & status produksi", "from")]),
                   ("D2", "", [("Update status pemesanan", "to"),
                               ("Data pemesanan untuk dijadwalkan", "from")])],
            "P6": [("D2", "", [("Baca data pemesanan", "from")]),
                   ("D5", "", [("Baca data pembayaran", "from")]),
                   ("D6", "", [("Baca data jadwal produksi", "from")]),
                   ("D7", "", [("Simpan pengeluaran", "to"),
                               ("Data pengeluaran", "from")])],
        },
    }
    return _materialize_dfd(data)


# Level-1 decompositions
DFD1 = {
    "P1": {
        "id": "dfd-l1-p1", "name": "DFD Level 1 - P1", "type": "dfd-level1",
        "title": "DFD Level 1 — P1 Kelola User",
        "procs": [("P1.1", "P1.1\nAutentikasi"),
                  ("P1.2", "P1.2\nRegister User"),
                  ("P1.3", "P1.3\nEdit User")],
        "ext": {"P1.1": [("Pelanggan", [("Data login", "to"),
                                        ("Status autentikasi", "from")])],
                "P1.2": [("Pelanggan", [("Data registrasi", "to")])],
                "P1.3": [("Pelanggan", [("Data perubahan user", "to")])]},
        "store": {"P1.1": [("D1", "", [("Verifikasi kredensial", "from")])],
                  "P1.2": [("D1", "", [("Simpan user baru", "to")])],
                  "P1.3": [("D1", "", [("Perbarui data user", "to"),
                                       ("Info user", "from")])]},
    },
    "P2": {
        "id": "dfd-l1-p2", "name": "DFD Level 1 - P2", "type": "dfd-level1",
        "title": "DFD Level 1 — P2 Kelola Pesanan",
        "procs": [("P2.1", "P2.1\nInput Data\nPemesanan"),
                  ("P2.2", "P2.2\nValidasi &\nPerhitungan"),
                  ("P2.3", "P2.3\nSimpan Pemesanan\n& Detail")],
        "ext": {"P2.1": [("Pelanggan", [("Data pemesanan", "to")])],
                "P2.2": [("Admin", [("Aturan validasi", "to")])],
                "P2.3": [("Pelanggan", [("Konfirmasi pemesanan", "from")])]},
        "store": {"P2.1": [("D3", "", [("Data paket", "from")])],
                  "P2.2": [("D3", "", [("Harga paket", "from")])],
                  "P2.3": [("D2", "", [("Simpan pemesanan", "to")]),
                           ("D8", "", [("Simpan detail pemesanan", "to")])]},
        "pp": [("P2.1", "P2.2", "Data pemesanan"),
               ("P2.2", "P2.3", "Data pemesanan valid")],
    },
    "P3": {
        "id": "dfd-l1-p3", "name": "DFD Level 1 - P3", "type": "dfd-level1",
        "title": "DFD Level 1 — P3 Kelola Paket & Portofolio",
        "procs": [("P3.1", "P3.1\nKelola Data Paket"),
                  ("P3.2", "P3.2\nKelola Data\nPortofolio"),
                  ("P3.3", "P3.3\nTampilkan Info\nPaket & Portofolio")],
        "ext": {"P3.1": [("Admin", [("Data paket", "to")])],
                "P3.2": [("Admin", [("Data portofolio", "to")])],
                "P3.3": [("Pelanggan", [("Informasi paket & portofolio", "from")])]},
        "store": {"P3.1": [("D3", "", [("Data paket", "to"), ("Info paket", "from")])],
                  "P3.2": [("D4", "", [("Data portofolio", "to"),
                                       ("Info portofolio", "from")])],
                  "P3.3": [("D3", "", [("Baca paket", "from")]),
                           ("D4", "", [("Baca portofolio", "from")])]},
    },
    "P4": {
        "id": "dfd-l1-p4", "name": "DFD Level 1 - P4", "type": "dfd-level1",
        "title": "DFD Level 1 — P4 Kelola Pembayaran",
        "procs": [("P4.1", "P4.1\nInput Data\nPembayaran"),
                  ("P4.2", "P4.2\nVerifikasi\nPembayaran")],
        "ext": {"P4.1": [("Pelanggan", [("Data pembayaran & bukti bayar", "to")])],
                "P4.2": [("Admin", [("Hasil verifikasi", "to")])]},
        "store": {"P4.1": [("D5", "", [("Simpan pembayaran", "to")])],
                  "P4.2": [("D5", "", [("Update status verifikasi", "to"),
                                       ("Data pembayaran", "from")]),
                           ("D2", "", [("Update status pemesanan", "to")])]},
        "pp": [("P4.1", "P4.2", "Data pembayaran")],
    },
    "P5": {
        "id": "dfd-l1-p5", "name": "DFD Level 1 - P5", "type": "dfd-level1",
        "title": "DFD Level 1 — P5 Penjadwalan Produksi & Progres Editing",
        "procs": [("P5.1", "P5.1\nSusun Jadwal\nProduksi"),
                  ("P5.2", "P5.2\nDistribusi Tugas\nke Editor"),
                  ("P5.3", "P5.3\nUpdate Progres\nEditing")],
        "ext": {"P5.1": [("Admin", [("Atur jadwal produksi", "to")])],
                "P5.2": [("Editor", [("Daftar tugas editing", "from")])],
                "P5.3": [("Editor", [("Update progres editing", "to")])]},
        "store": {"P5.1": [("D2", "", [("Data pemesanan", "from")]),
                           ("D6", "", [("Simpan jadwal produksi", "to")])],
                  "P5.2": [("D6", "", [("Data jadwal produksi", "from")])],
                  "P5.3": [("D6", "", [("Update status produksi", "to")]),
                           ("D2", "", [("Update status pemesanan", "to")])]},
        "pp": [("P5.1", "P5.2", "Jadwal produksi"),
               ("P5.2", "P5.3", "Tugas editing")],
    },
    "P6": {
        "id": "dfd-l1-p6", "name": "DFD Level 1 - P6", "type": "dfd-level1",
        "title": "DFD Level 1 — P6 Pelaporan & Pengeluaran",
        "procs": [("P6.1", "P6.1\nGenerate Laporan\nPemesanan"),
                  ("P6.2", "P6.2\nGenerate Laporan\nPendapatan & Pengeluaran"),
                  ("P6.3", "P6.3\nKelola\nPengeluaran")],
        "ext": {"P6.1": [("Admin", [("Permintaan laporan pemesanan", "to"),
                                     ("Laporan pemesanan", "from")])],
                "P6.2": [("Admin", [("Laporan pendapatan & pengeluaran", "from")])],
                "P6.3": [("Admin", [("Data pengeluaran", "to")])]},
        "store": {"P6.1": [("D2", "", [("Baca data pemesanan", "from")])],
                  "P6.2": [("D5", "", [("Baca data pembayaran", "from")]),
                           ("D7", "", [("Baca data pengeluaran", "from")])],
                  "P6.3": [("D7", "", [("Simpan pengeluaran", "to"),
                                       ("Info pengeluaran", "from")])]},
    },
}


def build_dfd1(pkey: str) -> Diagram:
    return _materialize_dfd(DFD1[pkey])


def build_all() -> dict[str, Diagram]:
    out = {
        "diagram_konteks": build_context(),
        "dfd_level0": build_dfd0(),
        "erd_chen": build_erd_chen(),
        "erd_crowsfoot": build_erd_crowsfoot(),
    }
    for p in ["P1", "P2", "P3", "P4", "P5", "P6"]:
        out[f"dfd_level1_{p}"] = build_dfd1(p)
    return out
