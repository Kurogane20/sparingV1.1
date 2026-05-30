# Feature 3: Device Health & Maintenance Log — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show real-time sensor health (online/warning/offline) on device cards and let operators record calibration and maintenance events per device.

**Architecture:** A new `MaintenanceLog` table stores typed log entries per device. Three new routes (`/health`, `/maintenance` GET/POST/DELETE) are added to the existing devices router. The frontend enhances device cards with live health status fetched from the health endpoint, and adds a "Log Perawatan" tab to the existing device detail modal.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic · Vue 3 Composition API + TailwindCSS

---

## File Map

### Backend — Create
- `sparing_api/alembic/versions/0004_add_maintenance_log.py` — migration
- `sparing_api/app/tests/test_device_health.py` — unit tests for health status logic

### Backend — Modify
- `sparing_api/app/models/models.py` — add `MaintenanceLog` model
- `sparing_api/app/schemas/device.py` — add `MaintenanceLogCreate`, `MaintenanceLogOut`, `DeviceHealthOut`
- `sparing_api/app/api/routers/devices.py` — add health + maintenance endpoints

### Frontend — Modify
- `sparing_front/resources/js/Composables/useApi.js` — add 4 new device methods
- `sparing_front/resources/js/Pages/Devices/Index.vue` — enhanced cards + maintenance modal

---

## Task 1: Migration — maintenance_logs table

**Files:**
- Create: `sparing_api/alembic/versions/0004_add_maintenance_log.py`

- [ ] **Step 1: Create migration file**

Create `sparing_api/alembic/versions/0004_add_maintenance_log.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = '0004_add_maintenance_log'
down_revision = '0003_add_site_device_secret'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('maintenance_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('sensor_devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(32), nullable=False),  # calibration|repair|inspection|note
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('performed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_maintenance_logs_device_id', 'maintenance_logs', ['device_id'])
    op.create_index('ix_maintenance_logs_performed_at', 'maintenance_logs', ['performed_at'])

def downgrade():
    op.drop_index('ix_maintenance_logs_performed_at', table_name='maintenance_logs')
    op.drop_index('ix_maintenance_logs_device_id', table_name='maintenance_logs')
    op.drop_table('maintenance_logs')
```

- [ ] **Step 2: Commit**

```bash
git add sparing_api/alembic/versions/0004_add_maintenance_log.py
git commit -m "feat: migration to add maintenance_logs table"
```

---

## Task 2: MaintenanceLog model, schemas, and health status tests

**Files:**
- Modify: `sparing_api/app/models/models.py`
- Modify: `sparing_api/app/schemas/device.py`
- Create: `sparing_api/app/tests/test_device_health.py`

- [ ] **Step 1: Write failing tests**

Create `sparing_api/app/tests/test_device_health.py`:

```python
from datetime import datetime, timezone, timedelta
from app.utils.device_health import compute_health_status

def _ago(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)

def test_health_online():
    assert compute_health_status(_ago(5)) == "online"

def test_health_warning():
    assert compute_health_status(_ago(30)) == "warning"

def test_health_offline():
    assert compute_health_status(_ago(120)) == "offline"

def test_health_unknown():
    assert compute_health_status(None) == "unknown"

def test_health_boundary_online():
    # Exactly 14 min ago → still online
    assert compute_health_status(_ago(14)) == "online"

def test_health_boundary_warning():
    # Exactly 15 min ago → warning
    assert compute_health_status(_ago(15)) == "warning"

def test_health_boundary_offline():
    # Exactly 60 min ago → offline
    assert compute_health_status(_ago(60)) == "offline"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd sparing_api && python -m pytest app/tests/test_device_health.py -v
```

Expected: `ImportError` — `app.utils.device_health` doesn't exist yet.

- [ ] **Step 3: Create device_health utility**

Create `sparing_api/app/utils/device_health.py`:

```python
from datetime import datetime, timezone

def compute_health_status(last_seen: datetime | None) -> str:
    """Return 'online', 'warning', 'offline', or 'unknown' based on last_seen timestamp."""
    if last_seen is None:
        return "unknown"
    diff_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
    if diff_minutes < 15:
        return "online"
    if diff_minutes < 60:
        return "warning"
    return "offline"
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd sparing_api && python -m pytest app/tests/test_device_health.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Add MaintenanceLog model to models.py**

Read `sparing_api/app/models/models.py`. At the end of the file, append:

```python
class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("sensor_devices.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # calibration | repair | inspection | note
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    device: Mapped["SensorDevice"] = relationship()
    performed_by: Mapped["User | None"] = relationship(foreign_keys=[performed_by_user_id])
```

Also add `Text` to the existing import line in models.py — it's imported in the first line as `from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, UniqueConstraint, Index, Text`. Check if `Text` is already there; if not, add it.

- [ ] **Step 6: Add schemas to device.py**

Read `sparing_api/app/schemas/device.py`. Add `from datetime import datetime` at the top, then append at the end:

```python
class MaintenanceLogCreate(BaseModel):
    type: str  # calibration | repair | inspection | note
    notes: str | None = None
    performed_at: datetime
    next_due_at: datetime | None = None

class MaintenanceLogOut(BaseModel):
    id: int
    device_id: int
    type: str
    notes: str | None
    performed_by_user_id: int | None
    performed_by_name: str | None
    performed_at: datetime
    next_due_at: datetime | None
    created_at: datetime

class DeviceHealthOut(BaseModel):
    device_id: int
    last_seen: datetime | None
    status: str  # online | warning | offline | unknown
    data_count_24h: int
    data_count_7d: int
    last_calibration_at: datetime | None = None
    next_calibration_at: datetime | None = None
```

- [ ] **Step 7: Verify imports**

```bash
cd sparing_api && python -c "from app.models.models import MaintenanceLog; from app.schemas.device import MaintenanceLogCreate, MaintenanceLogOut, DeviceHealthOut; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add sparing_api/app/utils/device_health.py sparing_api/app/tests/test_device_health.py sparing_api/app/models/models.py sparing_api/app/schemas/device.py
git commit -m "feat: add MaintenanceLog model, device health utility, and schemas"
```

---

## Task 3: Backend endpoints — health + maintenance CRUD

**Files:**
- Modify: `sparing_api/app/api/routers/devices.py`

- [ ] **Step 1: Add imports**

Read `sparing_api/app/api/routers/devices.py`. Add to the imports at the top:

```python
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app.models.models import Site, SensorDevice, SensorData, MaintenanceLog
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut, MaintenanceLogCreate, MaintenanceLogOut, DeviceHealthOut
from app.api.deps import require_roles, get_viewer_site_uids, get_current_user
from app.utils.device_health import compute_health_status
```

Replace the existing import lines in devices.py with the above (merging with whatever is already there — read first to avoid duplication).

- [ ] **Step 2: Append health endpoint**

At the bottom of `devices.py`, add:

```python
@router.get("/{id}/health", response_model=DeviceHealthOut)
async def get_device_health(
    id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    # Last seen: most recent SensorData row for this device
    last_seen_row = await db.execute(
        select(func.max(SensorData.ts)).where(SensorData.device_id == id)
    )
    last_seen: datetime | None = last_seen_row.scalar_one_or_none()

    # Count records in last 24h and 7d
    count_24h = (await db.execute(
        select(func.count(SensorData.id)).where(
            SensorData.device_id == id,
            SensorData.ts >= cutoff_24h,
        )
    )).scalar_one() or 0

    count_7d = (await db.execute(
        select(func.count(SensorData.id)).where(
            SensorData.device_id == id,
            SensorData.ts >= cutoff_7d,
        )
    )).scalar_one() or 0

    # Last calibration and next calibration due
    last_cal_row = await db.execute(
        select(MaintenanceLog.performed_at)
        .where(MaintenanceLog.device_id == id, MaintenanceLog.type == "calibration")
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(1)
    )
    last_calibration_at: datetime | None = last_cal_row.scalar_one_or_none()

    next_cal_row = await db.execute(
        select(MaintenanceLog.next_due_at)
        .where(
            MaintenanceLog.device_id == id,
            MaintenanceLog.type == "calibration",
            MaintenanceLog.next_due_at.isnot(None),
        )
        .order_by(MaintenanceLog.next_due_at.asc())
        .limit(1)
    )
    next_calibration_at: datetime | None = next_cal_row.scalar_one_or_none()

    return DeviceHealthOut(
        device_id=id,
        last_seen=last_seen,
        status=compute_health_status(last_seen),
        data_count_24h=count_24h,
        data_count_7d=count_7d,
        last_calibration_at=last_calibration_at,
        next_calibration_at=next_calibration_at,
    )
```

- [ ] **Step 3: Append maintenance list endpoint**

```python
@router.get("/{id}/maintenance", response_model=list[MaintenanceLogOut])
async def list_maintenance_logs(
    id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    from app.models.models import User
    result = await db.execute(
        select(MaintenanceLog, User.name.label("performer_name"))
        .outerjoin(User, User.id == MaintenanceLog.performed_by_user_id)
        .where(MaintenanceLog.device_id == id)
        .order_by(MaintenanceLog.performed_at.desc())
    )
    rows = result.all()
    return [
        MaintenanceLogOut(
            id=log.id,
            device_id=log.device_id,
            type=log.type,
            notes=log.notes,
            performed_by_user_id=log.performed_by_user_id,
            performed_by_name=performer_name,
            performed_at=log.performed_at,
            next_due_at=log.next_due_at,
            created_at=log.created_at,
        )
        for log, performer_name in rows
    ]
```

- [ ] **Step 4: Append maintenance create endpoint**

```python
@router.post("/{id}/maintenance", response_model=MaintenanceLogOut,
             dependencies=[Depends(require_roles("admin", "operator"))])
async def add_maintenance_log(
    id: int,
    data: MaintenanceLogCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    d = (await db.execute(select(SensorDevice).where(SensorDevice.id == id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Not found")

    log = MaintenanceLog(
        device_id=id,
        type=data.type,
        notes=data.notes,
        performed_by_user_id=user.id,
        performed_at=data.performed_at,
        next_due_at=data.next_due_at,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    from app.models.models import User
    performer = (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    return MaintenanceLogOut(
        id=log.id,
        device_id=log.device_id,
        type=log.type,
        notes=log.notes,
        performed_by_user_id=log.performed_by_user_id,
        performed_by_name=performer.name if performer else None,
        performed_at=log.performed_at,
        next_due_at=log.next_due_at,
        created_at=log.created_at,
    )
```

- [ ] **Step 5: Append maintenance delete endpoint**

```python
@router.delete("/{id}/maintenance/{log_id}",
               dependencies=[Depends(require_roles("admin", "operator"))])
async def delete_maintenance_log(
    id: int,
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    log = (await db.execute(
        select(MaintenanceLog).where(
            MaintenanceLog.id == log_id,
            MaintenanceLog.device_id == id,
        )
    )).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Log not found")
    await db.delete(log)
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 6: Verify**

```bash
cd sparing_api && python -c "from app.api.routers.devices import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add sparing_api/app/api/routers/devices.py
git commit -m "feat: add health and maintenance log endpoints to devices router"
```

---

## Task 4: Frontend — add maintenance API methods to useApi.js

**Files:**
- Modify: `sparing_front/resources/js/Composables/useApi.js`

- [ ] **Step 1: Add 4 new methods**

Read the file. Inside `useApi()`, after the site device-key methods and before `return {`, add:

```javascript
  // Device health & maintenance
  const getDeviceHealth = (deviceId) => request('GET', `/devices/${deviceId}/health`);
  const getMaintenanceLogs = (deviceId) => request('GET', `/devices/${deviceId}/maintenance`);
  const addMaintenanceLog = (deviceId, data) => request('POST', `/devices/${deviceId}/maintenance`, data);
  const deleteMaintenanceLog = (deviceId, logId) => request('DELETE', `/devices/${deviceId}/maintenance/${logId}`);
```

Add to return object:
```javascript
    // Device Health & Maintenance
    getDeviceHealth,
    getMaintenanceLogs,
    addMaintenanceLog,
    deleteMaintenanceLog,
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Composables/useApi.js
git commit -m "feat: add device health and maintenance API methods to useApi"
```

---

## Task 5: Frontend — enhanced device cards + maintenance modal

**Files:**
- Modify: `sparing_front/resources/js/Pages/Devices/Index.vue`

Read the full file before making changes.

- [ ] **Step 1: Add new useApi methods to destructuring**

Find the `useApi()` destructuring line:
```javascript
const { getSites, getDevices, createDevice, updateDevice, deleteDevice, getSiteStats } = useApi();
```
Replace with:
```javascript
const { getSites, getDevices, createDevice, updateDevice, deleteDevice, getSiteStats, getDeviceHealth, getMaintenanceLogs, addMaintenanceLog, deleteMaintenanceLog } = useApi();
```

- [ ] **Step 2: Add health state and maintenance state**

After the `deviceStats` ref, add:

```javascript
// Device health data keyed by device id
const deviceHealth = ref({});

// Maintenance modal state
const maintenanceDevice = ref(null);   // device being viewed in maintenance modal
const maintenanceModalTab = ref('info'); // 'info' | 'log'
const maintenanceLogs = ref([]);
const loadingLogs = ref(false);
const addingLog = ref(false);
const newLog = ref({
  type: 'calibration',
  notes: '',
  performed_at: new Date().toISOString().slice(0, 16),
  next_due_at: '',
});
const showAddLogForm = ref(false);

const LOG_TYPES = [
  { key: 'calibration', label: 'Kalibrasi', color: 'emerald' },
  { key: 'repair',      label: 'Perbaikan', color: 'red' },
  { key: 'inspection',  label: 'Inspeksi',  color: 'blue' },
  { key: 'note',        label: 'Catatan',   color: 'slate' },
];

const getLogTypeLabel = (type) => LOG_TYPES.find(t => t.key === type)?.label || type;
const getLogTypeColor = (type) => LOG_TYPES.find(t => t.key === type)?.color || 'slate';
```

- [ ] **Step 3: Add health fetch function and maintenance functions**

After the `loadDevices` function, add:

```javascript
const loadHealthForDevices = async (deviceList) => {
  for (const device of deviceList) {
    try {
      const health = await getDeviceHealth(device.id);
      deviceHealth.value = { ...deviceHealth.value, [device.id]: health };
    } catch {
      // silent — health stays unknown
    }
  }
};

const getHealthStatus = (device) => deviceHealth.value[device.id]?.status || 'unknown';

const healthStatusClass = (device) => {
  const s = getHealthStatus(device);
  if (s === 'online')  return 'text-emerald-600';
  if (s === 'warning') return 'text-amber-500';
  if (s === 'offline') return 'text-red-500';
  return 'text-slate-400';
};

const healthDotClass = (device) => {
  const s = getHealthStatus(device);
  if (s === 'online')  return 'bg-emerald-500 animate-pulse';
  if (s === 'warning') return 'bg-amber-400';
  if (s === 'offline') return 'bg-red-500';
  return 'bg-slate-300';
};

const healthLabel = (device) => {
  const h = deviceHealth.value[device.id];
  const s = getHealthStatus(device);
  if (s === 'unknown') return 'Belum ada data';
  if (!h?.last_seen) return 'Tidak diketahui';
  return getRelativeTime(h.last_seen);
};

const openMaintenanceModal = async (device) => {
  maintenanceDevice.value = device;
  maintenanceModalTab.value = 'info';
  showAddLogForm.value = false;
  newLog.value = { type: 'calibration', notes: '', performed_at: new Date().toISOString().slice(0, 16), next_due_at: '' };
  await loadMaintenanceLogs(device.id);
};

const loadMaintenanceLogs = async (deviceId) => {
  loadingLogs.value = true;
  try {
    const res = await getMaintenanceLogs(deviceId);
    maintenanceLogs.value = Array.isArray(res) ? res : [];
  } catch {
    maintenanceLogs.value = [];
  } finally {
    loadingLogs.value = false;
  }
};

const submitLog = async () => {
  if (!maintenanceDevice.value) return;
  addingLog.value = true;
  try {
    await addMaintenanceLog(maintenanceDevice.value.id, {
      type: newLog.value.type,
      notes: newLog.value.notes || null,
      performed_at: new Date(newLog.value.performed_at).toISOString(),
      next_due_at: newLog.value.next_due_at ? new Date(newLog.value.next_due_at).toISOString() : null,
    });
    await loadMaintenanceLogs(maintenanceDevice.value.id);
    showAddLogForm.value = false;
    newLog.value = { type: 'calibration', notes: '', performed_at: new Date().toISOString().slice(0, 16), next_due_at: '' };
    toast.success('Log berhasil ditambahkan');
  } catch {
    toast.error('Gagal menyimpan log');
  } finally {
    addingLog.value = false;
  }
};

const removeLog = async (logId) => {
  if (!maintenanceDevice.value) return;
  const ok = await confirm('Hapus catatan ini?');
  if (!ok) return;
  try {
    await deleteMaintenanceLog(maintenanceDevice.value.id, logId);
    maintenanceLogs.value = maintenanceLogs.value.filter(l => l.id !== logId);
    toast.success('Log dihapus');
  } catch {
    toast.error('Gagal menghapus log');
  }
};

const closeMaintenanceModal = () => {
  maintenanceDevice.value = null;
  maintenanceLogs.value = [];
  showAddLogForm.value = false;
};
```

- [ ] **Step 4: Call loadHealthForDevices after loading devices**

Find the `loadDevices` function. It ends with something like `devices.value = ...`. After that line, add:

```javascript
    if (devices.value.length > 0) {
      loadHealthForDevices(devices.value);
    }
```

(This is a fire-and-forget — health loads in background, cards update when data arrives.)

- [ ] **Step 5: Update device cards to show health status**

In the device card template, find the connection status row:
```html
              <div class="flex items-center gap-2">
                <i class="fas fa-circle w-3.5 text-center text-[8px]" :class="getLastSeenColorClass(device)"></i>
                <span :class="getLastSeenColorClass(device)">{{ getConnectionStatus(device) }}</span>
              </div>
```

Replace it with:
```html
              <!-- Health status (from API) -->
              <div class="flex items-center gap-2 text-xs">
                <span class="w-2 h-2 rounded-full shrink-0" :class="healthDotClass(device)"></span>
                <span :class="healthStatusClass(device)" class="capitalize">
                  {{ getHealthStatus(device) !== 'unknown' ? getHealthStatus(device) : 'Tidak diketahui' }}
                </span>
              </div>
              <!-- Last data time -->
              <div v-if="deviceHealth[device.id]" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-clock w-3.5 text-center text-primary/60"></i>
                <span>{{ healthLabel(device) }}</span>
              </div>
              <!-- Data count -->
              <div v-if="deviceHealth[device.id]" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-database w-3.5 text-center text-primary/60"></i>
                <span class="font-mono">{{ deviceHealth[device.id].data_count_24h }} data/24j</span>
              </div>
              <!-- Last calibration -->
              <div v-if="deviceHealth[device.id]?.last_calibration_at" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-tools w-3.5 text-center text-primary/60"></i>
                <span>Kalibrasi: {{ new Date(deviceHealth[device.id].last_calibration_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) }}</span>
              </div>
              <!-- Next calibration due -->
              <div v-if="deviceHealth[device.id]?.next_calibration_at" class="flex items-center gap-2 text-xs"
                :class="new Date(deviceHealth[device.id].next_calibration_at) < new Date() ? 'text-red-500' : new Date(deviceHealth[device.id].next_calibration_at) < new Date(Date.now() + 30*24*60*60*1000) ? 'text-amber-500' : 'text-slate-500'"
              >
                <i class="fas fa-calendar-check w-3.5 text-center"></i>
                <span>Berikutnya: {{ new Date(deviceHealth[device.id].next_calibration_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) }}</span>
              </div>
```

- [ ] **Step 6: Update "Detail" button to open maintenance modal**

In the device card actions, find:
```html
              <button @click="viewDeviceDetail(device)" class="btn-primary flex-1 text-xs py-2">
                <i class="fas fa-info-circle mr-1.5"></i>Detail
              </button>
```

Replace with:
```html
              <button @click="openMaintenanceModal(device)" class="btn-primary flex-1 text-xs py-2">
                <i class="fas fa-clipboard-list mr-1.5"></i>Log
              </button>
```

- [ ] **Step 7: Add maintenance modal to template**

After the closing `</div>` of the Add/Edit Device Modal section (and before the outer `</div></AppLayout></template>`), add:

```html
      <!-- Maintenance / Detail Modal -->
      <div
        v-if="maintenanceDevice"
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeMaintenanceModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
          <!-- Modal header -->
          <div class="flex justify-between items-center px-6 py-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <i class="fas fa-microchip text-emerald-600 text-xs"></i>
              </div>
              <div>
                <h3 class="font-bold text-slate-800">{{ maintenanceDevice.name }}</h3>
                <p class="text-xs text-slate-400 font-mono">{{ maintenanceDevice.model || '—' }} · SN {{ maintenanceDevice.serial_no || '—' }}</p>
              </div>
            </div>
            <button @click="closeMaintenanceModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-slate-100 px-6">
            <button
              @click="maintenanceModalTab = 'info'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="maintenanceModalTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Info
            </button>
            <button
              @click="maintenanceModalTab = 'log'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="maintenanceModalTab === 'log' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Log Perawatan
              <span v-if="maintenanceLogs.length" class="ml-1 text-xs font-mono text-slate-400">({{ maintenanceLogs.length }})</span>
            </button>
          </div>

          <!-- Info Tab -->
          <div v-if="maintenanceModalTab === 'info'" class="p-6 space-y-4">
            <!-- Health summary -->
            <div v-if="deviceHealth[maintenanceDevice.id]" class="grid grid-cols-3 gap-3">
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Status</div>
                <div class="flex items-center justify-center gap-1.5">
                  <span class="w-2 h-2 rounded-full" :class="healthDotClass(maintenanceDevice)"></span>
                  <span class="text-sm font-bold capitalize" :class="healthStatusClass(maintenanceDevice)">
                    {{ getHealthStatus(maintenanceDevice) }}
                  </span>
                </div>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Data 24j</div>
                <div class="text-lg font-bold font-mono text-slate-800">{{ deviceHealth[maintenanceDevice.id].data_count_24h }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Data 7 Hari</div>
                <div class="text-lg font-bold font-mono text-slate-800">{{ deviceHealth[maintenanceDevice.id].data_count_7d }}</div>
              </div>
            </div>

            <!-- Device details -->
            <div class="space-y-2 text-sm">
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Nama</span>
                <span class="font-semibold text-slate-800">{{ maintenanceDevice.name }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Model</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.model || '—' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Serial Number</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.serial_no || '—' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Modbus Address</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.modbus_addr }}</span>
              </div>
              <div class="flex justify-between py-2">
                <span class="text-slate-500">Status</span>
                <span :class="maintenanceDevice.is_active ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                  {{ maintenanceDevice.is_active ? 'Aktif' : 'Nonaktif' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Log Perawatan Tab -->
          <div v-if="maintenanceModalTab === 'log'" class="p-6">
            <!-- Loading -->
            <div v-if="loadingLogs" class="text-center text-sm text-slate-400 py-4">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
            </div>

            <div v-else>
              <!-- Log timeline -->
              <div v-if="!maintenanceLogs.length && !showAddLogForm" class="text-center text-sm text-slate-400 py-4">
                Belum ada log perawatan.
              </div>

              <div v-else class="space-y-3 mb-4">
                <div
                  v-for="log in maintenanceLogs"
                  :key="log.id"
                  class="flex gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50"
                >
                  <!-- Type badge -->
                  <div class="shrink-0 mt-0.5">
                    <span :class="[
                      'text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide',
                      `bg-${getLogTypeColor(log.type)}-50 text-${getLogTypeColor(log.type)}-700 border border-${getLogTypeColor(log.type)}-100`
                    ]">
                      {{ getLogTypeLabel(log.type) }}
                    </span>
                  </div>
                  <!-- Content -->
                  <div class="flex-1 min-w-0">
                    <div class="text-xs text-slate-500 font-mono">{{ new Date(log.performed_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) }}</div>
                    <div v-if="log.notes" class="text-sm text-slate-700 mt-0.5">{{ log.notes }}</div>
                    <div v-if="log.next_due_at" class="text-xs text-amber-600 mt-1">
                      <i class="fas fa-calendar-alt mr-1"></i>
                      Jadwal berikutnya: {{ new Date(log.next_due_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) }}
                    </div>
                    <div v-if="log.performed_by_name" class="text-xs text-slate-400 mt-1">
                      <i class="fas fa-user mr-1"></i>{{ log.performed_by_name }}
                    </div>
                  </div>
                  <!-- Delete -->
                  <button
                    v-if="canManageDevices"
                    @click="removeLog(log.id)"
                    class="shrink-0 text-slate-300 hover:text-red-400 transition-colors"
                  >
                    <i class="fas fa-times text-xs"></i>
                  </button>
                </div>
              </div>

              <!-- Add form -->
              <div v-if="showAddLogForm && canManageDevices" class="p-4 rounded-lg border border-primary/20 bg-primary/5 space-y-3 mb-3">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tipe</label>
                    <select v-model="newLog.type" class="form-input text-sm">
                      <option v-for="t in LOG_TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tanggal Pelaksanaan</label>
                    <input v-model="newLog.performed_at" type="datetime-local" class="form-input text-sm" />
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Catatan</label>
                  <textarea v-model="newLog.notes" rows="2" class="form-input text-sm resize-none" placeholder="Opsional..."></textarea>
                </div>
                <div v-if="newLog.type === 'calibration'">
                  <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Jadwal Kalibrasi Berikutnya</label>
                  <input v-model="newLog.next_due_at" type="date" class="form-input text-sm" />
                </div>
                <div class="flex gap-2">
                  <button @click="submitLog" :disabled="addingLog" class="btn-primary text-sm disabled:opacity-50">
                    <i :class="addingLog ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="mr-1.5 text-xs"></i>Simpan
                  </button>
                  <button @click="showAddLogForm = false" class="btn-secondary text-sm">Batal</button>
                </div>
              </div>

              <!-- Add button -->
              <button
                v-if="!showAddLogForm && canManageDevices"
                @click="showAddLogForm = true"
                class="btn-secondary text-sm flex items-center gap-1.5"
              >
                <i class="fas fa-plus text-xs"></i>Tambah Catatan
              </button>
            </div>
          </div>
        </div>
      </div>
```

- [ ] **Step 8: Commit**

```bash
git add sparing_front/resources/js/Pages/Devices/Index.vue
git commit -m "feat: enhanced device cards with health status and maintenance log modal"
```

---

## Post-Implementation Checklist

- [ ] Run migration on server: `cd /opt/sparing/api && sudo -u www-data /opt/sparing/api/.venv/bin/alembic upgrade head`
- [ ] `GET /devices/{id}/health` returns `{ status, last_seen, data_count_24h, data_count_7d }`
- [ ] `POST /devices/{id}/maintenance` creates a log, returns it with `performed_by_name`
- [ ] Device cards show colored status dot (green/amber/red)
- [ ] "Log" button opens maintenance modal → Info tab shows health summary
- [ ] Log Perawatan tab shows timeline → "Tambah Catatan" adds entry → trash icon deletes
- [ ] Kalibrasi type shows "Jadwal berikutnya" field
