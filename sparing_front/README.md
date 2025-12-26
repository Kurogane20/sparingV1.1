# SPARING - Industrial Environmental Monitoring System

Frontend application for SPARING (Air Quality Monitoring System / AQMS) built with Vue.js 3, Inertia.js, and Tailwind CSS.

## 📋 Features

- **Authentication**: JWT-based login with automatic token refresh
- **Dashboard**: Real-time sensor data monitoring with charts
- **History**: Historical data filtering, pagination, and CSV export
- **Device Management**: IoT device configuration and status monitoring
- **Settings**: User profile and system configuration
- **Responsive Design**: Mobile-friendly interface based on industrial design system

## 🛠️ Tech Stack

- **Framework**: Vue.js 3 (Composition API)
- **Routing**: Inertia.js
- **Styling**: Tailwind CSS
- **Charts**: Chart.js
- **HTTP Client**: Axios
- **Build Tool**: Vite

## 📂 Project Structure

```
resources/
├── js/
│   ├── Pages/
│   │   ├── Auth/
│   │   │   └── Login.vue              # Login page
│   │   ├── Dashboard/
│   │   │   └── Index.vue              # Main dashboard with real-time data
│   │   ├── History/
│   │   │   └── Index.vue              # Historical data with filters
│   │   ├── Devices/
│   │   │   └── Index.vue              # Device management
│   │   └── Settings/
│   │       └── Index.vue              # User & system settings
│   ├── Components/
│   │   ├── Sidebar.vue                # Navigation sidebar
│   │   ├── Header.vue                 # Top header with status
│   │   ├── SensorCard.vue             # Reusable sensor display card
│   │   ├── StatusBadge.vue            # Status indicator component
│   │   └── DataTable.vue              # Reusable data table with pagination
│   ├── Layouts/
│   │   └── AppLayout.vue              # Main application layout
│   ├── Composables/
│   │   ├── useApi.js                  # API integration composable
│   │   └── useAuth.js                 # Authentication composable
│   ├── Utils/
│   │   └── helpers.js                 # Helper functions
│   └── app.js                         # Main entry point
└── css/
    └── app.css                        # Global styles
```

## 🚀 Setup Instructions

### 1. Prerequisites

- Node.js 18+ and npm/yarn
- Running SPARING backend API (FastAPI)

### 2. Installation

```bash
# Clone repository or navigate to project folder
cd sparing_front

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Edit .env and set your API URL
# VITE_API_URL=http://localhost:8000
```

### 3. Development

```bash
# Start development server
npm run dev

# Application will run on http://localhost:3000
```

### 4. Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔐 Authentication

The application uses JWT authentication following the API specification:

### Login Credentials

Use credentials from your backend setup. Example:
- **Email**: `op@example.com`
- **Password**: `Op#12345`

### Token Management

- Access tokens are stored in `localStorage`
- Automatic token refresh on 401 errors
- Auto-redirect to login on authentication failure

## 📊 API Integration

All API endpoints are documented in [API.md](./API.md) and integrated via the `useApi` composable.

### Key Endpoints Used:

| Endpoint | Purpose | Page |
|----------|---------|------|
| `POST /auth/login` | User authentication | Login |
| `GET /sites` | List monitoring sites | Dashboard, History |
| `GET /devices` | List IoT devices | Dashboard, Devices |
| `GET /data/last` | Latest sensor readings | Dashboard |
| `GET /data` | Historical data | History |
| `GET /sites/{uid}/metrics` | Site statistics | Dashboard |
| `GET /sites/{uid}/stats/last-seen` | Device status | Dashboard, Devices |

## 🎨 Design System

Based on the HTML prototype ([contoh.html](./contoh.html)):

### Color Palette

```css
--primary-color: #10b981   /* Emerald Green */
--secondary-color: #3b82f6 /* Blue */
--danger: #ef4444          /* Red */
--warning: #f59e0b         /* Yellow */
```

### Components

- **SensorCard**: Displays sensor value with trend indicator
- **StatusBadge**: Color-coded status indicators
- **DataTable**: Paginated table with custom cell rendering
- **Charts**: Line chart (trends) and Donut chart (distribution)

## 📱 Responsive Breakpoints

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 🔧 Configuration

### Environment Variables

```env
VITE_API_URL         # Backend API base URL
VITE_APP_ENV         # Environment (development/production)
VITE_APP_NAME        # Application name
VITE_DEBUG           # Enable debug mode
```

### Auto-Refresh

Dashboard automatically refreshes sensor data every **30 seconds**.

To modify:
```javascript
// In Dashboard/Index.vue
const refreshInterval = 30000; // milliseconds
```

## 📈 Data Flow

### Dashboard Page

1. **Mount**: Load sites → Load latest data → Load devices
2. **Auto-refresh**: Every 30s update latest data and charts
3. **Chart period**: User can select today/week/month

### History Page

1. **Filter**: User selects site, date range, sensor fields
2. **Fetch**: API call with filters and pagination
3. **Export**: Download filtered data as CSV

### Devices Page

1. **Site selection**: User selects monitoring site
2. **Load devices**: Fetch devices for selected site
3. **CRUD**: Create/update devices (operator/admin only)

## 🔒 Role-Based Access

### Roles (from API)

- **admin**: Full access to all features
- **operator**: Can manage sites, devices, and data
- **viewer**: Read-only access to assigned sites

### Permission Checks

```javascript
import { useAuth } from '@/Composables/useAuth';

const { isAdmin, isOperator } = useAuth();

// Check in templates
<button v-if="isOperator">Add Device</button>
```

## 🐛 Troubleshooting

### API Connection Issues

1. Check backend is running: `http://localhost:8000/docs`
2. Verify `VITE_API_URL` in `.env`
3. Check CORS settings in backend

### Authentication Errors

1. Verify credentials with backend
2. Clear localStorage: `localStorage.clear()`
3. Check JWT token expiration in backend

### Chart Not Displaying

1. Check Chart.js is loaded
2. Verify data format from API
3. Check console for errors

## 📝 TODO / Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Advanced alarm configuration
- [ ] Multi-site comparison charts
- [ ] Mobile app (Progressive Web App)
- [ ] Data export to Excel
- [ ] Custom dashboard widgets
- [ ] User activity logs
- [ ] Notification preferences

## 🤝 Contributing

1. Follow Vue.js 3 Composition API best practices
2. Use TypeScript for type safety (future)
3. Write meaningful commit messages
4. Test on multiple browsers
5. Follow existing code style

## 📄 License

Copyright © 2025 SPARING Project

## 🆘 Support

For issues or questions:
- Check API documentation: [API.md](./API.md)
- Review HTML prototype: [contoh.html](./contoh.html)
- Contact development team

---

**Built with ❤️ using Vue.js 3 + Inertia.js**
