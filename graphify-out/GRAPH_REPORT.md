# Graph Report - sparingV1.1  (2026-08-21)

## Corpus Check
- 169 files · ~147,013 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2209 nodes · 3015 edges · 175 communities (161 shown, 14 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 408 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d96d4055`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Anomaly Detection Engine
- Database Models
- Dashboard Page
- Devices Page
- Alert Engine & Rules
- Sites & Data API
- Report Generation
- Reports Page
- Sites Page
- Ingestion & Time Utils
- App Bootstrap & Scheduler
- Metrics & Caching
- API Exceptions
- Analytics Page
- Users Page
- App Router & Entry
- History Page
- Site Map & Sidebar
- Devices & Maintenance API
- Frontend Dependencies
- Alert Notifications UI
- Device Ingest Endpoint
- Header Component
- Device Health Status
- Deploy Script
- Frontend Helpers
- Sensor Card Component
- Analytics Utils
- Build Tooling
- Auth & API Composables
- Getdata API Tests
- Package Manifest
- Alembic Env
- Auth Schemas & Routes
- Devices Page Actions
- App Config & Settings
- Auth API Tests
- Deploy Functions
- Request ID Middleware
- Data Table Component
- Status Badge Component
- Toast Component
- App Layout
- Common Schemas
- KLHK Threshold Checks
- Toast Composable
- Health Status Helpers
- Confirm Composable
- Log Type Helpers
- Maintenance Log UI
- What You Must Do When Invoked
- 🚀 SPARING - Quick Reference Card
- 🔧 Setup Fix - Switched from Inertia.js to Vue Router
- Part 2 — Frontend restructure
- 🎉 SPARING Frontend - Update Summary
- Feature 1: Alert & Notification System — Implementation Plan
- Sensor Data Quality & Anomaly Detection — Design
- SPARING Feature Roadmap — Design Spec
- Sensor Data Quality & Anomaly Detection Implementation Plan
- Site-Specific Timezone Display
- SPARING Frontend - Project Structure
- File Structure
- Site-Specific Timezone Display — Implementation Plan
- post_data
- Feature 3: Device Health & Maintenance Log — Implementation Plan
- Feature 4: Regulatory Report Generator — Implementation Plan
- generate_device_secret
- SPARING API Documentation
- ingest_state
- Endpoints
- graphify reference: extra exports and benchmark
- Admin Endpoints
- Deployment Options
- Production Deployment Guide
- TTLCache
- Alert
- SPARING Frontend - Implementation Guide
- graphify reference: query, path, explain
- UI Re-theme — "Teal/Ink Compliance" Design Language
- jspdf
- Sites Management
- Monitoring & Maintenance
- Troubleshooting
- 🎯 Best Practices Applied
- list_data
- Authentication
- Devices Management
- Environment Configuration
- 📊 Dashboard Implementation
- 🛠️ Helper Functions
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Database Setup
- Option 2: Kubernetes
- Security Checklist
- Scaling Considerations
- Reverse Proxy Setup (Nginx)
- 🎨 Reusable Components
- 🔐 Authentication Flow
- 🚀 Deployment
- 📜 History Page Implementation
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- SensorHealthOut
- Data Ingestion
- Updating the Application
- 🏗️ Architecture
- 📱 Responsive Design
- 🧪 Testing Strategy
- 📝 Code Style Guide
- 🔄 Component Communication
- 🔧 Device Management
- 🔮 Future Enhancements
- CLAUDE.md
- CLAUDE.md
- extraction-spec.md
- File Structure
- 🔌 API Integration
- File Structure
- File Structure
- SPARING API Documentation
- dedup_sensor_data.py
- onSiteChange
- package.json
- 🏗️ Architecture
- UtilityStrip.vue
- Option 1: Docker Compose (Recommended for Small-Medium Scale)
- Login.vue
- Sparkline.vue
- Authentication
- 🛠️ Helper Functions
- 🐛 Troubleshooting
- load
- xlsx
- 🔧 Admin Tasks
- 📈 Fitur Analytics
- app.js
- LoggerEventTimeline.vue
- AlertFollowupModal.vue
- login-page.test.mjs
- LoginMonitoringGraphic.vue
- PageHeader.vue
- getDeviceStatus
- 📦 Components
- 🚀 Setup Instructions
- Option 2: Kubernetes
- 🐛 Troubleshooting
- 📈 Data Flow
- 🔐 Authentication
- 🎨 Design System
- refreshAll
- Development
- 🔧 Admin Tasks
- 📈 Fitur Analytics

## God Nodes (most connected - your core abstractions)
1. `Site` - 51 edges
2. `User` - 39 edges
3. `Alert` - 27 edges
4. `C. DETAIL AUDIT 01–23` - 24 edges
5. `SensorData` - 22 edges
6. `generate_report()` - 20 edges
7. `LoggerStatus` - 19 edges
8. `scan_logger_liveness()` - 19 edges
9. `SPARING Frontend - Implementation Guide` - 19 edges
10. `Base` - 17 edges

## Surprising Connections (you probably didn't know these)
- `get_current_user()` --indirect_call--> `AuthTokenBlacklist`  [INFERRED]
  sparing_api/app/api/deps.py → sparing_api/app/models/models.py
- `assign_viewer()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `assign_viewer()` --indirect_call--> `ViewerSite`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `unassign_viewer()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `unassign_viewer()` --indirect_call--> `ViewerSite`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py

## Import Cycles
- 1-file cycle: `sparing_api/app/api/routers/__init__.py -> sparing_api/app/api/routers/__init__.py`
- 1-file cycle: `sparing_front/resources/js/app.js -> sparing_front/resources/js/app.js`

## Communities (175 total, 14 thin omitted)

### Community 0 - "Anomaly Detection Engine"
Cohesion: 0.07
Nodes (59): Alternating small noise around 7.0 — a realistic stable pH series., _series(), _stable(), test_as_utc_already_aware_stays_utc(), test_as_utc_naive_treated_as_utc(), test_drift_empty_windows_not_flagged(), test_drift_stable_not_flagged(), test_drift_sustained_shift_flagged() (+51 more)

### Community 1 - "Database Models"
Cohesion: 0.16
Nodes (16): change_password(), login(), logout(), me(), AsyncSession, Change own password (requires current password verification)., Authenticate user and return JWT tokens., Logout user by blacklisting the current access token. (+8 more)

### Community 2 - "Dashboard Page"
Cohesion: 0.03
Nodes (53): activeAlertCountKpi, activeAlertsTop, alarmNote, alertRulesByField, chartData, chartOptions, chartPeriod, chartSeries (+45 more)

### Community 3 - "Devices Page"
Cohesion: 0.05
Nodes (36): activeDevicesCount, addingLog, canManageDevices, { confirm }, DANGER_STYLE, DATA_STATUS_MAP, deviceForm, deviceHealth (+28 more)

### Community 4 - "Alert Engine & Rules"
Cohesion: 0.06
Nodes (68): acknowledge_alert(), _build_alert_out(), followup_alert(), get_alert_count(), list_alerts(), AsyncSession, datetime, Close an alert. A follow-up note is mandatory (SOP: no closure without a record) (+60 more)

### Community 5 - "Sites & Data API"
Cohesion: 0.10
Nodes (36): ingest_events(), list_logger_events(), list_logger_status(), AsyncSession, datetime, Request, Logger telemetry ingest.  Liveness is always judged on the SERVER clock (last_, None = no restriction (admin/operator); a list = the viewer's sites only. (+28 more)

### Community 6 - "Report Generation"
Cohesion: 0.09
Nodes (40): date, _build_violation_filter(), generate_report(), AsyncSession, Build SQLAlchemy WHERE clause for values outside baku mutu limits., BakuMutuOut, DailySummaryOut, ExceedanceEventOut (+32 more)

### Community 7 - "Reports Page"
Cohesion: 0.07
Nodes (21): completeness, doGenerateReport(), exportingPdf, { filterSitesByUser }, form, getPeriodDates(), { getSites, generateReport: apiGenerateReport, getCompleteness }, loading (+13 more)

### Community 8 - "Sites Page"
Cohesion: 0.07
Nodes (28): addRule(), alertRules, AVAILABLE_FIELDS, closeModal(), { confirm }, deleteSiteHandler(), deviceKey, editingSite (+20 more)

### Community 9 - "Ingestion & Time Utils"
Cohesion: 0.09
Nodes (27): JsonFormatter, BaseHTTPMiddleware, Request, RateLimitMiddleware, _ago(), datetime, test_health_boundary_offline(), test_health_boundary_online() (+19 more)

### Community 10 - "App Bootstrap & Scheduler"
Cohesion: 0.08
Nodes (22): get_db(), init_models(), api_error_handler(), _check_logger_liveness(), _check_offline_devices(), _cleanup_expired_tokens(), _detect_anomaly_drift(), general_exception_handler() (+14 more)

### Community 11 - "Metrics & Caching"
Cohesion: 0.08
Nodes (42): last_record(), list_data(), AsyncSession, datetime, ingest_bulk(), ingest_state(), AsyncSession, Request (+34 more)

### Community 12 - "API Exceptions"
Cohesion: 0.11
Nodes (19): APIError, AuthenticationError, ConflictError, ForbiddenError, InternalServerError, NotFoundError, Any, Exception (+11 more)

### Community 13 - "Analytics Page"
Cohesion: 0.04
Nodes (32): @/Utils/analysis.js, availability, barOptions, barSeries, chartData, colors, completeness, completenessPct (+24 more)

### Community 14 - "Users Page"
Cohesion: 0.07
Nodes (28): accessMatrix, allSites, apiErrorMessage(), closeModal(), closeSitesModal(), { confirm }, deleteUser(), editingUser (+20 more)

### Community 15 - "App Router & Entry"
Cohesion: 0.08
Nodes (24): applyFilters(), availableFields, dateDifferenceInDays, exporting, filters, { filterSitesByUser }, { getData, getSites }, getDefaultDateFrom() (+16 more)

### Community 16 - "History Page"
Cohesion: 0.13
Nodes (15): Backend, Backend (`sparing_api/.env`), Default Credentials (Development), Development, Docker, Documentation, Environment Variables, Features (+7 more)

### Community 17 - "Site Map & Sidebar"
Cohesion: 0.09
Nodes (25): leaflet/dist/leaflet.css, alertCount, allGroups, { getAlertCount, getLoggerStatus }, isActive(), loggerDownCount, { logout, user, isAdmin, isViewer }, route (+17 more)

### Community 18 - "Devices & Maintenance API"
Cohesion: 0.10
Nodes (29): get_key(), _global_secret(), _insert_ignore_duplicates(), _num(), post_data(), AsyncSession, Request, Extract a numeric field by any of `keys` (first non-None wins).      Returns ( (+21 more)

### Community 19 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (20): apexcharts, axios, chart.js, html2canvas, jspdf, dependencies, apexcharts, axios (+12 more)

### Community 20 - "Alert Notifications UI"
Cohesion: 0.12
Nodes (14): activeCount, alerts, ANOMALY_LABELS, dropdownRef, fetchAlerts(), FIELD_LABELS, { getAlertCount, getAlerts, acknowledgeAlert }, getAlertTitle() (+6 more)

### Community 21 - "Device Ingest Endpoint"
Cohesion: 0.05
Nodes (39): 01. Executive Dashboard — IMPLEMENTED, 02. Real-time Monitoring — IMPLEMENTED (polling), 03. Historical Trend — IMPLEMENTED, 04. Compliance / Baku Mutu — PARTIAL, 05. Data Completeness — PARTIAL, 06. Missing Data / Gap Analysis — NOT IMPLEMENTED, 07. Communication Monitoring — PARTIAL (berlapis, via heartbeat), 08. Sensor Health — PARTIAL (+31 more)

### Community 22 - "Header Component"
Cohesion: 0.08
Nodes (48): create_alert_rule(), delete_alert_rule(), _get_site_by_uid(), list_alert_rules(), AsyncSession, update_alert_rule(), AlertRule, AlertActionIn (+40 more)

### Community 23 - "Device Health Status"
Cohesion: 0.15
Nodes (13): Component API Reference, 📦 Components, 🎣 Composables, 🎨 CSS Classes, DataTable, Header, SensorCard, Sidebar (+5 more)

### Community 24 - "Deploy Script"
Cohesion: 0.41
Nodes (13): build_frontend(), check_deps(), copy_api(), die(), info(), install_nginx(), install_service(), main() (+5 more)

### Community 25 - "Frontend Helpers"
Cohesion: 0.19
Nodes (5): formatDate(), formatTime(), getRelativeTime(), getSensorStatus(), parseUTC()

### Community 26 - "Sensor Card Component"
Cohesion: 0.17
Nodes (11): accentColor, cardStatus, displayValue, fieldAccentMap, props, statusRingClass, thresholdStatus, trendClass (+3 more)

### Community 27 - "Analytics Utils"
Cohesion: 0.29
Nodes (11): analyzeParameter(), calculateCompliance(), calculateStats(), calculateTrend(), detectAnomalies(), generateFullAnalysis(), generateRecommendations(), getComplianceStatus() (+3 more)

### Community 28 - "Build Tooling"
Cohesion: 0.18
Nodes (11): autoprefixer, postcss, devDependencies, autoprefixer, postcss, tailwindcss, vite, @vitejs/plugin-vue (+3 more)

### Community 29 - "Auth & API Composables"
Cohesion: 0.31
Nodes (8): apiClient, useApi(), decodeJWT(), NOTE: This requires backend to allow viewer/operator access to /admin/viewer-sit, token, useAuth(), user, logger

### Community 30 - "Getdata API Tests"
Cohesion: 0.15
Nodes (13): Alert Channels, Alert Rules, Alerting, Alertmanager Configuration, Best Practices, Checklist, Dashboard Examples, Distributed Tracing (+5 more)

### Community 31 - "Package Manifest"
Cohesion: 0.06
Nodes (36): 1. Prerequisites, 2. Installation, 3. Development, 4. Production Build, API Connection Issues, 📊 API Integration, 🔐 Authentication, Authentication Errors (+28 more)

### Community 32 - "Alembic Env"
Cohesion: 0.29
Nodes (7): Connection, do_run_migrations(), Run migrations in 'offline' mode., Configure context and run migrations given a sync Connection., Run migrations in 'online' mode with an **async** engine., run_migrations_offline(), run_migrations_online()

### Community 33 - "Auth Schemas & Routes"
Cohesion: 0.06
Nodes (33): Admin Endpoints, Assign Viewer to Site (admin only), Bulk Ingest, Create Device (admin/operator only), Create Site (admin/operator only), Data Ingestion, Data Retrieval, Delete Device (admin only) (+25 more)

### Community 34 - "Devices Page Actions"
Cohesion: 0.25
Nodes (8): closeModal(), deleteDeviceHandler(), loadDevices(), loadHealthForDevices(), loadLoggerStatuses(), loadSites(), saveDevice(), toggleDeviceStatus()

### Community 35 - "App Config & Settings"
Cohesion: 0.29
Nodes (4): BaseSettings, Refuse to start in production with a default/empty JWT secret.          A defa, Parse cors_origins_str into a list of origins., Settings

### Community 36 - "Auth API Tests"
Cohesion: 0.06
Nodes (32): 1️⃣ Install Dependencies, 2️⃣ Configure Environment, 3️⃣ Start Development Server, 4️⃣ Open in Browser, 5️⃣ Login with Test Credentials, 6️⃣ Explore the Application, Add a New API Endpoint, Add a New Page (+24 more)

### Community 37 - "Deploy Functions"
Cohesion: 0.90
Nodes (4): deploy_backend(), deploy_frontend(), say(), deploy.sh script

### Community 38 - "Request ID Middleware"
Cohesion: 0.40
Nodes (3): BaseHTTPMiddleware, Request, RequestIDMiddleware

### Community 39 - "Data Table Component"
Cohesion: 0.40
Nodes (4): paginationText, props, totalPages, visiblePages

### Community 40 - "Status Badge Component"
Cohesion: 0.40
Nodes (4): dotClass, props, showDot, statusClasses

### Community 41 - "Toast Component"
Cohesion: 0.40
Nodes (4): icons, { state: confirmState, answer }, styles, { toasts }

### Community 42 - "App Layout"
Cohesion: 0.33
Nodes (3): isMobile, lastSync, sidebarOpen

### Community 43 - "Common Schemas"
Cohesion: 0.67
Nodes (3): Message, Page, BaseModel

### Community 44 - "KLHK Threshold Checks"
Cohesion: 0.50
Nodes (3): check_thresholds(), KLHK baku mutu thresholds — logs warnings on exceedance., Return list of threshold violations and log each one.

### Community 45 - "Toast Composable"
Cohesion: 0.67
Nodes (3): show(), toasts, useToast()

### Community 46 - "Health Status Helpers"
Cohesion: 0.07
Nodes (18): activeLoggerAlarms, aliveCount, DANGER_STYLE, events, events24h, eventsLoading, { getLoggerStatus, getLoggerEvents, getAlerts }, OFFLINE_STYLE (+10 more)

### Community 55 - "Maintenance Log UI"
Cohesion: 0.67
Nodes (3): loadMaintenanceLogs(), openMaintenanceModal(), submitLog()

### Community 61 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 62 - "🚀 SPARING - Quick Reference Card"
Cohesion: 0.15
Nodes (13): 🔄 Auto-Refresh, 📊 Baku Mutu (Standar Compliance), 🔑 Default Credentials, ⌨️ Keyboard Shortcuts, Parameter Air Limbah (Dashboard), Parameter Tambahan, 📱 Responsive Breakpoints, 🎯 Sensor Parameters (+5 more)

### Community 63 - "🔧 Setup Fix - Switched from Inertia.js to Vue Router"
Cohesion: 0.08
Nodes (25): 1. Clean Install Dependencies, 2. Create Environment File, 3. Start Development Server, After (Vue Router), 🔐 Authentication Flow, Before (Inertia.js), ✨ Benefits of This Change, 📝 Changed Files (+17 more)

### Community 64 - "Part 2 — Frontend restructure"
Cohesion: 0.08
Nodes (24): 1.1 Alert follow-up workflow (migration `0007_alert_followup`), 1.2 Stats endpoints (new router `app/api/routers/stats.py`, prefix `/stats`), 1.3 History aggregation, 1.4 Per-row validation flag (migration `0008_sensor_data_quality_flag`), 2.1 App shell v2 (`AppLayout.vue` rework; `Header.vue` retired), 2.2 Login v2 (`Login.vue`), 2.3 Dashboard v2 (`Pages/Dashboard/Index.vue`), 2.4 Alarm page (new `Pages/Alarms/Index.vue`, route `/alarms`) (+16 more)

### Community 65 - "🎉 SPARING Frontend - Update Summary"
Cohesion: 0.09
Nodes (22): 1. **Dashboard** ✅, 2. **Analytics Page** ✅, 3. **User Management** ✅, 4. **Site Management** ✅, 5. **Routing Updated** ✅, 6. **Sidebar Menu Updated** ✅, Akses Halaman Baru, Analytics (+14 more)

### Community 66 - "Feature 1: Alert & Notification System — Implementation Plan"
Cohesion: 0.09
Nodes (21): Backend — Create, Backend — Modify, Feature 1: Alert & Notification System — Implementation Plan, File Map, Frontend — Create, Frontend — Modify, Post-Implementation Checklist, Task 10: Integrate alert engine into ingest endpoints (+13 more)

### Community 67 - "Sensor Data Quality & Anomaly Detection — Design"
Cohesion: 0.10
Nodes (19): A. Extend `alerts` table (Alembic migration), Amendment (2026-06-29) — burst-ingest anchoring, `anomaly_engine.py`, API, Architecture, B. New table `sensor_health`, Components, Data flow (+11 more)

### Community 68 - "SPARING Feature Roadmap — Design Spec"
Cohesion: 0.12
Nodes (16): Backend, Backend, Backend, Backend, Context, Feature 1 — Alert & Notification System, Feature 2 — API Key Management (Per-Site Device Secret), Feature 3 — Device Health & Maintenance Log (+8 more)

### Community 69 - "Sensor Data Quality & Anomaly Detection Implementation Plan"
Cohesion: 0.12
Nodes (15): Deployment notes (run after all tasks; not part of task commits), File Structure, Self-Review Notes, Sensor Data Quality & Anomaly Detection Implementation Plan, Task 0: Test tooling setup, Task 10: Frontend — health badge + data_quality alert display, Task 1: Config, `AnomalyResult`, and `check_implausible`, Task 2: `check_flatline` (+7 more)

### Community 70 - "Site-Specific Timezone Display"
Cohesion: 0.12
Nodes (15): Architecture, Backend, Data Flow, Devices Page Special Case, Error Handling, Files to Change, Frontend — ApexCharts (Dashboard + Analytics), Frontend — `helpers.js` (+7 more)

### Community 71 - "SPARING Frontend - Project Structure"
Cohesion: 0.12
Nodes (15): 🔌 API Integration Map, 🎨 Asset Dependencies, 📦 Build Output Structure, 🎯 Component Hierarchy, 🔄 Data Flow Diagram, 🚀 Development Workflow, 📂 Directory Breakdown, 📊 File Size Overview (+7 more)

### Community 72 - "File Structure"
Cohesion: 0.13
Nodes (14): File Structure, Self-Review Notes, Task 0: Baseline — suite green, Task 10: Full suite, deploy, production verification, Task 1: Alert follow-up columns (model + migration 0007), Task 2: `quality_flag` column + passthrough in /data (model + migration 0008, TDD), Task 3: Follow-up / resolve endpoints with mandatory note (TDD), Task 4: `/alerts` filters + optional pagination wrapper (TDD) (+6 more)

### Community 73 - "Site-Specific Timezone Display — Implementation Plan"
Cohesion: 0.15
Nodes (12): File Map, Site-Specific Timezone Display — Implementation Plan, Task 10: Build, Migrate, and Deploy, Task 1: Backend — Migration + Model + Schema, Task 2: Backend — Update Site and Reports Routers, Task 3: Frontend — Parameterize `helpers.js`, Task 4: Frontend — Sites Form Timezone Dropdown, Task 5: Frontend — Dashboard Timezone (+4 more)

### Community 74 - "post_data"
Cohesion: 0.08
Nodes (25): 1.1 Heartbeat (every 2 min), 1.2 Local event log + retroactive sync, 1.3 Crash vs clean restart, 1.4 Last gasp, 2.1 Tables (migration `0009_logger_monitoring`), 2.2 Endpoints, 2.3 Dead-man's switch, 2.4 Alarm noise policy (+17 more)

### Community 75 - "Feature 3: Device Health & Maintenance Log — Implementation Plan"
Cohesion: 0.17
Nodes (11): Backend — Create, Backend — Modify, Feature 3: Device Health & Maintenance Log — Implementation Plan, File Map, Frontend — Modify, Post-Implementation Checklist, Task 1: Migration — maintenance_logs table, Task 2: MaintenanceLog model, schemas, and health status tests (+3 more)

### Community 76 - "Feature 4: Regulatory Report Generator — Implementation Plan"
Cohesion: 0.17
Nodes (11): Backend — Create, Backend — Modify, Feature 4: Regulatory Report Generator — Implementation Plan, File Map, Frontend — Create, Frontend — Modify, Post-Implementation Checklist, Task 1: Backend schemas + helper functions with tests (+3 more)

### Community 77 - "generate_device_secret"
Cohesion: 0.08
Nodes (22): alerts, ANOMALY_LABELS, applyFilters(), changePage(), closeModal(), FIELD_LABELS, filters, { getAlerts, getSites, followupAlert, resolveAlert } (+14 more)

### Community 78 - "SPARING API Documentation"
Cohesion: 0.17
Nodes (12): Best Practices, Error Responses, Examples, Idempotency, JavaScript/Node.js Example, Overview, Python Client Example, Rate Limiting (+4 more)

### Community 79 - "ingest_state"
Cohesion: 0.09
Nodes (15): alertRules, editForm, editingRuleId, loadingRules, PARAM_LABELS, passwordError, passwordForm, profileForm (+7 more)

### Community 80 - "Endpoints"
Cohesion: 0.20
Nodes (10): Data Retrieval, Endpoints, Get Latest Reading, Health Checks, Liveness Probe, Metrics & Statistics, Query Data, Readiness Probe (+2 more)

### Community 81 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 82 - "Admin Endpoints"
Cohesion: 0.22
Nodes (9): Admin Endpoints, Assign Viewer to Site (admin only), Delete User (admin only), List Users (admin only), List Viewer-Site Assignments (admin only), List Viewers (admin only), Register User (admin only), Unassign Viewer from Site (admin only) (+1 more)

### Community 83 - "Deployment Options"
Cohesion: 0.22
Nodes (9): 1.1 Production Docker Compose, 1.2 Deploy, 1.3 View Logs, 3.1 Create Virtual Environment, 3.2 Create Systemd Service, 3.3 Enable and Start Service, Deployment Options, Option 1: Docker Compose (Recommended for Small-Medium Scale) (+1 more)

### Community 84 - "Production Deployment Guide"
Cohesion: 0.22
Nodes (9): Getting Help, Prerequisites, Production Checklist, Production Deployment Guide, Regular Maintenance Tasks, Software Requirements, Support & Maintenance, System Requirements (+1 more)

### Community 85 - "TTLCache"
Cohesion: 0.08
Nodes (21): last_seen(), AsyncSession, datetime, Get last data timestamp for a site., Get aggregated metrics (avg, min, max) for a site.     Now includes: pH, TSS, C, site_metrics(), cache_key(), cached() (+13 more)

### Community 86 - "Alert"
Cohesion: 0.42
Nodes (10): assign_viewer(), create_user(), delete_user(), list_users(), list_viewer_sites(), list_viewers(), AsyncSession, unassign_viewer() (+2 more)

### Community 87 - "SPARING Frontend - Implementation Guide"
Cohesion: 0.25
Nodes (8): 📚 Additional Resources, API Endpoints Mapped, 🔌 API Integration, Common Issues, 📋 Overview, SPARING Frontend - Implementation Guide, 🆘 Troubleshooting, useApi Composable

### Community 88 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 89 - "UI Re-theme — "Teal/Ink Compliance" Design Language"
Cohesion: 0.33
Nodes (5): Design tokens, Goal, Implementation approach, Out of scope, UI Re-theme — "Teal/Ink Compliance" Design Language

### Community 90 - "jspdf"
Cohesion: 0.67
Nodes (3): exportPdf(), statusLabel(), trendLabel()

### Community 91 - "Sites Management"
Cohesion: 0.33
Nodes (6): Create Site (admin/operator only), Delete Site (admin only), Get Site by ID, List Sites, Sites Management, Update Site (admin/operator only)

### Community 92 - "Monitoring & Maintenance"
Cohesion: 0.33
Nodes (6): 1. Prometheus Metrics, 2. Log Aggregation, 3. Database Backups, 4. Health Monitoring, 5. Performance Monitoring, Monitoring & Maintenance

### Community 93 - "Troubleshooting"
Cohesion: 0.33
Nodes (6): API Won't Start, Database Connection Issues, High Memory Usage, Rate Limit Issues, Slow Queries, Troubleshooting

### Community 94 - "🎯 Best Practices Applied"
Cohesion: 0.33
Nodes (6): 1. Single Responsibility, 2. DRY (Don't Repeat Yourself), 3. Composition Over Inheritance, 4. Prop Validation, 5. Error Handling, 🎯 Best Practices Applied

### Community 95 - "list_data"
Cohesion: 0.13
Nodes (14): File Structure, Logger Monitoring — Backend Implementation Plan (Plan 1 of 3), Self-Review Notes, Task 0: Baseline — suite green, Task 10: Full suite, deploy, production verification, Task 1: Extract the device-JWT verifier (TDD), Task 2: Logger tables (models + migration 0009), Task 3: `op_status` column + sentinel handling at ingest (TDD) (+6 more)

### Community 96 - "Authentication"
Cohesion: 0.40
Nodes (5): Authentication, Login, Logout, Refresh Token, Using Authentication

### Community 97 - "Devices Management"
Cohesion: 0.40
Nodes (5): Create Device (admin/operator only), Delete Device (admin only), Devices Management, List Devices, Update Device (admin/operator only)

### Community 98 - "Environment Configuration"
Cohesion: 0.40
Nodes (5): 1. Copy Production Environment Template, 2. Configure Critical Settings, 3. Optional Settings, Environment Configuration, Generate Strong JWT Secret

### Community 99 - "📊 Dashboard Implementation"
Cohesion: 0.40
Nodes (5): Charts Integration, 📊 Dashboard Implementation, Data Loading Sequence, Real-Time Monitoring, Sensor Cards

### Community 100 - "🛠️ Helper Functions"
Cohesion: 0.40
Nodes (5): Data Processing, Date & Time, 🛠️ Helper Functions, Sensor Utilities, Status Helpers

### Community 101 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 102 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 103 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 104 - "Database Setup"
Cohesion: 0.50
Nodes (4): 1. Create Production Database, 2. Run Migrations, 3. Seed Initial Data (Optional), Database Setup

### Community 105 - "Option 2: Kubernetes"
Cohesion: 0.09
Nodes (48): availability(), data_gaps(), _parse_range(), AsyncSession, datetime, Advanced analytics endpoints (audit Priority 2): data-gap detection and debit→vo, #18: full-range statistics (median/P95/P99/std) per parameter, computed over, Reconstruct uptime% from logger_events transitions. Returns None when there (+40 more)

### Community 106 - "Security Checklist"
Cohesion: 0.50
Nodes (4): Application Security, Before Deployment, Database Security, Security Checklist

### Community 107 - "Scaling Considerations"
Cohesion: 0.50
Nodes (4): Caching, Horizontal Scaling, Scaling Considerations, Vertical Scaling

### Community 108 - "Reverse Proxy Setup (Nginx)"
Cohesion: 0.50
Nodes (4): Enable Site, Nginx Configuration, Reverse Proxy Setup (Nginx), SSL Certificate (Let's Encrypt)

### Community 109 - "🎨 Reusable Components"
Cohesion: 0.50
Nodes (4): 1. SensorCard, 2. StatusBadge, 3. DataTable, 🎨 Reusable Components

### Community 110 - "🔐 Authentication Flow"
Cohesion: 0.50
Nodes (4): 🔐 Authentication Flow, Login Process, Logout Process, Token Refresh

### Community 111 - "🚀 Deployment"
Cohesion: 0.50
Nodes (4): Build for Production, 🚀 Deployment, Environment Configuration, Serve Static Files

### Community 112 - "📜 History Page Implementation"
Cohesion: 0.50
Nodes (4): CSV Export, Filter System, 📜 History Page Implementation, Pagination

### Community 117 - "SensorHealthOut"
Cohesion: 0.12
Nodes (35): add_maintenance_log(), create_device(), delete_device(), delete_maintenance_log(), _device_data_filter(), get_device(), get_device_health(), list_devices() (+27 more)

### Community 118 - "Data Ingestion"
Cohesion: 0.67
Nodes (3): Bulk Ingest, Data Ingestion, Ingest Single Reading

### Community 119 - "Updating the Application"
Cohesion: 0.67
Nodes (3): Rollback, Updating the Application, Zero-Downtime Deployment

### Community 120 - "🏗️ Architecture"
Cohesion: 0.17
Nodes (6): Environment Variables (.env.production), Prerequisites, Quick Start, Security Checklist, SPARING Deployment Guide, Useful Commands

### Community 121 - "📱 Responsive Design"
Cohesion: 0.67
Nodes (3): Breakpoint Strategy, 📱 Responsive Design, Sidebar Behavior

### Community 122 - "🧪 Testing Strategy"
Cohesion: 0.67
Nodes (3): Browser Compatibility, Manual Testing Checklist, 🧪 Testing Strategy

### Community 123 - "📝 Code Style Guide"
Cohesion: 0.67
Nodes (3): 📝 Code Style Guide, File Organization, Naming Conventions

### Community 124 - "🔄 Component Communication"
Cohesion: 0.67
Nodes (3): 🔄 Component Communication, Props Down, Events Up, Shared State (Composables)

### Community 125 - "🔧 Device Management"
Cohesion: 0.67
Nodes (3): CRUD Operations, 🔧 Device Management, Device Status Detection

### Community 126 - "🔮 Future Enhancements"
Cohesion: 0.67
Nodes (3): 🔮 Future Enhancements, Planned Features, Technical Improvements

### Community 130 - "File Structure"
Cohesion: 0.14
Nodes (13): File Structure, Self-Review Notes, Task 0: Baseline — build is green, Task 1: API layer — new endpoints + note-aware resolve, Task 2: App shell v2 (sidebar, utility strip, page header, footer), Task 3: Add the `/alarms` route, Task 4: Alarm page + follow-up modal, Task 5: Sparkline component + Dashboard v2 (+5 more)

### Community 131 - "🔌 API Integration"
Cohesion: 0.36
Nodes (13): _auth_headers(), _make_alert(), test_alert_count_scoped_by_site_uid(), test_alert_out_includes_followup_fields(), test_alerts_bare_list_without_page_param(), test_alerts_filters(), test_alerts_paginated_wrapper_with_page_param(), test_followup_sets_acknowledged_note_optional() (+5 more)

### Community 132 - "File Structure"
Cohesion: 0.15
Nodes (12): File Structure, Logger Monitoring — Frontend Implementation Plan (Plan 3 of 3), Self-Review Notes, Task 0: Baseline — build is green, Task 1: API methods, Task 2: `/loggers` route + sidebar nav with down-count pill, Task 3: Event timeline component, Task 4: Loggers page — KPIs + per-site status table + timeline (+4 more)

### Community 133 - "File Structure"
Cohesion: 0.15
Nodes (12): File Structure, Logger Monitoring — Logger App Implementation Plan (Plan 2 of 3), Self-Review Notes, Task 0: Baseline — the app imports and runs dummy mode, Task 1: Config — derive logger URLs + heartbeat interval, Task 2: `telemetry.py` — pure status + resource readers (TDD), Task 3: Event log in SQLite + idempotent serialization (TDD), Task 4: Crash-vs-clean-restart marker (TDD) (+4 more)

### Community 134 - "SPARING API Documentation"
Cohesion: 0.17
Nodes (12): Best Practices, Error Responses, Examples, Idempotency, JavaScript/Node.js Example, Overview, Python Client Example, Rate Limiting (+4 more)

### Community 135 - "dedup_sensor_data.py"
Cohesion: 0.67
Nodes (3): main(), Remove duplicate (site_id, ts) rows from sensor_data before the unique constrain, _run()

### Community 136 - "onSiteChange"
Cohesion: 0.22
Nodes (11): loadAlertRules(), loadChartData(), loadDevices(), loadLatestData(), loadSensorHealth(), loadSitesStatus(), loadStats(), manualRefresh() (+3 more)

### Community 137 - "package.json"
Cohesion: 0.20
Nodes (9): description, name, scripts, build, dev, preview, test, type (+1 more)

### Community 139 - "🏗️ Architecture"
Cohesion: 0.67
Nodes (3): 🏗️ Architecture, Component-Based Design, Data Flow

### Community 141 - "UtilityStrip.vue"
Cohesion: 0.25
Nodes (5): BULAN, clock, HARI, { healthCheck }, serverOk

### Community 142 - "Option 1: Docker Compose (Recommended for Small-Medium Scale)"
Cohesion: 0.58
Nodes (8): _auth_headers(), _make_site(), _row(), test_aggregation_requires_date_from(), test_daily_aggregation_single_bucket(), test_data_returns_quality_flag(), test_hourly_aggregation_excludes_anomaly(), test_viewer_without_site_uid_is_confined_to_assigned_sites()

### Community 143 - "Login.vue"
Cohesion: 0.29
Nodes (5): errorMessage, form, isLoading, { login }, showPassword

### Community 145 - "Sparkline.vue"
Cohesion: 0.33
Nodes (4): bounds, d, props, threshLine

### Community 146 - "Authentication"
Cohesion: 0.40
Nodes (5): Authentication, Login, Logout, Refresh Token, Using Authentication

### Community 147 - "🛠️ Helper Functions"
Cohesion: 0.29
Nodes (6): HTTPAuthorizationCredentials, get_current_token(), get_current_user(), get_viewer_site_uids(), AsyncSession, decode_jwt()

### Community 148 - "🐛 Troubleshooting"
Cohesion: 0.47
Nodes (10): _auth_headers(), _evt(), _make_site(), _row(), test_analytics_forbidden_for_unassigned_viewer(), test_availability_from_events(), test_gaps_endpoint_detects_hole(), test_statistics_endpoint_full_range() (+2 more)

### Community 149 - "load"
Cohesion: 0.17
Nodes (12): Architecture Notes, Documentation, Features, Key Endpoints, Production Deployment, Quickstart (Docker), Scaling Considerations, Security Features (+4 more)

### Community 150 - "xlsx"
Cohesion: 0.50
Nodes (4): xlsx, exportToExcel(), exportExcel(), xlsx

### Community 151 - "🔧 Admin Tasks"
Cohesion: 0.36
Nodes (5): LoginIn, BaseModel, RegisterIn, TokenOut, UserOut

### Community 152 - "📈 Fitur Analytics"
Cohesion: 0.27
Nodes (6): hash_password(), _make_user(), test_login_success_returns_tokens(), test_login_wrong_password_401(), test_me_returns_user_with_token(), main()

### Community 164 - "📦 Components"
Cohesion: 0.31
Nodes (8): DeclarativeBase, Base, ApiKey, AuthTokenBlacklist, IngestLog, SensorHealth, SensorType, ViewerSite

### Community 165 - "🚀 Setup Instructions"
Cohesion: 0.22
Nodes (9): Centralized Logging, Current Logging Implementation, Log Levels, Log Retention, Log Sources, Logging Strategy, Option 1: ELK Stack (Elasticsearch, Logstash, Kibana), Option 2: Loki + Grafana (+1 more)

### Community 166 - "Option 2: Kubernetes"
Cohesion: 0.50
Nodes (4): 2.1 Create Deployment, 2.2 Create Service, 2.3 Deploy to Kubernetes, Option 2: Kubernetes

### Community 167 - "🐛 Troubleshooting"
Cohesion: 0.25
Nodes (8): Application Metrics, Built-in Prometheus Metrics, Business Metrics, Custom Application Metrics, Infrastructure Metrics, Key Metrics to Monitor, Metrics & Monitoring, Prometheus Setup

### Community 168 - "📈 Data Flow"
Cohesion: 0.29
Nodes (7): 1. High Response Time, 2. Memory Leaks, 3. Database Connection Pool Exhausted, 4. High CPU Usage, Common Issues & Solutions, Debug Logging, Troubleshooting Guide

### Community 169 - "🔐 Authentication"
Cohesion: 0.40
Nodes (5): Date & Time, 🛠️ Helper Functions, Number & Data Formatting, Sensor Utilities, Status Utilities

### Community 170 - "🎨 Design System"
Cohesion: 0.40
Nodes (5): Chart tidak muncul, Export CSV tidak bekerja, "No data" di Dashboard, 🐛 Troubleshooting, User tidak bisa login

### Community 171 - "refreshAll"
Cohesion: 0.40
Nodes (5): loadActiveLoggerAlarms(), loadEvents(), loadEvents24h(), loadStatuses(), refreshAll()

### Community 172 - "Development"
Cohesion: 0.50
Nodes (4): Database Migrations, Development, Project Structure, Running Tests

### Community 173 - "🔧 Admin Tasks"
Cohesion: 0.50
Nodes (4): 🔧 Admin Tasks, Tambah Lokasi Baru, Tambah Perangkat Baru, Tambah User Baru

### Community 174 - "📈 Fitur Analytics"
Cohesion: 0.50
Nodes (4): Charts Tersedia, Export, Filter Data, 📈 Fitur Analytics

## Knowledge Gaps
- **989 isolated node(s):** `name`, `version`, `description`, `type`, `dev` (+984 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Site` connect `Alert Engine & Rules` to `Anomaly Detection Engine`, `🔌 API Integration`, `📦 Components`, `Sites & Data API`, `Report Generation`, `Option 2: Kubernetes`, `Metrics & Caching`, `Option 1: Docker Compose (Recommended for Small-Medium Scale)`, `Devices & Maintenance API`, `🐛 Troubleshooting`, `SensorHealthOut`, `Alert`, `Header Component`, `TTLCache`, `📈 Fitur Analytics`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `SensorData` connect `Metrics & Caching` to `Anomaly Detection Engine`, `📦 Components`, `Report Generation`, `Option 2: Kubernetes`, `Option 1: Docker Compose (Recommended for Small-Medium Scale)`, `Devices & Maintenance API`, `🐛 Troubleshooting`, `SensorHealthOut`, `Header Component`, `📈 Fitur Analytics`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `User` connect `Alert` to `Database Models`, `🔌 API Integration`, `Alert Engine & Rules`, `Sites & Data API`, `📦 Components`, `Option 1: Docker Compose (Recommended for Small-Medium Scale)`, `🛠️ Helper Functions`, `🐛 Troubleshooting`, `SensorHealthOut`, `Header Component`, `📈 Fitur Analytics`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `Site` (e.g. with `assign_viewer()` and `list_viewer_sites()`) actually correct?**
  _`Site` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `User` (e.g. with `assign_viewer()` and `create_user()`) actually correct?**
  _`User` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `Alert` (e.g. with `acknowledge_alert()` and `followup_alert()`) actually correct?**
  _`Alert` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `SensorData` (e.g. with `statistics()` and `last_record()`) actually correct?**
  _`SensorData` has 21 INFERRED edges - model-reasoned connections that need verification._