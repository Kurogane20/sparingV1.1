# SPARING Frontend - Implementation Guide

## 📋 Overview

This document explains the complete Vue.js 3 + Inertia.js frontend implementation for SPARING (Industrial Environmental Monitoring System).

## 🏗️ Architecture

### Component-Based Design

The application follows Vue.js 3 Composition API pattern with:

1. **Pages**: Route-level components
2. **Components**: Reusable UI components
3. **Composables**: Shared business logic
4. **Utils**: Helper functions
5. **Layouts**: Page layouts

### Data Flow

```
User Action → Component → Composable → API → Backend
                 ↓
             Update State
                 ↓
            Re-render UI
```

## 🔌 API Integration

### useApi Composable

Located at: [resources/js/Composables/useApi.js](resources/js/Composables/useApi.js)

**Purpose**: Centralize all API calls and handle authentication automatically.

**Key Features**:
- Axios interceptors for JWT token injection
- Automatic token refresh on 401
- Error handling
- Loading states

**Usage Example**:
```javascript
import { useApi } from '@/Composables/useApi';

const { getSites, loading, error } = useApi();

// Fetch sites
const sites = await getSites({ page: 1, per_page: 50 });
```

### API Endpoints Mapped

| API Endpoint | Composable Method | Used In |
|--------------|-------------------|---------|
| `/auth/login` | `login(credentials)` | Login.vue |
| `/auth/logout` | `logout()` | Sidebar.vue |
| `/sites` | `getSites(params)` | Dashboard, History, Devices |
| `/sites/{uid}` | `getSite(uid)` | Dashboard |
| `/sites/{uid}/stats/last-seen` | `getSiteStats(uid)` | Dashboard, Devices |
| `/sites/{uid}/metrics` | `getSiteMetrics(uid, params)` | Dashboard |
| `/devices` | `getDevices(params)` | Dashboard, Devices |
| `/devices` (POST) | `createDevice(data)` | Devices |
| `/data` | `getData(params)` | History, Dashboard |
| `/data/last` | `getLatestData(siteUid)` | Dashboard |
| `/ingest/state` | `ingestData(data, key)` | (Future) |
| `/healthz` | `healthCheck()` | Header.vue |

## 🔐 Authentication Flow

### Login Process

1. User enters credentials in [Login.vue](resources/js/Pages/Auth/Login.vue)
2. Calls `useAuth().login(credentials)`
3. `useAuth` calls `useApi().login()`
4. On success:
   - Store `access_token` and `refresh_token` in localStorage
   - Store user info
   - Redirect to `/dashboard`

### Token Refresh

Handled automatically in [useApi.js:36-55](resources/js/Composables/useApi.js#L36-L55):

```javascript
// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        const { data } = await axios.post('/auth/refresh', {
          refresh_token: refreshToken,
        });
        // Retry original request with new token
        return apiClient.request(error.config);
      }
    }
  }
);
```

### Logout Process

1. User clicks logout in Sidebar
2. Calls `useAuth().logout()`
3. Sends logout request to API
4. Clears localStorage
5. Redirects to `/login`

## 📊 Dashboard Implementation

Located at: [resources/js/Pages/Dashboard/Index.vue](resources/js/Pages/Dashboard/Index.vue)

### Real-Time Monitoring

**Auto-Refresh**: Every 30 seconds

```javascript
// Setup auto-refresh interval
refreshInterval = setInterval(async () => {
  await loadLatestData();
  updateDonutChart();
}, 30000);
```

### Data Loading Sequence

1. **onMounted**:
   ```javascript
   loadSite()          // Get first available site
   ↓
   loadLatestData()    // Get latest sensor readings
   ↓
   loadDevices()       // Get device list
   ↓
   loadChartData()     // Get historical data for chart
   ↓
   updateDonutChart()  // Render pollutant distribution
   ```

2. **Auto-refresh**:
   - Refresh latest data every 30s
   - Update donut chart with new values

### Sensor Cards

Uses [SensorCard.vue](resources/js/Components/SensorCard.vue):

```vue
<SensorCard
  label="Temperatur"
  :value="latestData?.temp"
  unit="°C"
  icon="fas fa-thermometer-half"
  icon-class="bg-red-100 text-red-600"
  :trend="getTrend('temp')"
  field="temp"
/>
```

**Trend Calculation**:
- Compares current value with previous reading
- Shows percentage change
- Color-coded: green (down), red (up), gray (stable)

### Charts Integration

**Chart.js** is used for visualizations:

1. **Line Chart** (Temperature & Humidity):
   - X-axis: Time labels
   - Y-axis: Sensor values
   - Two datasets: temp (red), rh (blue)

2. **Donut Chart** (Pollutant Distribution):
   - Shows PM2.5, PM10, O3, NO2
   - Color-coded segments

## 📜 History Page Implementation

Located at: [resources/js/Pages/History/Index.vue](resources/js/Pages/History/Index.vue)

### Filter System

**Available Filters**:
- Site selection (dropdown)
- Date range (from/to)
- Sensor fields (multi-select)

**Filter Flow**:
```javascript
User changes filter → applyFilters()
                       ↓
               Reset page to 1
                       ↓
            loadHistoryData() with new params
                       ↓
              Update table display
```

### Pagination

Managed by [DataTable.vue](resources/js/Components/DataTable.vue):

```javascript
pagination = {
  currentPage: 1,
  totalItems: 0,  // From API response
  perPage: 50
}
```

**Page Change Flow**:
```
User clicks page → handlePageChange(page)
                    ↓
          Update currentPage
                    ↓
           loadHistoryData()
```

### CSV Export

Uses helper function from [helpers.js:243-259](resources/js/Utils/helpers.js#L243-L259):

```javascript
const exportToCSV = () => {
  const csvData = historyData.value.map((row) => ({
    'Waktu': formatDate(row.ts, true),
    'pH': row.ph,
    'TSS': row.tss,
    // ... other fields
  }));

  downloadCSV(csvData, `sparing-data-${siteUid}-${date}.csv`);
};
```

## 🔧 Device Management

Located at: [resources/js/Pages/Devices/Index.vue](resources/js/Pages/Devices/Index.vue)

### CRUD Operations

**Create Device**:
```javascript
const saveDevice = async () => {
  const payload = {
    site_uid: selectedSiteUid.value,
    name: deviceForm.name,
    model: deviceForm.model,
    serial_no: deviceForm.serial_no,
    modbus_addr: deviceForm.modbus_addr,
    is_active: deviceForm.is_active
  };

  await createDevice(payload);
  await loadDevices(); // Refresh list
};
```

**Update Device**:
- Not yet implemented in API
- TODO placeholder in code

**Toggle Status**:
- Local state update (pending API endpoint)

### Device Status Detection

Based on last seen time from API:

```javascript
const getDeviceStatus = (device) => {
  const minutesAgo = stats.minutes_ago;

  if (minutesAgo < 5) return 'online';    // Green
  if (minutesAgo < 30) return 'warning';  // Yellow
  return 'offline';                       // Red
};
```

## 🎨 Reusable Components

### 1. SensorCard

**Props**:
- `label`: Display name
- `value`: Sensor reading
- `unit`: Unit of measurement
- `icon`: FontAwesome icon class
- `iconClass`: Icon background color
- `trend`: Percentage change
- `field`: Sensor field name (for threshold detection)

**Features**:
- Auto-format numbers
- Trend indicators (up/down/stable)
- Color-coded status labels
- Null value handling

### 2. StatusBadge

**Props**:
- `status`: Status value (online/offline/warning/etc)
- `label`: Display text
- `icon`: Optional icon

**Auto-styling**:
```javascript
// Automatically applies color based on status
getStatusClass('online')   → 'bg-green-100 text-green-800'
getStatusClass('offline')  → 'bg-red-100 text-red-800'
getStatusClass('warning')  → 'bg-yellow-100 text-yellow-800'
```

### 3. DataTable

**Props**:
- `title`: Table title
- `data`: Array of row objects
- `columns`: Column definitions
- `loading`: Loading state
- `pagination`: Enable pagination
- `currentPage`, `totalItems`, `perPage`: Pagination config

**Column Definition**:
```javascript
{
  key: 'field_name',           // Object property
  label: 'Display Name',       // Header text
  format: 'date|datetime|number|function', // Auto-formatting
  decimals: 2,                 // For number format
  headerClass: '',             // Custom header classes
  cellClass: ''                // Custom cell classes
}
```

**Custom Cell Rendering**:
```vue
<DataTable :data="items" :columns="columns">
  <!-- Custom cell template -->
  <template #cell-status="{ row, value }">
    <StatusBadge :status="value" :label="value" />
  </template>
</DataTable>
```

## 🛠️ Helper Functions

Located at: [resources/js/Utils/helpers.js](resources/js/Utils/helpers.js)

### Date & Time

- `formatDate(date, includeTime)`: Indonesian date format
- `getRelativeTime(date)`: "5 menit lalu"

### Sensor Utilities

- `getSensorName(field)`: Human-readable name
- `getSensorUnit(field)`: Unit string (°C, %, ppm, etc)
- `getThresholdStatus(field, value)`: normal/warning/danger
- `validateSensorValue(field, value)`: Range validation

### Data Processing

- `formatNumber(value, decimals)`: Thousand separators
- `downloadCSV(data, filename)`: Export to CSV
- `debounce(fn, delay)`: Debounce function

### Status Helpers

- `getStatusClass(status)`: CSS class for status
- `getSensorStatus(lastSeen, threshold)`: Determine online/offline

## 🔄 Component Communication

### Props Down, Events Up

**Parent to Child** (Props):
```vue
<SensorCard :value="temperature" :trend="tempTrend" />
```

**Child to Parent** (Events):
```vue
<!-- Child emits event -->
<button @click="$emit('close')">Close</button>

<!-- Parent listens -->
<Modal @close="handleClose" />
```

### Shared State (Composables)

```javascript
// Multiple components can access same auth state
const { user, isAuthenticated } = useAuth();
```

## 🎯 Best Practices Applied

### 1. Single Responsibility

Each component has one clear purpose:
- `SensorCard`: Display sensor value
- `DataTable`: Display tabular data
- `StatusBadge`: Show status indicator

### 2. DRY (Don't Repeat Yourself)

Reusable components prevent code duplication:
- ✅ One `SensorCard` component used 4 times in Dashboard
- ❌ Instead of 4 similar card implementations

### 3. Composition Over Inheritance

Use composables for shared logic:
```javascript
// useApi composable used in all pages
const { getData } = useApi();
```

### 4. Prop Validation

```javascript
defineProps({
  value: {
    type: [Number, String],
    default: null,
  },
  trend: {
    type: Number,
    default: null,
  }
});
```

### 5. Error Handling

```javascript
try {
  await getData(params);
} catch (error) {
  console.error('Failed to load data:', error);
  // Show user-friendly message
}
```

## 📱 Responsive Design

### Breakpoint Strategy

```css
/* Mobile First */
.grid { grid-template-columns: 1fr; }

/* Tablet */
@media (min-width: 768px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Desktop */
@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(4, 1fr); }
}
```

### Sidebar Behavior

- **Desktop**: Always visible
- **Mobile**: Toggle with hamburger menu
- **Transition**: Smooth slide animation

## 🧪 Testing Strategy

### Manual Testing Checklist

- [ ] Login with valid credentials
- [ ] Login with invalid credentials (error handling)
- [ ] Dashboard loads sensor data
- [ ] Auto-refresh updates data
- [ ] Charts render correctly
- [ ] Filter history data
- [ ] Paginate through results
- [ ] Export CSV
- [ ] Create new device (operator role)
- [ ] Logout

### Browser Compatibility

Test on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

Output: `public/build/`

### Environment Configuration

**Development**:
```env
VITE_API_URL=http://localhost:8000
VITE_DEBUG=true
```

**Production**:
```env
VITE_API_URL=https://api.yourdomain.com
VITE_DEBUG=false
```

### Serve Static Files

The built files in `public/build/` should be served by:
- Nginx
- Apache
- Inertia.js server-side adapter (Laravel/FastAPI)

## 📝 Code Style Guide

### Naming Conventions

- **Components**: PascalCase (`SensorCard.vue`)
- **Composables**: camelCase starting with 'use' (`useApi.js`)
- **Props**: camelCase (`sensorValue`)
- **Events**: kebab-case (`page-change`)
- **CSS classes**: kebab-case (`sensor-card`)

### File Organization

```vue
<template>
  <!-- HTML structure -->
</template>

<script setup>
// Imports
import { ref } from 'vue';

// Composables
const { getData } = useApi();

// State
const data = ref([]);

// Computed
const filteredData = computed(() => ...);

// Methods
const loadData = async () => { ... };

// Lifecycle
onMounted(() => { ... });
</script>

<style scoped>
/* Component-specific styles */
</style>
```

## 🔮 Future Enhancements

### Planned Features

1. **Real-time WebSocket**: Replace polling with WebSocket for live updates
2. **Advanced Filters**: Date presets, custom ranges, saved filters
3. **Alarm System**: Visual and audio notifications for threshold breaches
4. **Multi-language**: i18n support (Indonesian, English)
5. **Dark Mode**: Theme toggle
6. **User Management**: Admin panel for user CRUD
7. **Reports**: PDF report generation
8. **Analytics**: Advanced data visualization with D3.js

### Technical Improvements

1. **TypeScript**: Migrate to TypeScript for type safety
2. **Unit Tests**: Vitest + Vue Test Utils
3. **E2E Tests**: Playwright/Cypress
4. **State Management**: Pinia (if needed for complex state)
5. **PWA**: Service worker for offline capability
6. **Performance**: Virtual scrolling for large datasets

## 🆘 Troubleshooting

### Common Issues

**Issue**: White screen on load
**Solution**: Check console for errors, verify API URL in .env

**Issue**: Login fails
**Solution**: Verify backend is running, check CORS settings

**Issue**: Charts not rendering
**Solution**: Ensure Chart.js is loaded, check data format

**Issue**: Data not refreshing
**Solution**: Check auto-refresh interval, verify API connection

## 📚 Additional Resources

- [Vue.js 3 Documentation](https://vuejs.org/)
- [Inertia.js Documentation](https://inertiajs.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Chart.js Documentation](https://www.chartjs.org/)
- [SPARING API Documentation](./API.md)

---

**Last Updated**: 2025-12-25
**Version**: 1.0.0
