# SPARING Frontend - Project Structure

```
sparing_front/
│
├── 📄 package.json                      # Node dependencies and scripts
├── 📄 vite.config.js                    # Vite build configuration
├── 📄 tailwind.config.js                # Tailwind CSS configuration
├── 📄 postcss.config.js                 # PostCSS configuration
├── 📄 .env.example                      # Environment variables template
├── 📄 .gitignore                        # Git ignore rules
├── 📄 index.html                        # HTML entry point
│
├── 📚 Documentation/
│   ├── README.md                        # Main documentation
│   ├── API.md                           # API documentation (provided)
│   ├── IMPLEMENTATION_GUIDE.md          # Implementation details
│   ├── COMPONENT_API_REFERENCE.md       # Component API reference
│   └── PROJECT_STRUCTURE.md             # This file
│
├── 📁 resources/
│   │
│   ├── 📁 js/
│   │   │
│   │   ├── 📄 app.js                    # Application entry point
│   │   │
│   │   ├── 📁 Pages/                    # Route-level components
│   │   │   │
│   │   │   ├── 📁 Auth/
│   │   │   │   └── Login.vue            # Login page
│   │   │   │
│   │   │   ├── 📁 Dashboard/
│   │   │   │   └── Index.vue            # Main dashboard with real-time monitoring
│   │   │   │
│   │   │   ├── 📁 History/
│   │   │   │   └── Index.vue            # Historical data with filters & export
│   │   │   │
│   │   │   ├── 📁 Devices/
│   │   │   │   └── Index.vue            # Device management (CRUD)
│   │   │   │
│   │   │   └── 📁 Settings/
│   │   │       └── Index.vue            # User & system settings
│   │   │
│   │   ├── 📁 Components/               # Reusable UI components
│   │   │   ├── Sidebar.vue              # Navigation sidebar
│   │   │   ├── Header.vue               # Top header with status
│   │   │   ├── SensorCard.vue           # Sensor display card
│   │   │   ├── StatusBadge.vue          # Status indicator
│   │   │   └── DataTable.vue            # Paginated data table
│   │   │
│   │   ├── 📁 Layouts/                  # Page layouts
│   │   │   └── AppLayout.vue            # Main layout (sidebar + header)
│   │   │
│   │   ├── 📁 Composables/              # Shared business logic
│   │   │   ├── useApi.js                # API integration
│   │   │   └── useAuth.js               # Authentication state
│   │   │
│   │   └── 📁 Utils/                    # Helper functions
│   │       └── helpers.js               # Date, number, sensor utilities
│   │
│   └── 📁 css/
│       └── app.css                      # Global styles + Tailwind
│
├── 📁 public/                           # Static assets
│   ├── 📁 build/                        # Built assets (generated)
│   └── 📁 css/                          # Additional CSS (if needed)
│
└── 📁 node_modules/                     # Dependencies (generated)
```

## 📂 Directory Breakdown

### `/resources/js/Pages/`
**Purpose**: Route-level Vue components (one per URL)

| File | Route | Description |
|------|-------|-------------|
| `Auth/Login.vue` | `/login` | Login form with JWT authentication |
| `Dashboard/Index.vue` | `/dashboard` | Main dashboard with real-time sensor data |
| `History/Index.vue` | `/history` | Historical data with filters and CSV export |
| `Devices/Index.vue` | `/devices` | Device management (list, create, edit) |
| `Settings/Index.vue` | `/settings` | User profile and system settings |

---

### `/resources/js/Components/`
**Purpose**: Reusable UI components

| Component | Used In | Description |
|-----------|---------|-------------|
| `Sidebar.vue` | All pages | Navigation menu with logout |
| `Header.vue` | All pages | Page title, system status, user info |
| `SensorCard.vue` | Dashboard | Display sensor value with trend |
| `StatusBadge.vue` | Dashboard, Devices | Color-coded status indicator |
| `DataTable.vue` | Dashboard, History, Devices | Paginated table with custom cells |

---

### `/resources/js/Composables/`
**Purpose**: Shared reactive state and logic

| Composable | Purpose | Used In |
|------------|---------|---------|
| `useApi.js` | API calls with axios | All pages |
| `useAuth.js` | Authentication state | Login, Sidebar, Settings |

---

### `/resources/js/Utils/`
**Purpose**: Pure helper functions

| Function Category | Examples |
|-------------------|----------|
| Date & Time | `formatDate()`, `getRelativeTime()` |
| Sensor Utils | `getSensorName()`, `getSensorUnit()`, `getThresholdStatus()` |
| Number Format | `formatNumber()`, `downloadCSV()` |
| Status Utils | `getStatusClass()`, `getSensorStatus()` |

---

### `/resources/js/Layouts/`
**Purpose**: Page layout wrappers

| Layout | Used By | Contains |
|--------|---------|----------|
| `AppLayout.vue` | Dashboard, History, Devices, Settings | Sidebar + Header + Page Content |

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Action                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Vue Component (Page)     │
        │  - Login.vue                │
        │  - Dashboard/Index.vue      │
        │  - History/Index.vue        │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   Composable (useApi.js)    │
        │  - getSites()               │
        │  - getData()                │
        │  - getDevices()             │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   Axios HTTP Request        │
        │  - Bearer token injection   │
        │  - Error handling           │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    FastAPI Backend          │
        │  - /auth/login              │
        │  - /sites                   │
        │  - /data                    │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Response Processing      │
        │  - Update component state   │
        │  - Re-render UI             │
        └─────────────────────────────┘
```

---

## 🎯 Component Hierarchy

```
App (Inertia.js Root)
│
├── Login.vue (Public Route)
│
└── AppLayout.vue (Authenticated Routes)
    │
    ├── Sidebar.vue
    │   └── Menu Items (Dashboard, History, Devices, Settings)
    │
    ├── Header.vue
    │   ├── StatusBadge (System Status)
    │   └── User Profile Info
    │
    └── Page Content (Slot)
        │
        ├── Dashboard/Index.vue
        │   ├── SensorCard (×4)
        │   ├── Chart.js (Line Chart)
        │   ├── Chart.js (Donut Chart)
        │   └── DataTable (Devices)
        │       └── StatusBadge (per row)
        │
        ├── History/Index.vue
        │   ├── Filters (Site, Date, Fields)
        │   └── DataTable (with pagination)
        │
        ├── Devices/Index.vue
        │   ├── Site Selector
        │   ├── DataTable
        │   │   └── StatusBadge (per row)
        │   └── Modal (Add/Edit Device)
        │
        └── Settings/Index.vue
            ├── Profile Form
            ├── Password Form
            └── System Settings (Admin only)
```

---

## 📦 Build Output Structure

After running `npm run build`:

```
public/
└── build/
    ├── manifest.json          # Asset manifest
    ├── assets/
    │   ├── app.[hash].js      # Main JavaScript bundle
    │   ├── app.[hash].css     # Main CSS bundle
    │   └── vendor.[hash].js   # Third-party libraries
    └── *.map                  # Source maps (dev only)
```

---

## 🔌 API Integration Map

| Frontend Page | API Endpoints Used | Method |
|---------------|-------------------|--------|
| **Login.vue** | `/auth/login` | POST |
| | `/auth/refresh` | POST |
| **Dashboard** | `/sites` (get first) | GET |
| | `/data/last?site_uid=...` | GET |
| | `/data?site_uid=...&date_from=...` | GET |
| | `/devices?site_uid=...` | GET |
| | `/sites/{uid}/stats/last-seen` | GET |
| | `/healthz` | GET |
| **History** | `/sites` | GET |
| | `/data?site_uid=...&date_from=...&date_to=...&fields=...&page=...` | GET |
| **Devices** | `/sites` | GET |
| | `/devices?site_uid=...` | GET |
| | `/devices` (create) | POST |
| | `/sites/{uid}/stats/last-seen` | GET |
| **Settings** | (No API calls yet - TODO) | - |

---

## 🚀 Development Workflow

```
1. npm install
   ↓
2. cp .env.example .env
   ↓
3. Edit .env (set VITE_API_URL)
   ↓
4. npm run dev
   ↓
5. Open http://localhost:3000
   ↓
6. Login with credentials
   ↓
7. Start development!
```

---

## 📊 File Size Overview

| Category | Files | Total Lines* |
|----------|-------|--------------|
| Pages | 5 | ~1,500 |
| Components | 5 | ~800 |
| Composables | 2 | ~400 |
| Utils | 1 | ~300 |
| Config | 4 | ~100 |
| **Total** | **17** | **~3,100** |

*Approximate lines of code (excluding comments)

---

## 🎨 Asset Dependencies

| Asset Type | Source | Usage |
|------------|--------|-------|
| **Fonts** | Google Fonts (Inter) | Global typography |
| **Icons** | FontAwesome 6.4.0 (CDN) | UI icons |
| **Charts** | Chart.js (npm) | Data visualization |
| **Styles** | Tailwind CSS (npm) | Component styling |

---

## 🔐 Security Considerations

| File | Security Aspect |
|------|----------------|
| `.env` | Contains API URL - **Not committed to Git** |
| `localStorage` | Stores JWT tokens - **Use httpOnly cookies in production** |
| `useApi.js` | Auto-refresh tokens - **Prevents session timeout** |
| CORS | Backend must allow frontend origin |

---

**Last Updated**: 2025-12-25
**Total Files Created**: 20+
**Framework**: Vue.js 3 + Inertia.js + Tailwind CSS
