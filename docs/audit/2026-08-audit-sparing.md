# Audit Menyeluruh — Dashboard Monitoring SPARING

**Tanggal:** 2026-08-20 · **Metode:** READ → TRACE → ANALYZE (read-only, tanpa modifikasi kode)
**Cakupan:** `sparing_api` (FastAPI/SQLAlchemy/MySQL), `sparing_front` (Vue 3/Vite), `sparing_python` (logger Pi).

Bukti diambil dari source code aktual (file · fungsi · endpoint · tabel). Tidak ada asumsi dari UI semata.

---

## A. EXECUTIVE SUMMARY

```
Overall Project Completion: ~72%

Critical Issues: 3
High Issues:     6
Medium Issues:   7
Low Issues:      5
```

**Klasifikasi kesiapan: PILOT READY (menuju Operational).**

Alasan: alur inti **Database → Backend → API → Frontend → output nyata** berjalan untuk monitoring realtime, historis, compliance, alarm dengan lifecycle, device/logger health, dan raw-data explorer + export — semuanya dari data aktual (bukan mock; tidak ditemukan `Math.random`/dummy di frontend). Sistem sudah bisa menjawab "kondisi SPARING sekarang", "memenuhi baku mutu?", "sensor/logger sehat?", "ada alarm?". **Belum production-ready** karena: (1) tak ada unique-constraint anti-duplikat pada `sensor_data`, (2) dua sumber threshold yang bisa saling bertentangan, (3) belum ada volume/gap/korelasi/exceedance-event/transmission-rate — analitik yang dibutuhkan untuk pelaporan operasional penuh.

---

## B. FEATURE COVERAGE MATRIX

| No | Feature | Status | FE | BE | DB | Confidence |
|---|---|---|---|---|---|---|
| 01 | Executive Dashboard | IMPLEMENTED | ✅ | ✅ | ✅ | High |
| 02 | Real-time Monitoring | IMPLEMENTED (polling 30s) | ✅ | ✅ | ✅ | High |
| 03 | Historical Trend | IMPLEMENTED | ✅ | ✅ | ✅ | High |
| 04 | Compliance / Baku Mutu | PARTIAL (dua sumber threshold) | ✅ | ✅ | ✅ | High |
| 05 | Data Completeness | PARTIAL (asumsi 30/jam tetap, hitung semua baris) | ✅ | ✅ | ✅ | High |
| 06 | Missing Data / Gap Analysis | NOT IMPLEMENTED | ❌ | ❌ | ⚠ | High |
| 07 | Communication Monitoring | PARTIAL (via heartbeat, berlapis) | ✅ | ✅ | ✅ | Med |
| 08 | Sensor Health | PARTIAL | ✅ | ✅ | ✅ | Med |
| 09 | Sensor Stuck Detection | IMPLEMENTED (flatline run ≥15m) | ✅ | ✅ | ✅ | High |
| 10 | Outlier / Anomaly Detection | IMPLEMENTED (MAD/drift/implausible) | ✅ | ✅ | ✅ | High |
| 11 | Alarm & Notification Center | IMPLEMENTED (lifecycle + catatan) | ✅ | ✅ | ✅ | High |
| 12 | Event Timeline | PARTIAL (logger events saja) | ✅ | ✅ | ✅ | High |
| 13 | Power Monitoring | UI ONLY (V/I ditampilkan, tak ada W/alarm) | ✅ | ⚠ | ✅ | High |
| 14 | Maintenance Management | PARTIAL (CRUD; tak ada overdue) | ✅ | ✅ | ✅ | High |
| 15 | Calibration History | PARTIAL (tak ada before/after/offset) | ✅ | ✅ | ✅ | High |
| 16 | Debit & Total Volume | NOT IMPLEMENTED (instantaneous saja) | ⚠ | ❌ | ⚠ | High |
| 17 | Correlation Analysis | NOT IMPLEMENTED | ❌ | ❌ | ⚠ | High |
| 18 | Parameter Statistics | PARTIAL (P95 client-side; tak ada median BE/P99) | ✅ | ⚠ | ✅ | Med |
| 19 | Exceedance Analysis | INCORRECT (hitung baris, bukan event) | ⚠ | ⚠ | ✅ | High |
| 20 | Reliability / Availability | PARTIAL (dicampur dengan completeness) | ⚠ | ⚠ | ✅ | Med |
| 21 | Data Transmission Monitoring | PARTIAL (status boolean; tak ada rate) | ✅ | ✅ | ✅ | Med |
| 22 | Raw Data Explorer | IMPLEMENTED (filter+paginasi+export Excel) | ✅ | ✅ | ✅ | High |
| 23 | Multi-Site Monitoring | IMPLEMENTED | ✅ | ✅ | ✅ | High |

---

## C. DETAIL AUDIT 01–23

### 01. Executive Dashboard — IMPLEMENTED
- FE `Pages/Dashboard/Index.vue`; BE `stats.py`, `alerts.py`, `getdata`/`data.py`, `devices.py`, `logger.py`. DB `sensor_data`, `alerts`, `logger_status`, `sensor_devices`.
- KPI dari data nyata: Perangkat online (dari device last_seen), Kepatuhan 30hr (`/stats/compliance`), Alarm aktif (`/alerts/count`), Kelengkapan hari ini (`/stats/completeness`, dari 00:00 WIB). Chip logger (`/logger/status`). Status badge Normal/Waspada/Bahaya/Cek-Sensor via `getSensorStatus`.
- **Beban request:** dashboard memanggil ~6-8 endpoint + N+1 (`getLatestData` per site di `loadSitesStatus`, `getDeviceHealth` per device). Untuk 4 site masih ringan; skala puluhan site → perlu endpoint agregat. Priority: Medium.

### 02. Real-time Monitoring — IMPLEMENTED (polling)
- Mekanisme: **polling 30 detik** (`setInterval` di Dashboard), bukan WS/SSE/MQTT. Wajar untuk cadence data 2 menit. Nilai terakhir + satuan + status + baku-mutu (dari AlertRule) + sparkline ~2 jam. `data.py::last_record`. Priority: Low.

### 03. Historical Trend — IMPLEMENTED
- FE trend chart (ApexCharts) + History page. BE `data.py::list_data` mendukung `interval=raw|hourly|daily` (agregasi Python-side, mengecualikan anomali & op_status). Filter tanggal + parameter. **Downsampling:** chart Dashboard `per_page:100`; History paginasi 50/hal + agregasi. Tak menarik jutaan baris sekaligus. Priority: Low.

### 04. Compliance / Baku Mutu — PARTIAL
- BE `/stats/compliance` + `/stats/compliance-daily`: benar secara logika (per reading × AlertRule danger bounds, kecualikan anomali/op_status, per-site, delta window). Threshold dari **DB `AlertRule`** ✅.
- **PROBLEM (High):** `Pages/Analytics/Index.vue` + `Utils/analysis.js::standards` memakai **threshold hardcoded** (TSS≤100, COD≤200, NH3-N≤10) yang **berbeda** dari default AlertRule (TSS danger 200). Dua sumber kebenaran → compliance Analytics ≠ Dashboard. Required: satukan ke AlertRule (drop `standards` atau ambil dari `/alert-rules`).

### 05. Data Completeness — PARTIAL
- BE `stats.py::completeness`: `actual` = COUNT(sensor_data) sejak `date_from` (00:00 WIB dari FE), `expected = sites × 30 × hours`. Sudah memperhitungkan partial-day (window dari midnight) & timezone (FE kirim UTC ISO dari WIB).
- **PROBLEM (Medium):** (a) `30/jam` **hardcoded** (`READINGS_PER_SITE_PER_HOUR`), bukan dari interval konfigurasi/`Site`. (b) Menghitung **semua baris** termasuk baris kalibrasi/anomali & **duplikat** (lihat #Audit Duplicate) → bisa overcount. (c) Bukan per-parameter. Required: derive interval per site; hitung distinct timestamp.

### 06. Missing Data / Gap Analysis — NOT IMPLEMENTED
- Tidak ada endpoint/logika mendeteksi gap (start/end/duration/jumlah hilang) maupun heatmap missing. Hanya `completeness` (rasio) yang ada. Required: endpoint `/analytics/gaps` (deteksi selisih antar `ts` > interval). Priority: High.

### 07. Communication Monitoring — PARTIAL (berlapis, via heartbeat)
- `logger.py` heartbeat membawa: `internet_ok`, `last_send_ok_mm`, `last_send_ok_klhk`, `ph_ok..nh3n_ok`, `consec_fail`. `logger_monitor.py` dead-man's switch membedakan **logger down** (silence >10m) vs **internet down** (event saja). Jadi lapisan Sensor / Logger / Internet / Kirim-server dibedakan ✅. **Kurang:** status server KLHK eksternal hanya boolean per-heartbeat (bukan verifikasi end-to-end). Priority: Medium.

### 08. Sensor Health — PARTIAL
- `logger_status.*_ok` (tri-state per sensor) + `sensor_health` table (dari anomaly engine: status/anomaly_type/last_value). `sensor_fail_since` → alarm `sensor_<name>` warning >15m (`logger_monitor`). **Kurang:** last-successful-read timestamp per sensor, Modbus-timeout counter granular, recovery time. Priority: Medium.

### 09. Sensor Stuck Detection — IMPLEMENTED
- `anomaly_engine.py::check_flatline`: run nilai identik terkini ≥ `FLATLINE_MIN_MINUTES` (15m), di-anchor ke reading terbaru (bukan 2 data). Metode masuk akal. Priority: Low.

### 10. Outlier / Anomaly Detection — IMPLEMENTED (statistik/rule)
- `anomaly_engine.py`: `check_implausible` (rentang fisik), `check_spike` (median + **MAD**, K=5, min-abs-delta), `check_drift` (relative mean shift 24h vs 7d), `check_flatline`. Dibedakan dari **exceedance** (compliance) ✅. Frontend `analysis.js::detectAnomalies` (IQR) adalah sistem **kedua** yang terpisah, hanya atas ~100 titik chart — potensi membingungkan. Metode: rule/statistical (bukan ML). Priority: Low (BE), Medium (rekonsiliasi FE/BE).

### 11. Alarm & Notification Center — IMPLEMENTED
- `alerts.py` + `alert_engine.py` + `logger_monitor.py`. Kategori: `compliance` (pH/TSS/COD/…), `data_quality` (implausible/flatline/spike/drift), `logger` (`logger_down`, `sensor_*`). Severity `danger`/`warning`. Lifecycle: active → acknowledged → resolved, **catatan wajib saat tutup**, auto-resolve dengan catatan sistem, satu alert aktif per (site,field). Bell + halaman Alarm + filter + paginasi + PIC. **Kurang:** kategori Power belum ada; notifikasi eksternal (email/WA) backlog. Priority: Low.

### 12. Event Timeline — PARTIAL
- `logger_events` (started/stopping/stopped/net_down/net_up/send_fail/sensor_fail/sensor_recover/opstatus_change/buffer_high) + timeline di `/loggers`. Punya ts/type/severity/detail/site. **Kurang:** event exceedance/maintenance/calibration tidak masuk timeline terpadu (tersebar). Priority: Medium.

### 13. Power Monitoring — UI ONLY / PARTIAL
- `sensor_data.voltage/current` tersimpan + chart "Parameter Kelistrikan". **TIDAK ada** perhitungan Power = V×I, **tidak ada** alarm low/high voltage/overcurrent/power-failure. Untuk site saat ini V/I selalu 0 (sensor tak terpasang) → chart auto-hidden. Required: kolom/derived power + AlertRule untuk voltage/current. Priority: Medium.

### 14. Maintenance Management — PARTIAL
- `maintenance_logs` (type/notes/performed_at/next_due_at/performed_by) + CRUD di halaman Perangkat (modal). Health endpoint pakai `next_due_at`. **Kurang:** perhitungan **overdue/due** tidak disurface; tak ada status maintenance (planned/completed) selain implisit. Priority: Medium.

### 15. Calibration History — PARTIAL
- `maintenance_logs.type='calibration'`; `devices.py::get_device_health` menghitung `last_calibration_at` + `next_calibration_at`. "Days since calibration" bisa diturunkan FE. **PROBLEM:** schema `MaintenanceLog` **tidak menyimpan** before/after value maupun offset (hanya notes). Required: kolom `before_value`/`after_value`/`offset` bila kalibrasi formal dibutuhkan. Priority: Medium.

### 16. Debit & Total Volume — NOT IMPLEMENTED
- Hanya instantaneous flow (Debit) yang ditampilkan. **Tidak ada** daily/monthly/accumulated volume, tidak ada integrasi Flow×Δt. `reports.py` tak menghitung volume. Satuan debit di sistem = **L/min** (bukan m³/h) — konversi ke volume perlu Δt (interval). Priority: High (jika volume dibutuhkan untuk pelaporan).

### 17. Correlation Analysis — NOT IMPLEMENTED
- Tidak ada fungsi korelasi (Pearson) di FE/BE. `analysis.js` tak punya `correlation`. Required: endpoint/util korelasi dengan **timestamp alignment** + handling null/duplikat. Priority: Low.

### 18. Parameter Statistics — PARTIAL
- `reports.py`: avg/min/max/count + **`stddev_pop`** (population, bukan sample). `analysis.js::calculateStats`: avg/min/max/median/stdDev (population). **P95** dihitung **client-side** (`Analytics/Index.vue::percentile95`) atas sampel chart terbatas. **Tidak ada** median/P95/P99 di **backend** SQL. Impact: statistik agregat besar tak akurat (hanya sampel). Required: endpoint `/analytics/statistics` (SQL percentile/median atas full range). Priority: Medium.

### 19. Exceedance Analysis — INCORRECT IMPLEMENTATION
- `reports.py::_build_violation_filter` + COUNT baris di luar baku mutu. **PROBLEM:** menghitung **jumlah baris** exceedance, **bukan** menggabungkan baris berturut jadi satu **event** (start/end/duration/peak). Contoh 3 baris berturut = 3, seharusnya 1 event. Required: grouping consecutive-exceedance. Priority: High.

### 20. Reliability / Availability — PARTIAL (tercampur)
- Tidak ada perhitungan availability terpisah (uptime/observation). `completeness` (rasio data) dipakai sebagai proksi ketersediaan — **dua konsep berbeda**. Logger heartbeat memberi liveness tapi belum diakumulasi jadi uptime%. Required: availability berbasis heartbeat (`logger_status.state_since` + histori event). Priority: Medium.

### 21. Data Transmission Monitoring — PARTIAL
- Heartbeat: `last_send_ok_mm`/`_klhk` (boolean terakhir), `buffer_depth` (antrean), `daily_sent`. Event `send_fail`. **Kurang:** total sent/success/failed/retry/pending kumulatif, **success rate %**, timestamp last-success/last-failed. `sparing_python::api_client` punya retry+backup tapi metriknya tak dikirim/disimpan agregat. Priority: Medium.

### 22. Raw Data Explorer — IMPLEMENTED
- `Pages/History/Index.vue` + `data.py::list_data`. Filter site/parameter/tanggal/interval; kolom Validasi (quality_flag) + badge op_status; paginasi; **Export Excel** (SheetJS) menarik **seluruh rentang** (loop halaman, bukan halaman aktif saja). Timezone WIB. Priority: Low.

### 23. Multi-Site Monitoring — IMPLEMENTED
- `sites` master (uid unik), `viewer_sites` (akses per user), device per site, filter site, site map (Leaflet), overview per site. Scoping viewer diberlakukan di BE (data/alerts/stats/logger). **Tidak ada hardcoded UID di web** (bug cross-site `device_uid` sudah diperbaiki jadi site-scoped). Catatan: default dataclass `admin-LOG` ada di repo **logger** (`config.py`), di-override `config.json` per Pi — bukan di web. Priority: Low.

---

## D. BUGS & LOGIC ERRORS

### Critical
1. **Tidak ada anti-duplikat pada `sensor_data`.** Lokasi: `models.py` (`sensor_data.__table_args__` = hanya `Index(site_id, ts)`, non-unique) + `getdata.py::post_data` (insert tanpa upsert/dedup). Cause: tak ada `UniqueConstraint(site_id, ts)`. Impact: perangkat retry / burst ganda bisa menyisipkan baris ganda → completeness overcount, average/statistik bias, exceedance/chart ganda. Fix: unique index `(site_id, ts)` + `INSERT … ON DUPLICATE KEY`/skip. **(Perlu migrasi + dedup data lama dulu.)**
2. **Dua sumber threshold compliance.** Lokasi: `analysis.js::standards` (hardcoded) vs `alert_rules`/`stats.py` (DB). Impact: halaman Analytics bisa menyatakan patuh/langgar berbeda dari Dashboard/laporan untuk data yang sama. Fix: satukan ke AlertRule.
3. **Exceedance dihitung per-baris, bukan per-event.** Lokasi: `reports.py`. Impact: jumlah kejadian pelanggaran salah (over-count), durasi/peak tak ada → laporan compliance menyesatkan. Fix: grouping consecutive.

### High
4. **Completeness memakai interval hardcoded 30/jam + menghitung baris non-pengukuran/duplikat.** Lokasi: `stats.py::completeness`. Impact: %kelengkapan bisa keliru bila cadence berbeda atau ada duplikat/kalibrasi. Fix: interval per-site + distinct-timestamp + kecualikan op_status.
5. **Tidak ada gap/missing-data detection.** Impact: tak bisa jawab "kapan data hilang". Fix: endpoint gap.
6. **Volume/debit tidak diintegrasikan.** Impact: tak ada total volume untuk pelaporan. Fix: integrasi Flow×Δt (perhatikan satuan L/min).
7. **P95/median statistik dihitung dari sampel client-side (chartData terbatas).** Lokasi: `Analytics/Index.vue`. Impact: statistik "periode" tidak mewakili seluruh data. Fix: hitung di SQL.
8. **`_num()` tak memvalidasi voltage/current & batas atas TSS/COD/NH3-N.** Lokasi: `getdata.py::_num` (pH 0–14, tss/cod/debit/nh3n hanya `lo=0`; voltage/current tanpa batas). Impact: nilai ekstrem/janggal tersimpan. Fix: rentang wajar per parameter (konfigurasi).
9. **N+1 di Dashboard/Devices** (`getDeviceHealth` per device, `getLatestData` per site). Impact: latency & beban DB naik dengan jumlah site/device. Fix: endpoint agregat.

### Medium
10. Availability disamakan dengan completeness (konsep beda).
11. Event timeline tidak terpadu (exceedance/maintenance/calibration di luar `logger_events`).
12. Kalibrasi tak menyimpan before/after/offset.
13. Maintenance overdue/due tak dihitung/disurface.
14. Transmission tak punya success-rate/rekam kumulatif.
15. Power = V×I & alarm power tak ada.
16. Anomaly detection ganda (BE MAD vs FE IQR) tak direkonsiliasi.

### Low
17. `logger_version` tampil "unknown" (tak ada konstanta VERSION di logger config).
18. Bundle FE > 1.6MB (belum code-split).
19. Frontend `standards` mencantumkan temp/voltage/current yang sebagian tak dipakai.
20. Reports `stddev_pop` (population) vs kemungkinan kebutuhan sample stddev — konfirmasikan definisi.
21. Tak ada retensi/purge untuk `sensor_data` yang tumbuh (~1jt baris/site/tahun).

---

## E. MISSING FEATURES

**Must Have:** anti-duplikat `sensor_data`; satukan threshold; exceedance-event grouping; gap/missing-data; validasi rentang parameter penuh.
**Should Have:** total volume; statistik agregat SQL (median/P95/P99); availability terpisah; transmission success-rate; maintenance overdue; power (W)+alarm.
**Nice to Have:** correlation; event timeline terpadu; notifikasi eksternal (email/WA); kalibrasi before/after/offset; retensi data.

---

## F. HARDCODE / MOCK FINDINGS

| File | Fungsi | Nilai hardcoded | Risk | Rekomendasi |
|---|---|---|---|---|
| `sparing_front/.../Utils/analysis.js` | `standards` | Baku mutu (ph 6–9, tss 100, cod 200, nh3n 10, V 200–240, I 0–10) | High (beda dari DB AlertRule) | Ambil dari `/alert-rules` |
| `sparing_api/.../routers/stats.py` | `READINGS_PER_SITE_PER_HOUR` | `30` | Medium | Derive dari interval/`Site` |
| `sparing_api/.../utils/anomaly_engine.py` | konstanta | rentang plausible, K spike, window drift/flatline | Low (wajar, tapi non-configurable) | Pindahkan ke config bila perlu |
| `sparing_python/config.py` | `uid_1` default | `admin-LOG` | Low (di-override `config.json`) | Pastikan tiap Pi punya config.json |

Tidak ditemukan `Math.random`, `dummy`, `mock`, `TODO/FIXME` terkait fitur SPARING di frontend. Status online/offline & completeness = **data nyata**.

---

## G. DATABASE GAP ANALYSIS (perubahan minimum efektif)

Skema existing sebagian besar memadai. Perubahan minimum:
1. **`sensor_data`**: tambah **UNIQUE(site_id, ts)** (setelah dedup data lama). Kritis.
2. **`sites`** atau `sensor_devices`: kolom `data_interval_seconds` (default 120) → completeness/gap konfigurabel.
3. **`maintenance_logs`**: (opsional) `before_value`, `after_value`, `offset` untuk kalibrasi formal.
4. **(Opsional)** tabel/agregat `transmission_stats` bila metrik kirim kumulatif diperlukan — atau turunkan dari `logger_events`/`ingest_logs` yang sudah ada (hindari tabel baru bila cukup).
Index existing sudah baik (`site_id`, `ts`, `device_id`, `device_uid`, `created_at` ter-index; unique pada uid site, alert_rule (site,field), sensor_health, logger_event (site,event_uid)).

---

## H. API GAP ANALYSIS (hanya yang belum bisa dilayani endpoint existing)

```
GET /analytics/gaps?site_uid&date_from&date_to        # missing-data / gap (#06)
GET /analytics/exceedance?site_uid&field&date_from…   # event grouping start/end/duration/peak (#19)
GET /analytics/statistics?site_uid&field&period       # median/P95/P99 di SQL (#18)
GET /analytics/volume?site_uid&date_from&date_to      # total volume dari debit (#16)
GET /analytics/availability?site_uid&period           # uptime berbasis heartbeat (#20)
GET /transmission/summary?site_uid&period             # success-rate/last-sent (#21)  (bisa turunan)
```
Sisanya (compliance, completeness, data, alerts, logger status/events, device health, reports) sudah ada dan dipakai FE.

---

## I. PRIORITY IMPLEMENTATION ROADMAP

**PRIORITY 1 — Critical Operational (correctness & data integrity)**
- Anti-duplikat `sensor_data` (unique + upsert) — files: `models.py`, migrasi baru, `getdata.py` — dep: dedup data lama — **L** — risk: tinggi (perlu migrasi hati-hati).
- Satukan threshold ke AlertRule (drop `analysis.js::standards`) — `Analytics/Index.vue`, `analysis.js` — **M** — risk: rendah.
- Exceedance-event grouping — `reports.py` (+endpoint) — **M** — risk: rendah.
- Completeness: interval-configurable + distinct + exclude op_status — `stats.py` — **S/M** — risk: rendah.
- Validasi rentang parameter penuh — `getdata.py::_num` — **S** — risk: rendah.

**PRIORITY 2 — Compliance & Maintenance**
- Gap/missing-data endpoint — **M**. Volume dari debit (Flow×Δt) — **M**. Maintenance overdue + kalibrasi before/after — **M**.

**PRIORITY 3 — Analytics**
- Statistik agregat SQL (median/P95/P99) — **M**. Availability terpisah — **M**. Transmission success-rate — **M**.

**PRIORITY 4 — Advanced Intelligence**
- Correlation — **M**. Event timeline terpadu — **M**. Power (W)+alarm — **S**. Notifikasi eksternal — **M**.

---

## J. FINAL SCORE (0–100)

| Aspek | Skor | Dasar |
|---|---|---|
| Frontend | 82 | v2 konsisten, realtime, export; N+1 & bundle besar |
| Backend | 78 | router rapi, scheduler, lifecycle alarm; beberapa analitik kurang |
| Database Design | 70 | index baik; **tak ada unique anti-duplikat**; interval hardcoded |
| Data Quality | 62 | validasi parsial; risiko duplikat; op_status/anomali dikecualikan dengan benar |
| Monitoring | 80 | realtime + logger heartbeat + dead-man's switch kuat |
| Compliance | 65 | benar di BE stats; dua sumber threshold; exceedance salah hitung |
| Analytics | 45 | statistik dasar; tanpa gap/korelasi/volume/percentile-BE |
| Device Health | 72 | logger/sensor health baik; kalibrasi/power kurang |
| Maintainability | 78 | struktur jelas, test backend (~143), TDD; sedikit duplikasi FE/BE |
| Performance | 68 | query ter-range & paginasi; N+1 & tanpa retensi |
| Security | 76 | JWT, argon2, role-gating, viewer-scoping, rate-limit; audit-log belum ada |
| **Overall Production Readiness** | **~72** | **Pilot Ready** |

---

## NEXT RECOMMENDED ACTION (maks 10, urut prioritas)

1. **Anti-duplikat `sensor_data`** (unique `(site_id, ts)` + dedup data lama + upsert di ingest) — correctness & integritas dasar semua metrik.
2. **Satukan threshold** ke `AlertRule` (buang `analysis.js::standards`) — hilangkan compliance yang bertentangan.
3. **Perbaiki completeness** — interval per-site configurable, hitung distinct-timestamp, kecualikan op_status.
4. **Exceedance-event grouping** (bukan per-baris) — laporan pelanggaran benar.
5. **Validasi rentang parameter penuh** di ingest (`_num`) — cegah nilai janggal masuk.
6. **Gap/missing-data endpoint + tampilan** — jawab "kapan data hilang".
7. **Statistik agregat di SQL** (median/P95/P99 atas full range) — statistik akurat.
8. **Total volume** dari debit (Flow×Δt, satuan benar) — kebutuhan pelaporan.
9. **Availability berbasis heartbeat** (pisahkan dari completeness).
10. **Transmission success-rate** + maintenance overdue — kelengkapan operasional.
