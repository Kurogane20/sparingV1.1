# UI Re-theme — "Teal/Ink Compliance" Design Language

**Status:** Approved (brainstorming)
**Date:** 2026-07-16
**Reference mockup:** sparing-ui-v2.html (Berau site) — used as a design-language
reference only; app content/data (Mitra Mutiara, WIB, 4 sites) is unchanged.

## Goal
Re-skin the entire Vue frontend (all pages + shared components) from the current
"modern-spacious blue/Inter" look to a "formal-compact teal/ink compliance" look,
without changing any functionality, routes, or data.

## Design tokens

**Colors** (map onto existing token slots so most usages update centrally):
| Role | New value |
|---|---|
| primary / action | `#0E7C86` (hover/dark `#0A5A62`) |
| primary soft tint | `#E4F1F2` |
| ink (sidebar, headings) | `#12333B` (secondary ink `#1A424C`) |
| page background | `#EEF2F3` |
| card | `#FFFFFF` |
| border | `#D7E0E1` (stronger `#C4D1D3`) |
| text / muted | `#26383C` / `#617377` |
| status ok | text `#1F7A4D`, bg `#E6F2EC` |
| status warning | text `#9A6B00`, bg `#F7EFD9` |
| status danger/bad | text `#B03030`, bg `#F7E4E4` |
| status offline | text `#6E7E82`, bg `#EAEEEF` |

**Typography:**
- sans: **Source Sans 3** (replaces Inter)
- mono: **IBM Plex Mono** (replaces JetBrains Mono) — used for numeric values,
  sensor readings, timestamps, IDs.

**Component style shift:**
- Cards: thin border + 8px radius, less shadow/gradient, denser padding.
- Status badges: small 4px-radius chips, formal (non-pastel) status colors.
- Tables: uppercase muted headers, thin rules, mono right-aligned numbers, subtle row hover.
- Sidebar: dark ink; active item solid white.
- KPI/sensor values: mono font; 3px left accent per status.

## Implementation approach
1. **Foundation (central, auto-propagates):** `tailwind.config.js` colors +
   fonts, `resources/css/app.css` `:root` variables + base font + component
   classes (`.card`, `.btn-*`, etc.), `index.html` Google Fonts links.
2. **Sweep literal colors:** components/pages that hardcode `bg-blue-*`,
   `text-slate-*`, bright `emerald/amber/rose` → the new teal/ink/status palette.
   Order: shared components (Sidebar, Header, SensorCard, DataTable, StatusBadge,
   AlertDropdown, Toast, SiteMap) → pages (Dashboard, Login, Analytics, Reports,
   History, Sites, Devices, Users, Settings).

## Out of scope
No new pages/features, no layout restructuring beyond styling, no data/timezone
changes, no backend changes. Functionality and routes stay identical.
