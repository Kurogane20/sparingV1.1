# Site-Specific Timezone Display

**Date:** 2026-06-09
**Status:** Approved

## Problem

All timestamps in the app are currently displayed in `Asia/Jakarta` (WIB, UTC+7) regardless of the site's actual location. Sites in Central or Eastern Indonesia (WITA/WIT) show incorrect local times.

## Goal

Display all timestamps — table cells, cards, charts, tooltips — in the timezone of the site whose data is being shown.

## Timezone Options

Indonesia has three standard timezone zones:

| Label | IANA String | UTC Offset |
|---|---|---|
| WIB – Waktu Indonesia Barat | `Asia/Jakarta` | UTC+7 |
| WITA – Waktu Indonesia Tengah | `Asia/Makassar` | UTC+8 |
| WIT – Waktu Indonesia Timur | `Asia/Jayapura` | UTC+9 |

## Architecture

### Backend

**`Site` model** (`models.py`):
- Add `timezone: Mapped[str] = mapped_column(String(64), default='Asia/Jakarta')`

**Schemas** (`schemas/site.py`):
- `SiteCreate`: add `timezone: str = 'Asia/Jakarta'`
- `SiteUpdate`: add `timezone: str | None = None`
- `SiteOut`: add `timezone: str`

**Migration** `0005_add_site_timezone.py`:
- `op.add_column('sites', Column('timezone', String(64), nullable=False, server_default='Asia/Jakarta'))`

### Frontend — `helpers.js`

Update `formatDate` and `formatTime` to accept an optional `tz` parameter:

```js
export function formatDate(date, includeTime = false, tz = 'Asia/Jakarta') { ... }
```

Uses `{ timeZone: tz }` in `toLocaleDateString` options. `parseUTC` stays unchanged.

Export a new helper `formatTime(date, tz)` for time-only display (used in History).

### Frontend — Sites Form (`Sites/Index.vue`)

Add timezone dropdown to the site create/edit form:

```
[ WIB – Waktu Indonesia Barat (UTC+7)  ▼ ]
  WITA – Waktu Indonesia Tengah (UTC+8)
  WIT  – Waktu Indonesia Timur (UTC+9)
```

Existing sites default to WIB (set by server_default in migration).

### Frontend — Pages

Each page already loads the currently-selected site. Pass `site.timezone` to all `formatDate` / `formatTime` calls.

| Page | Site source | Timestamps affected |
|---|---|---|
| Dashboard | `currentSite.timezone` | Last seen, chart labels, chart tooltips |
| Analytics | selected site from `sites` list | Chart labels, chart tooltips, CSV export |
| History | selected site from `sites` list | `ts` column (date + time), CSV export |
| Reports | selected site from form | Violation table `ts`, generated_at header |
| Devices | site per device (via `deviceHealth`) | Calibration dates, maintenance log dates |

### Frontend — ApexCharts (Dashboard + Analytics)

Chart options are `computed` properties. Add `xaxis.labels.formatter` and `tooltip.x.formatter`:

```js
xaxis: {
  type: 'datetime',
  labels: {
    formatter: (val) => new Date(val).toLocaleString('id-ID', {
      timeZone: siteTz,
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    })
  }
},
tooltip: {
  x: {
    formatter: (val) => new Date(val).toLocaleString('id-ID', {
      timeZone: siteTz,
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  }
}
```

`siteTz` is a `computed` derived from the selected site's `timezone` field.

## Data Flow

```
IoT Logger → UTC epoch → DB stores UTC literal
    ↓
FastAPI returns naive datetime string (e.g. "2026-06-09T16:00:00")
    ↓
Frontend parseUTC() appends 'Z' → actual UTC Date object
    ↓
formatDate(date, includeTime, site.timezone) → displays in site's local time
```

## Devices Page Special Case

Devices can belong to different sites. The timezone for calibration/maintenance dates should use the timezone of the device's site. The `deviceHealth` API response already includes `site_uid`; the Devices page already loads the full site list — look up timezone by matching `device.site_id` to the loaded sites.

## Error Handling

- If `site.timezone` is missing or invalid, fall back to `'Asia/Jakarta'`. `Intl.DateTimeFormat` throws a `RangeError` for unknown timezone strings — catch it in `formatDate` and use the fallback.

## Out of Scope

- Auto-deriving timezone from lat/lon coordinates
- Timezone support outside Indonesia
- User-level timezone override

## Files to Change

**Backend:**
- `sparing_api/app/models/models.py`
- `sparing_api/app/schemas/site.py`
- `sparing_api/alembic/versions/0005_add_site_timezone.py` (new)

**Frontend:**
- `sparing_front/resources/js/Utils/helpers.js`
- `sparing_front/resources/js/Pages/Sites/Index.vue`
- `sparing_front/resources/js/Pages/Dashboard/Index.vue`
- `sparing_front/resources/js/Pages/Analytics/Index.vue`
- `sparing_front/resources/js/Pages/History/Index.vue`
- `sparing_front/resources/js/Pages/Reports/Index.vue`
- `sparing_front/resources/js/Pages/Devices/Index.vue`
