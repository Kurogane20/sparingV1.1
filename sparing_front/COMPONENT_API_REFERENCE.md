# Component API Reference

Quick reference for all reusable components and their props/events.

## 📦 Components

### SensorCard

Display sensor readings with trend indicators and status.

**Location**: `resources/js/Components/SensorCard.vue`

**Props**:
```typescript
{
  label: string          // Required - Display label (e.g., "Temperatur")
  value: number | string // Required - Sensor value or null
  unit?: string          // Optional - Unit suffix (e.g., "°C")
  icon: string           // Required - FontAwesome icon class
  iconClass?: string     // Optional - Icon background color class
  trend?: number | null  // Optional - Percentage change from previous
  field?: string         // Optional - Sensor field name for threshold check
  decimals?: number      // Optional - Decimal places (default: 1)
}
```

**Usage Example**:
```vue
<SensorCard
  label="Temperatur"
  :value="latestData?.temp"
  unit="°C"
  icon="fas fa-thermometer-half"
  icon-class="bg-red-100 text-red-600"
  :trend="1.2"
  field="temp"
  :decimals="1"
/>
```

**Features**:
- Auto-formats numbers with thousand separators
- Shows trend with colored arrows
- Applies threshold-based color coding
- Handles null/undefined values gracefully

---

### StatusBadge

Color-coded status indicator.

**Location**: `resources/js/Components/StatusBadge.vue`

**Props**:
```typescript
{
  status: string   // Required - Status value (online/offline/warning/etc)
  label: string    // Required - Display text
  icon?: string    // Optional - FontAwesome icon class
}
```

**Usage Example**:
```vue
<StatusBadge
  status="online"
  label="Sistem Online"
  icon="fas fa-wifi"
/>
```

**Status Colors**:
- `online`, `active` → Green
- `offline`, `inactive`, `error` → Red
- `warning`, `sleep` → Yellow
- Default → Gray

---

### DataTable

Paginated data table with custom cell rendering.

**Location**: `resources/js/Components/DataTable.vue`

**Props**:
```typescript
{
  title?: string          // Optional - Table title
  data: Array<object>     // Required - Array of row objects
  columns: Array<Column>  // Required - Column definitions
  loading?: boolean       // Optional - Show loading state
  emptyMessage?: string   // Optional - Message when no data
  pagination?: boolean    // Optional - Enable pagination
  currentPage?: number    // Optional - Current page number
  totalItems?: number     // Optional - Total items count
  perPage?: number        // Optional - Items per page
  rowKey?: string         // Optional - Unique row identifier (default: 'id')
}
```

**Column Definition**:
```typescript
{
  key: string              // Object property to display
  label: string            // Column header text
  format?: string | function  // 'date' | 'datetime' | 'number' | custom function
  decimals?: number        // For 'number' format
  headerClass?: string     // CSS classes for header
  cellClass?: string       // CSS classes for cells
}
```

**Events**:
```typescript
{
  'page-change': (page: number) => void  // Emitted when page changes
}
```

**Slots**:
```typescript
{
  actions: {}                           // Header action buttons
  'cell-{key}': { row, value }         // Custom cell rendering
}
```

**Usage Example**:
```vue
<DataTable
  title="Daftar Perangkat"
  :data="devices"
  :columns="[
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nama' },
    { key: 'created_at', label: 'Dibuat', format: 'date' },
    { key: 'voltage', label: 'Tegangan', format: 'number', decimals: 2 },
  ]"
  :loading="loading"
  :pagination="true"
  :current-page="1"
  :total-items="100"
  :per-page="20"
  @page-change="handlePageChange"
>
  <!-- Custom header actions -->
  <template #actions>
    <button @click="refresh">Refresh</button>
  </template>

  <!-- Custom cell rendering -->
  <template #cell-status="{ row, value }">
    <StatusBadge :status="value" :label="value" />
  </template>
</DataTable>
```

---

### Sidebar

Navigation sidebar with menu items.

**Location**: `resources/js/Components/Sidebar.vue`

**Props**:
```typescript
{
  isOpen: boolean  // Controls sidebar visibility (mobile)
}
```

**Events**:
```typescript
{
  close: () => void  // Emitted when sidebar should close
}
```

**Usage Example**:
```vue
<Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />
```

---

### Header

Top header with page title and user info.

**Location**: `resources/js/Components/Header.vue`

**Events**:
```typescript
{
  'toggle-sidebar': () => void  // Emitted when hamburger clicked
}
```

**Inertia Props** (via usePage):
```typescript
{
  title?: string      // Page title
  subtitle?: string   // Page subtitle
}
```

**Usage Example**:
```vue
<Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />
```

---

## 🎣 Composables

### useApi

Centralized API integration.

**Location**: `resources/js/Composables/useApi.js`

**Returns**:
```typescript
{
  // State
  loading: Ref<boolean>
  error: Ref<string | null>

  // Generic request
  request: (method, url, data?, config?) => Promise<any>

  // Auth
  login: (credentials) => Promise<AuthResponse>
  logout: () => Promise<void>
  refreshToken: (token) => Promise<AuthResponse>

  // Health
  healthCheck: () => Promise<HealthResponse>
  readinessCheck: () => Promise<ReadyResponse>

  // Sites
  getSites: (params?) => Promise<PaginatedResponse<Site>>
  getSite: (uid) => Promise<Site>
  createSite: (data) => Promise<Site>
  updateSite: (uid, data) => Promise<Site>
  deleteSite: (uid) => Promise<void>
  getSiteStats: (uid) => Promise<SiteStats>
  getSiteMetrics: (uid, params?) => Promise<Metrics>

  // Devices
  getDevices: (params) => Promise<PaginatedResponse<Device>>
  createDevice: (data) => Promise<Device>

  // Data
  ingestData: (data, idempotencyKey?) => Promise<IngestResponse>
  bulkIngest: (data) => Promise<IngestResponse>
  getData: (params) => Promise<PaginatedResponse<SensorData>>
  getLatestData: (siteUid) => Promise<SensorData>

  // Admin
  registerUser: (data) => Promise<User>
  getUsers: () => Promise<User[]>
}
```

**Usage Example**:
```javascript
import { useApi } from '@/Composables/useApi';

const { getSites, loading, error } = useApi();

const loadSites = async () => {
  try {
    const response = await getSites({ page: 1, per_page: 50 });
    sites.value = response.items;
  } catch (err) {
    console.error('Error:', error.value);
  }
};
```

---

### useAuth

Authentication state and methods.

**Location**: `resources/js/Composables/useAuth.js`

**Returns**:
```typescript
{
  // State
  user: Ref<User | null>
  token: Ref<string | null>

  // Computed
  isAuthenticated: ComputedRef<boolean>
  isAdmin: ComputedRef<boolean>
  isOperator: ComputedRef<boolean>

  // Methods
  login: (credentials) => Promise<AuthResponse>
  logout: () => Promise<void>
  hasRole: (role: string) => boolean
}
```

**Usage Example**:
```javascript
import { useAuth } from '@/Composables/useAuth';

const { user, isAuthenticated, isAdmin, login, logout } = useAuth();

// Check authentication
if (!isAuthenticated.value) {
  router.visit('/login');
}

// Check permission
if (isAdmin.value) {
  // Show admin features
}
```

---

## 🛠️ Helper Functions

### Date & Time

**Location**: `resources/js/Utils/helpers.js`

```typescript
formatDate(date: string | Date, includeTime?: boolean): string
// Returns: "25 Des 2025" or "25 Des 2025, 14:30"

getRelativeTime(date: string | Date): string
// Returns: "5 menit lalu", "2 jam lalu", etc.
```

---

### Sensor Utilities

```typescript
getSensorName(field: string): string
// 'temp' → 'Temperatur'
// 'ph' → 'pH'

getSensorUnit(field: string): string
// 'temp' → '°C'
// 'pm25' → 'µg/m³'

getThresholdStatus(field: string, value: number): 'normal' | 'warning' | 'danger'
// Checks if value is within acceptable range

validateSensorValue(field: string, value: number): boolean
// Validates value against field constraints
```

---

### Status Utilities

```typescript
getStatusClass(status: string): string
// Returns Tailwind classes for status badge
// 'online' → 'bg-green-100 text-green-800'
// 'offline' → 'bg-red-100 text-red-800'

getSensorStatus(lastSeen: string | Date, thresholdMinutes?: number): 'online' | 'warning' | 'offline'
// Determines device status based on last seen time
```

---

### Number & Data Formatting

```typescript
formatNumber(value: number, decimals?: number): string
// 1234.5678 → "1.234,57" (Indonesian format)

downloadCSV(data: Array<object>, filename: string): void
// Exports array of objects as CSV file

debounce(fn: Function, delay?: number): Function
// Returns debounced function (default delay: 300ms)
```

---

## 🎨 CSS Classes

### Tailwind Utilities

**Component Classes**:
```css
.card              /* White rounded card with shadow */
.status-badge      /* Status indicator pill */
.menu-item         /* Sidebar menu item */
.btn-primary       /* Primary button (green) */
.btn-secondary     /* Secondary button (blue) */
.btn-danger        /* Danger button (red) */
.form-input        /* Standard form input */
```

**Color Variables**:
```css
--primary-color: #10b981   /* Emerald green */
--secondary-color: #3b82f6 /* Blue */
--danger: #ef4444          /* Red */
--warning: #f59e0b         /* Yellow */
--sidebar-bg: #1f2937      /* Dark gray */
```

---

## 📝 TypeScript Type Definitions

For reference (TypeScript migration):

```typescript
// API Response Types
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

interface Site {
  id: number;
  uid: string;
  name: string;
  company_name: string;
  lat: number;
  lon: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Device {
  id: number;
  site_uid: string;
  name: string;
  modbus_addr: number;
  model?: string;
  serial_no?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface SensorData {
  id: number;
  site_uid: string;
  device_id?: number;
  ts: string;
  ph?: number;
  tss?: number;
  debit?: number;
  nh3n?: number;
  cod?: number;
  temp?: number;
  rh?: number;
  wind_speed_kmh?: number;
  wind_deg?: number;
  noise?: number;
  co?: number;
  so2?: number;
  no2?: number;
  o3?: number;
  pm25?: number;
  pm10?: number;
  tvoc?: number;
  voltage?: number;
  current?: number;
  payload?: object;
}

interface SiteStats {
  site_uid: string;
  last_seen_at: string;
  minutes_ago: number;
}

interface Metrics {
  site_uid: string;
  period: {
    from: string;
    to: string;
  };
  metrics: {
    [field: string]: {
      avg: number;
      min: number;
      max: number;
      count: number;
    };
  };
}

interface User {
  id: number;
  email: string;
  name?: string;
  role: 'admin' | 'operator' | 'viewer';
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
```

---

**Last Updated**: 2025-12-25
