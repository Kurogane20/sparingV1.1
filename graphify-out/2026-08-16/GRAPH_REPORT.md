# Graph Report - sparingV1.1  (2026-07-19)

## Corpus Check
- 133 files · ~104,368 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1669 nodes · 2119 edges · 130 communities (122 shown, 8 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 253 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `73b4d309`
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
- Base
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

## God Nodes (most connected - your core abstractions)
1. `Site` - 35 edges
2. `User` - 25 edges
3. `SPARING Frontend - Implementation Guide` - 19 edges
4. `generate_report()` - 18 edges
5. `Feature 1: Alert & Notification System — Implementation Plan` - 17 edges
6. `SPARING - Industrial Environmental Monitoring System` - 17 edges
7. `Base` - 15 edges
8. `Sensor Data Quality & Anomaly Detection Implementation Plan` - 15 edges
9. `compute_health_status()` - 14 edges
10. `Production Deployment Guide` - 14 edges

## Surprising Connections (you probably didn't know these)
- `send_alert_emails()` --references--> `FIELD_LABELS`  [EXTRACTED]
  sparing_api/app/utils/email.py → sparing_front/resources/js/Components/AlertDropdown.vue
- `assign_viewer()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `unassign_viewer()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `list_viewer_sites()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/admin.py → sparing_api/app/models/models.py
- `_build_alert_out()` --indirect_call--> `Site`  [INFERRED]
  sparing_api/app/api/routers/alerts.py → sparing_api/app/models/models.py

## Import Cycles
- 1-file cycle: `sparing_api/app/api/routers/__init__.py -> sparing_api/app/api/routers/__init__.py`
- 1-file cycle: `sparing_front/resources/js/app.js -> sparing_front/resources/js/app.js`

## Communities (130 total, 8 thin omitted)

### Community 0 - "Anomaly Detection Engine"
Cohesion: 0.07
Nodes (56): SensorData, Alternating small noise around 7.0 — a realistic stable pH series., _series(), _stable(), test_drift_empty_windows_not_flagged(), test_drift_stable_not_flagged(), test_drift_sustained_shift_flagged(), test_drift_tiny_baseline_floor_prevents_false_positive() (+48 more)

### Community 1 - "Database Models"
Cohesion: 0.06
Nodes (49): HTTPAuthorizationCredentials, get_current_token(), get_current_user(), get_viewer_site_uids(), AsyncSession, assign_viewer(), create_user(), delete_user() (+41 more)

### Community 2 - "Dashboard Page"
Cohesion: 0.05
Nodes (38): chartData, chartOptions, chartPeriod, chartSeries, colors, complianceParams, currentSite, debitTempOptions (+30 more)

### Community 3 - "Devices Page"
Cohesion: 0.05
Nodes (30): activeDevicesCount, addingLog, canManageDevices, { confirm }, deviceColumns, deviceForm, deviceHealth, devices (+22 more)

### Community 4 - "Alert Engine & Rules"
Cohesion: 0.12
Nodes (26): create_alert_rule(), delete_alert_rule(), _get_site_by_uid(), list_alert_rules(), AsyncSession, update_alert_rule(), AlertRule, AlertCountOut (+18 more)

### Community 5 - "Sites & Data API"
Cohesion: 0.28
Nodes (15): create_site(), delete_site(), get_sensor_health(), get_site(), get_site_device_key(), list_sites(), AsyncSession, rotate_site_secret() (+7 more)

### Community 6 - "Report Generation"
Cohesion: 0.10
Nodes (32): date, _build_violation_filter(), generate_report(), AsyncSession, Build SQLAlchemy WHERE clause for values outside baku mutu limits., BakuMutuOut, DailySummaryOut, ParameterReportOut (+24 more)

### Community 7 - "Reports Page"
Cohesion: 0.07
Nodes (20): doGenerateReport(), exportingPdf, { filterSitesByUser }, form, getPeriodDates(), { getSites, generateReport: apiGenerateReport }, loading, MONTHS (+12 more)

### Community 8 - "Sites Page"
Cohesion: 0.07
Nodes (28): addRule(), alertRules, AVAILABLE_FIELDS, closeModal(), { confirm }, deleteSiteHandler(), deviceKey, editingSite (+20 more)

### Community 9 - "Ingestion & Time Utils"
Cohesion: 0.08
Nodes (35): JsonFormatter, BaseHTTPMiddleware, Request, RateLimitMiddleware, _ago(), datetime, test_health_boundary_offline(), test_health_boundary_online() (+27 more)

### Community 10 - "App Bootstrap & Scheduler"
Cohesion: 0.08
Nodes (20): get_db(), init_models(), api_error_handler(), _check_offline_devices(), _cleanup_expired_tokens(), _detect_anomaly_drift(), general_exception_handler(), healthz() (+12 more)

### Community 11 - "Metrics & Caching"
Cohesion: 0.08
Nodes (21): last_seen(), AsyncSession, datetime, Get last data timestamp for a site., Get aggregated metrics (avg, min, max) for a site.     Now includes: pH, TSS, C, site_metrics(), cache_key(), cached() (+13 more)

### Community 12 - "API Exceptions"
Cohesion: 0.11
Nodes (19): APIError, AuthenticationError, ConflictError, ForbiddenError, InternalServerError, NotFoundError, Any, Exception (+11 more)

### Community 13 - "Analytics Page"
Cohesion: 0.07
Nodes (18): @/Utils/analysis.js, barOptions, barSeries, chartData, colors, complianceParams, exporting, filters (+10 more)

### Community 14 - "Users Page"
Cohesion: 0.09
Nodes (22): allSites, closeModal(), closeSitesModal(), { confirm }, deleteUser(), editingUser, { getUsers, registerUser, updateUser: apiUpdateUser, deleteUser: apiDeleteUser, getSites, updateUserSites, getViewerSites }, { isAdmin, user: currentUser } (+14 more)

### Community 15 - "App Router & Entry"
Cohesion: 0.05
Nodes (34): app, router, errorMessage, features, form, isLoading, { login }, showPassword (+26 more)

### Community 16 - "History Page"
Cohesion: 0.05
Nodes (37): Environment Variables (.env.production), Prerequisites, Quick Start, Security Checklist, SPARING Deployment Guide, Useful Commands, Backend, Backend (`sparing_api/.env`) (+29 more)

### Community 17 - "Site Map & Sidebar"
Cohesion: 0.13
Nodes (19): leaflet/dist/leaflet.css, allMenuItems, isActive(), { logout, user }, menuItems, route, addMarkers(), buildPopup() (+11 more)

### Community 18 - "Devices & Maintenance API"
Cohesion: 0.22
Nodes (20): add_maintenance_log(), create_device(), delete_device(), delete_maintenance_log(), get_device(), get_device_health(), list_devices(), list_maintenance_logs() (+12 more)

### Community 19 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (20): apexcharts, axios, chart.js, html2canvas, dependencies, apexcharts, axios, chart.js (+12 more)

### Community 20 - "Alert Notifications UI"
Cohesion: 0.13
Nodes (13): activeCount, alerts, ANOMALY_LABELS, dropdownRef, fetchAlerts(), { getAlertCount, getAlerts, acknowledgeAlert }, getAlertTitle(), getFieldLabel() (+5 more)

### Community 21 - "Device Ingest Endpoint"
Cohesion: 0.31
Nodes (10): _num(), Extract a numeric field by any of `keys` (first non-None wins).      Returns (, test_num_alias_order_first_present_wins(), test_num_below_lower_bound_dropped(), test_num_missing_is_none_not_dropped(), test_num_no_bounds_passes_any_number(), test_num_non_numeric_dropped(), test_num_out_of_upper_bound_dropped() (+2 more)

### Community 22 - "Header Component"
Cohesion: 0.12
Nodes (12): currentDate, dropdownOpen, dropdownRef, { healthCheck }, pageTitle, pageTitles, route, systemStatus (+4 more)

### Community 23 - "Device Health Status"
Cohesion: 0.05
Nodes (35): Authentication, Best Practices, Error Responses, Examples, Idempotency, JavaScript/Node.js Example, Login, Logout (+27 more)

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
Cohesion: 0.10
Nodes (19): autoprefixer, postcss, description, devDependencies, autoprefixer, postcss, tailwindcss, vite (+11 more)

### Community 29 - "Auth & API Composables"
Cohesion: 0.31
Nodes (8): apiClient, useApi(), decodeJWT(), NOTE: This requires backend to allow viewer/operator access to /admin/viewer-sit, token, useAuth(), user, logger

### Community 30 - "Getdata API Tests"
Cohesion: 0.05
Nodes (37): 1. High Response Time, 2. Memory Leaks, 3. Database Connection Pool Exhausted, 4. High CPU Usage, Alert Channels, Alert Rules, Alerting, Alertmanager Configuration (+29 more)

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
Nodes (8): closeModal(), deleteDeviceHandler(), loadDevices(), loadHealthForDevices(), loadSites(), loadSiteStats(), saveDevice(), toggleDeviceStatus()

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
Cohesion: 0.50
Nodes (4): getHealthStatus(), healthDotClass(), healthLabel(), healthStatusClass()

### Community 54 - "Log Type Helpers"
Cohesion: 0.67
Nodes (3): getLogTypeColor(), getLogTypeLabel(), LOG_TYPES

### Community 55 - "Maintenance Log UI"
Cohesion: 0.67
Nodes (3): loadMaintenanceLogs(), openMaintenanceModal(), submitLog()

### Community 61 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 62 - "🚀 SPARING - Quick Reference Card"
Cohesion: 0.08
Nodes (26): 🔧 Admin Tasks, 🔄 Auto-Refresh, 📊 Baku Mutu (Standar Compliance), Chart tidak muncul, Charts Tersedia, 🔑 Default Credentials, Export, Export CSV tidak bekerja (+18 more)

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
Cohesion: 0.21
Nodes (11): get_key(), _global_secret(), post_data(), AsyncSession, Request, Check data against active AlertRules. Creates its own DB session — safe for asyn, trigger_alerts(), _get_recipient_emails() (+3 more)

### Community 75 - "Feature 3: Device Health & Maintenance Log — Implementation Plan"
Cohesion: 0.17
Nodes (11): Backend — Create, Backend — Modify, Feature 3: Device Health & Maintenance Log — Implementation Plan, File Map, Frontend — Modify, Post-Implementation Checklist, Task 1: Migration — maintenance_logs table, Task 2: MaintenanceLog model, schemas, and health status tests (+3 more)

### Community 76 - "Feature 4: Regulatory Report Generator — Implementation Plan"
Cohesion: 0.17
Nodes (11): Backend — Create, Backend — Modify, Feature 4: Regulatory Report Generator — Implementation Plan, File Map, Frontend — Create, Frontend — Modify, Post-Implementation Checklist, Task 1: Backend schemas + helper functions with tests (+3 more)

### Community 77 - "generate_device_secret"
Cohesion: 0.24
Nodes (10): test_generate_device_secret_hex(), test_generate_device_secret_length(), test_generate_device_secret_unique(), test_mask_secret_empty(), test_mask_secret_normal(), test_mask_secret_short(), generate_device_secret(), mask_secret() (+2 more)

### Community 78 - "SPARING API Documentation"
Cohesion: 0.17
Nodes (12): Best Practices, Error Responses, Examples, Idempotency, JavaScript/Node.js Example, Overview, Python Client Example, Rate Limiting (+4 more)

### Community 79 - "ingest_state"
Cohesion: 0.33
Nodes (9): ingest_bulk(), ingest_state(), AsyncSession, Request, _validate_ranges(), DataOut, IngestBulkIn, IngestStateIn (+1 more)

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

### Community 85 - "Base"
Cohesion: 0.36
Nodes (6): DeclarativeBase, Base, ApiKey, IngestLog, SensorHealth, SensorType

### Community 86 - "Alert"
Cohesion: 0.54
Nodes (7): acknowledge_alert(), _build_alert_out(), get_alert_count(), list_alerts(), AsyncSession, resolve_alert(), Alert

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
Cohesion: 0.33
Nodes (6): jspdf, jspdf, exportReport(), exportPdf(), statusLabel(), trendLabel()

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
Cohesion: 0.60
Nodes (4): last_record(), list_data(), AsyncSession, datetime

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
Cohesion: 0.50
Nodes (4): 2.1 Create Deployment, 2.2 Create Service, 2.3 Deploy to Kubernetes, Option 2: Kubernetes

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

### Community 118 - "Data Ingestion"
Cohesion: 0.67
Nodes (3): Bulk Ingest, Data Ingestion, Ingest Single Reading

### Community 119 - "Updating the Application"
Cohesion: 0.67
Nodes (3): Rollback, Updating the Application, Zero-Downtime Deployment

### Community 120 - "🏗️ Architecture"
Cohesion: 0.67
Nodes (3): 🏗️ Architecture, Component-Based Design, Data Flow

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

## Knowledge Gaps
- **782 isolated node(s):** `name`, `version`, `description`, `type`, `dev` (+777 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Site` connect `Sites & Data API` to `Anomaly Detection Engine`, `Database Models`, `Alert Engine & Rules`, `Report Generation`, `Ingestion & Time Utils`, `post_data`, `Metrics & Caching`, `ingest_state`, `Devices & Maintenance API`, `Base`, `Alert`, `list_data`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `detect_drift_all_sites()` connect `Anomaly Detection Engine` to `App Bootstrap & Scheduler`, `Sites & Data API`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `APIError` connect `API Exceptions` to `App Bootstrap & Scheduler`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `Site` (e.g. with `assign_viewer()` and `list_viewer_sites()`) actually correct?**
  _`Site` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `User` (e.g. with `assign_viewer()` and `create_user()`) actually correct?**
  _`User` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `generate_report()` (e.g. with `AlertRule` and `SensorData`) actually correct?**
  _`generate_report()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `description` to the rest of the system?**
  _782 weakly-connected nodes found - possible documentation gaps or missing edges._