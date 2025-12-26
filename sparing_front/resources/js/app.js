import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import '../css/app.css';

// Import pages
import Login from './Pages/Auth/Login.vue';
import Dashboard from './Pages/Dashboard/Index.vue';
import Analytics from './Pages/Analytics/Index.vue';
import History from './Pages/History/Index.vue';
import Sites from './Pages/Sites/Index.vue';
import Devices from './Pages/Devices/Index.vue';
import Users from './Pages/Users/Index.vue';
import Settings from './Pages/Settings/Index.vue';

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { requiresAuth: false },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: Dashboard,
      meta: { requiresAuth: true },
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: Analytics,
      meta: { requiresAuth: true },
    },
    {
      path: '/history',
      name: 'history',
      component: History,
      meta: { requiresAuth: true },
    },
    {
      path: '/sites',
      name: 'sites',
      component: Sites,
      meta: { requiresAuth: true },
    },
    {
      path: '/devices',
      name: 'devices',
      component: Devices,
      meta: { requiresAuth: true },
    },
    {
      path: '/users',
      name: 'users',
      component: Users,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings,
      meta: { requiresAuth: true },
    },
  ],
});

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token');
  const requiresAuth = to.meta.requiresAuth;

  if (requiresAuth && !token) {
    // Redirect to login if not authenticated
    next('/login');
  } else if (to.path === '/login' && token) {
    // Redirect to dashboard if already logged in
    next('/dashboard');
  } else {
    next();
  }
});

// Create and mount app
const app = createApp(App);

app.use(router);
app.mount('#app');
