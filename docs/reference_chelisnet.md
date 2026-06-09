# Additional style reference — "Sistem Informasi Penjualan Chelisnet"

A second DFD style the diagrams should be able to match (provided by the user as
reference screenshots). Captured here as a written spec since it informs the
engine's conventions.

## Context diagram (Diagram 0)
- **Two external entities placed on opposite sides** — `Owner` on the **left**,
  `Admin` on the **right** — both exchanging the *same set* of flows with the one
  central system circle.
- Inputs stacked on top as parallel labelled arrows: `Data Merk`, `Data User`,
  `Data Jenis`, `Data Sementara`, `Data Barang`, `Data Detail`, `Data Transaksi`.
- Outputs stacked below: `Info Merk`, `Info User`, … `Info Transaksi`.
- **Orthogonal (Manhattan) routing**, lines run parallel and wrap around the
  external boxes; no overlap.

## DFD Level 0
- `OWNER` on the **left**, `ADMIN` on the **right**; **processes in a central
  vertical column**: `Login 1.0`, `Pengolahan_data_transaksi 2.0`,
  `…_barang 3.0`, `…_detail 4.0`, `…_jenis 5.0`, `…_merk 6.0`, `…_sementara 7.0`,
  `…_user 8.0`, `Cetak_laporan_transaksi 9.0`.
- Each process has its **data store** (`D1 User` … `D7 Sementara`) with a
  bidirectional `Data_x` / `Update_x` pair.
- Each process exchanges `Data_x` (in) / `Info_x` (out) with the externals.
- Orthogonal routing; flows are bidirectional everywhere.

## DFD Level 1 — CRUD decomposition (per table)
For each entity (user, transaksi, detail, sementara, jenis, barang, merk):
- Three sub-processes around a central store `TB <X>`:
  **`membuat X.1`**, **`mengubah X.2`**, **`menghapus X.3`**.
- `ADMIN` and `OWNER` on the sides; flows:
  `input_data_X_baru`, `informasi_data_X_baru`, `mengubah_data_X`,
  `informasi_data_X_yang_diubah`, `data_X_yang_dihapus`,
  `konfirmasi_data_X_yang_dihapus`.

## What the engine already honours from this
- Externals can sit on **either side** and edges enter from **any side**.
- **Every external / process / store is bidirectional** (input *and* output).
- Zero overlap, opaque labels.

> The current engine uses the *per-process-cluster* DFD layout (duplicated stores
> marked) which is overlap-free by construction. The Chelisnet "central process
> column + shared store + orthogonal routing" look and the CRUD Level-1 pattern
> can be added as an alternative layout mode on request.
