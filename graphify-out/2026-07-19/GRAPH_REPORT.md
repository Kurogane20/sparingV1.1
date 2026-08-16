# Graph Report - .  (2026-07-18)

## Corpus Check
- 121 files · ~86,844 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 936 nodes · 1404 edges · 61 communities (59 shown, 2 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 249 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

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

## God Nodes (most connected - your core abstractions)
1. `Site` - 34 edges
2. `User` - 24 edges
3. `generate_report()` - 18 edges
4. `Base` - 15 edges
5. `compute_health_status()` - 14 edges
6. `APIError` - 13 edges
7. `_series()` - 13 edges
8. `main()` - 12 edges
9. `SensorDevice` - 12 edges
10. `_num()` - 11 edges

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

## Communities (61 total, 2 thin omitted)

### Community 0 - "Anomaly Detection Engine"
Cohesion: 0.07
Nodes (56): SensorData, Alternating small noise around 7.0 — a realistic stable pH series., _series(), _stable(), test_drift_empty_windows_not_flagged(), test_drift_stable_not_flagged(), test_drift_sustained_shift_flagged(), test_drift_tiny_baseline_floor_prevents_false_positive() (+48 more)

### Community 1 - "Database Models"
Cohesion: 0.07
Nodes (49): DeclarativeBase, HTTPAuthorizationCredentials, get_current_token(), get_current_user(), get_viewer_site_uids(), AsyncSession, assign_viewer(), create_user() (+41 more)

### Community 2 - "Dashboard Page"
Cohesion: 0.05
Nodes (38): chartData, chartOptions, chartPeriod, chartSeries, colors, complianceParams, currentSite, debitTempOptions (+30 more)

### Community 3 - "Devices Page"
Cohesion: 0.05
Nodes (30): activeDevicesCount, addingLog, canManageDevices, { confirm }, deviceColumns, deviceForm, deviceHealth, devices (+22 more)

### Community 4 - "Alert Engine & Rules"
Cohesion: 0.10
Nodes (32): create_alert_rule(), delete_alert_rule(), _get_site_by_uid(), list_alert_rules(), AsyncSession, update_alert_rule(), AlertRule, AlertCountOut (+24 more)

### Community 5 - "Sites & Data API"
Cohesion: 0.10
Nodes (31): last_record(), list_data(), AsyncSession, datetime, create_site(), delete_site(), get_sensor_health(), get_site() (+23 more)

### Community 6 - "Report Generation"
Cohesion: 0.10
Nodes (32): date, _build_violation_filter(), generate_report(), AsyncSession, Build SQLAlchemy WHERE clause for values outside baku mutu limits., BakuMutuOut, DailySummaryOut, ParameterReportOut (+24 more)

### Community 7 - "Reports Page"
Cohesion: 0.06
Nodes (26): xlsx, doGenerateReport(), exportExcel(), exportingPdf, exportPdf(), { filterSitesByUser }, form, getPeriodDates() (+18 more)

### Community 8 - "Sites Page"
Cohesion: 0.07
Nodes (28): addRule(), alertRules, AVAILABLE_FIELDS, closeModal(), { confirm }, deleteSiteHandler(), deviceKey, editingSite (+20 more)

### Community 9 - "Ingestion & Time Utils"
Cohesion: 0.09
Nodes (23): ingest_bulk(), ingest_state(), AsyncSession, Request, _validate_ranges(), JsonFormatter, BaseHTTPMiddleware, Request (+15 more)

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
Cohesion: 0.09
Nodes (15): app, router, errorMessage, features, form, isLoading, { login }, showPassword (+7 more)

### Community 16 - "History Page"
Cohesion: 0.11
Nodes (19): applyFilters(), availableFields, dateDifferenceInDays, filters, { filterSitesByUser }, { getData, getSites }, getDefaultDateFrom(), getDefaultDateTo() (+11 more)

### Community 17 - "Site Map & Sidebar"
Cohesion: 0.13
Nodes (19): leaflet/dist/leaflet.css, allMenuItems, isActive(), { logout, user }, menuItems, route, addMarkers(), buildPopup() (+11 more)

### Community 18 - "Devices & Maintenance API"
Cohesion: 0.22
Nodes (20): add_maintenance_log(), create_device(), delete_device(), delete_maintenance_log(), get_device(), get_device_health(), list_devices(), list_maintenance_logs() (+12 more)

### Community 19 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (20): apexcharts, axios, chart.js, html2canvas, jspdf, dependencies, apexcharts, axios (+12 more)

### Community 20 - "Alert Notifications UI"
Cohesion: 0.13
Nodes (13): activeCount, alerts, ANOMALY_LABELS, dropdownRef, fetchAlerts(), { getAlertCount, getAlerts, acknowledgeAlert }, getAlertTitle(), getFieldLabel() (+5 more)

### Community 21 - "Device Ingest Endpoint"
Cohesion: 0.20
Nodes (15): get_key(), _global_secret(), _num(), post_data(), AsyncSession, Request, Extract a numeric field by any of `keys` (first non-None wins).      Returns (, test_num_alias_order_first_present_wins() (+7 more)

### Community 22 - "Header Component"
Cohesion: 0.12
Nodes (12): currentDate, dropdownOpen, dropdownRef, { healthCheck }, pageTitle, pageTitles, route, systemStatus (+4 more)

### Community 23 - "Device Health Status"
Cohesion: 0.29
Nodes (13): _ago(), datetime, test_health_boundary_offline(), test_health_boundary_online(), test_health_boundary_warning(), test_health_offline(), test_health_online_recent(), test_health_online_within_a_burst_cycle() (+5 more)

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
Cohesion: 0.42
Nodes (8): _make_site(), post_data fires trigger_alerts/detect_realtime via asyncio.create_task;     they, _silence_background_tasks(), test_post_data_drops_impossible_value_keeps_batch(), test_post_data_invalid_signature_rejected(), test_post_data_stores_valid_batch(), test_post_data_unknown_site_rejected(), _token()

### Community 31 - "Package Manifest"
Cohesion: 0.22
Nodes (8): description, name, scripts, build, dev, preview, type, version

### Community 32 - "Alembic Env"
Cohesion: 0.29
Nodes (7): Connection, do_run_migrations(), Run migrations in 'offline' mode., Configure context and run migrations given a sync Connection., Run migrations in 'online' mode with an **async** engine., run_migrations_offline(), run_migrations_online()

### Community 33 - "Auth Schemas & Routes"
Cohesion: 0.36
Nodes (5): LoginIn, BaseModel, RegisterIn, TokenOut, UserOut

### Community 34 - "Devices Page Actions"
Cohesion: 0.25
Nodes (8): closeModal(), deleteDeviceHandler(), loadDevices(), loadHealthForDevices(), loadSites(), loadSiteStats(), saveDevice(), toggleDeviceStatus()

### Community 35 - "App Config & Settings"
Cohesion: 0.29
Nodes (4): BaseSettings, Refuse to start in production with a default/empty JWT secret.          A defa, Parse cors_origins_str into a list of origins., Settings

### Community 36 - "Auth API Tests"
Cohesion: 0.43
Nodes (4): _make_user(), test_login_success_returns_tokens(), test_login_wrong_password_401(), test_me_returns_user_with_token()

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

## Knowledge Gaps
- **242 isolated node(s):** `name`, `version`, `description`, `type`, `dev` (+237 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Site` connect `Sites & Data API` to `Anomaly Detection Engine`, `Database Models`, `Alert Engine & Rules`, `Report Generation`, `Ingestion & Time Utils`, `Metrics & Caching`, `Devices & Maintenance API`, `Device Ingest Endpoint`, `Getdata API Tests`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Why does `detect_drift_all_sites()` connect `Anomaly Detection Engine` to `App Bootstrap & Scheduler`, `Sites & Data API`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `generate_report()` connect `Report Generation` to `Anomaly Detection Engine`, `Alert Engine & Rules`, `Sites & Data API`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `Site` (e.g. with `assign_viewer()` and `list_viewer_sites()`) actually correct?**
  _`Site` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `User` (e.g. with `assign_viewer()` and `create_user()`) actually correct?**
  _`User` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `generate_report()` (e.g. with `AlertRule` and `SensorData`) actually correct?**
  _`generate_report()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `Base` (e.g. with `Alert` and `AlertRule`) actually correct?**
  _`Base` has 13 INFERRED edges - model-reasoned connections that need verification._