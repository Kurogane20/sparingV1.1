# 🚀 SPARING Frontend - Quick Start Guide

Get up and running in 5 minutes!

## ✅ Prerequisites

- **Node.js** 18+ installed ([download](https://nodejs.org/))
- **SPARING Backend** running on `http://localhost:8000`
- Basic knowledge of Vue.js and terminal commands

## 📋 Step-by-Step Setup

### 1️⃣ Install Dependencies

```bash
cd sparing_front
npm install
```

**Expected output**: Dependencies installed successfully (~2 minutes)

---

### 2️⃣ Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
# Windows: notepad .env
# Mac/Linux: nano .env
```

**Edit `.env` file**:
```env
VITE_API_URL=http://localhost:8000
VITE_APP_ENV=development
VITE_DEBUG=true
```

> **Important**: Make sure `VITE_API_URL` points to your running backend!

---

### 3️⃣ Start Development Server

```bash
npm run dev
```

**Expected output**:
```
VITE v5.0.8  ready in 500 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

---

### 4️⃣ Open in Browser

Navigate to: **http://localhost:3000**

You should see the **SPARING Login Page**

---

### 5️⃣ Login with Test Credentials

Use credentials from your backend setup:

```
Email: op@example.com
Password: Op#12345
```

> **Note**: These are example credentials from the API documentation. Use actual credentials from your backend.

---

### 6️⃣ Explore the Application

After successful login, you'll see:

✅ **Dashboard** - Real-time sensor monitoring
✅ **History** - Historical data with filters
✅ **Devices** - IoT device management
✅ **Settings** - User preferences

---

## 🎯 First-Time Checklist

- [ ] Backend API is running on port 8000
- [ ] Can access Swagger docs at `http://localhost:8000/docs`
- [ ] `.env` file created with correct API URL
- [ ] Dependencies installed (`node_modules/` exists)
- [ ] Dev server running (`npm run dev`)
- [ ] Can open http://localhost:3000 in browser
- [ ] Login page loads
- [ ] Can login successfully
- [ ] Dashboard shows data

---

## 🐛 Common Issues

### Issue: "Cannot connect to API"

**Solution**:
1. Check backend is running: `http://localhost:8000/docs`
2. Verify `VITE_API_URL` in `.env`
3. Check for CORS errors in browser console

**Fix CORS (Backend)**:
```python
# In FastAPI backend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Issue: "Login fails with 401"

**Solution**:
1. Verify credentials are correct
2. Check backend `/auth/login` endpoint works
3. Test login in Swagger UI first

---

### Issue: "White screen / No data"

**Solution**:
1. Open browser DevTools (F12)
2. Check Console for errors
3. Check Network tab for failed API calls
4. Verify backend has sample data

---

### Issue: "npm install fails"

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

---

## 📚 Next Steps

### Learn the Codebase

1. Read [README.md](./README.md) - Project overview
2. Read [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - Detailed implementation
3. Read [COMPONENT_API_REFERENCE.md](./COMPONENT_API_REFERENCE.md) - Component docs

### Customize

1. **Change Colors**: Edit `tailwind.config.js`
2. **Add Pages**: Create new `.vue` files in `resources/js/Pages/`
3. **Add Components**: Create in `resources/js/Components/`

### Deploy

```bash
# Build for production
npm run build

# Output will be in public/build/
```

---

## 🎓 Tutorials

### Add a New Page

**Step 1**: Create Vue component
```bash
# Create file
touch resources/js/Pages/Reports/Index.vue
```

**Step 2**: Add content
```vue
<template>
  <AppLayout>
    <h1>Reports Page</h1>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
</script>
```

**Step 3**: Add to sidebar (edit `Components/Sidebar.vue`)
```javascript
const menuItems = [
  // ... existing items
  {
    path: '/reports',
    icon: 'fas fa-file-alt',
    label: 'Laporan',
  },
];
```

---

### Add a New API Endpoint

**Step 1**: Add to `useApi.js`
```javascript
const getReports = (params = {}) =>
  request('GET', '/reports', null, { params });

return {
  // ... existing methods
  getReports,
};
```

**Step 2**: Use in component
```javascript
import { useApi } from '@/Composables/useApi';

const { getReports } = useApi();

const loadReports = async () => {
  const data = await getReports({ month: 'january' });
  console.log(data);
};
```

---

### Add a New Sensor Card

```vue
<SensorCard
  label="Tekanan"
  :value="latestData?.pressure"
  unit="hPa"
  icon="fas fa-tachometer-alt"
  icon-class="bg-purple-100 text-purple-600"
  :trend="getTrend('pressure')"
  field="pressure"
/>
```

---

## 🔧 Useful Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start dev server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm install <package>` | Add new dependency |
| `npm list` | List installed packages |

---

## 📞 Getting Help

### Check Documentation

- [README.md](./README.md) - Main docs
- [API.md](./API.md) - Backend API reference
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - Implementation details

### Check Browser Console

Press **F12** → **Console** tab to see errors

### Check Network Requests

Press **F12** → **Network** tab to see API calls

### Verify Backend

Visit: `http://localhost:8000/docs` (Swagger UI)

---

## 🎉 You're All Set!

Your SPARING frontend is now running. Start developing!

### Recommended Workflow

1. **Make changes** to `.vue` files
2. **Save file** (Vite will auto-reload)
3. **Check browser** for updates
4. **Check console** for errors
5. **Repeat**!

---

## 📖 Additional Resources

- [Vue.js Docs](https://vuejs.org/) - Vue.js 3 documentation
- [Inertia.js Docs](https://inertiajs.com/) - Inertia.js documentation
- [Tailwind Docs](https://tailwindcss.com/) - Tailwind CSS documentation
- [Chart.js Docs](https://www.chartjs.org/) - Chart.js documentation

---

**Happy Coding! 🚀**

---

**Last Updated**: 2025-12-25
