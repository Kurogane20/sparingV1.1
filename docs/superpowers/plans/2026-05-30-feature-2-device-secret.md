# Feature 2: API Key Management (Per-Site Device Secret) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each monitoring site its own JWT signing secret so IoT devices can be onboarded and revoked per-site without changing a global hardcoded secret.

**Architecture:** Add `device_secret` and `last_ingest_at` columns to the `sites` table. `GET /api/get-key?uid=SITE_UID` returns the site-specific secret for new devices; without the `uid` param it returns the global secret for backward compatibility. `POST /api/post-data` performs a two-step JWT decode: first without verification to read `uid`, then with the site's secret (falling back to global if not set). A new admin-only `POST /sites/{uid}/rotate-secret` regenerates the secret. The frontend adds a "Device Key" tab (admin only) inside the site edit modal.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + PyJWT · Vue 3 Composition API + TailwindCSS

---

## File Map

### Backend — Create
- `sparing_api/alembic/versions/0003_add_site_device_secret.py` — migration: add `device_secret` + `last_ingest_at` to `sites`, backfill existing rows
- `sparing_api/app/tests/test_device_secret.py` — unit tests for secret generation + JWT verification logic

### Backend — Modify
- `sparing_api/app/core/config.py` — add `getdata_secret` setting (replaces hardcoded `"sparing"`)
- `sparing_api/app/models/models.py` — add `device_secret`, `last_ingest_at` to `Site` model
- `sparing_api/app/schemas/site.py` — add `SiteDeviceKeyOut` schema
- `sparing_api/app/api/routers/sites.py` — auto-generate secret on `create_site`; add `GET /{uid}/device-key` and `POST /{uid}/rotate-secret` endpoints
- `sparing_api/app/api/routers/getdata.py` — use config setting; update `get_key` with uid param; update `post_data` to two-step JWT + update `last_ingest_at`

### Frontend — Modify
- `sparing_front/resources/js/Composables/useApi.js` — add `getSiteDeviceKey`, `rotateSiteSecret`
- `sparing_front/resources/js/Pages/Sites/Index.vue` — add "Device Key" tab inside the edit modal (admin only)

---

## Task 1: Promote GETDATA_SECRET to config setting

**Files:**
- Modify: `sparing_api/app/core/config.py`
- Modify: `sparing_api/app/api/routers/getdata.py`

- [ ] **Step 1: Add getdata_secret to Settings**

In `sparing_api/app/core/config.py`, add inside the `Settings` class after `smtp_tls`:
```python
    # Secret for legacy IoT get-key/post-data endpoints (backward compat default: "sparing")
    getdata_secret: str = "sparing"
```

- [ ] **Step 2: Update getdata.py to use config**

Read the file. Replace the hardcoded constant at the top:
```python
# Dedicated secret for getdata API (separate from main JWT auth)
GETDATA_SECRET = "sparing"
```
With:
```python
from app.core.config import settings as _settings

def _global_secret() -> str:
    return _settings.getdata_secret
```

Replace all uses of `GETDATA_SECRET` with `_global_secret()`:
- In `get_key`: `return _global_secret()`
- In `post_data` JWT decode: `decode = jwt.decode(token, _global_secret(), algorithms=["HS256"])`

- [ ] **Step 3: Verify import**

```bash
cd sparing_api && python -c "from app.api.routers.getdata import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add sparing_api/app/core/config.py sparing_api/app/api/routers/getdata.py
git commit -m "refactor: promote GETDATA_SECRET from hardcoded to config setting"
```

---

## Task 2: Migration — add device_secret and last_ingest_at to sites

**Files:**
- Create: `sparing_api/alembic/versions/0003_add_site_device_secret.py`

- [ ] **Step 1: Create migration file**

Create `sparing_api/alembic/versions/0003_add_site_device_secret.py`:

```python
from alembic import op
import sqlalchemy as sa
import secrets

revision = '0003_add_site_device_secret'
down_revision = '0002_add_alerts'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sites', sa.Column('device_secret', sa.String(64), nullable=True, unique=True))
    op.add_column('sites', sa.Column('last_ingest_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill device_secret for all existing sites
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM sites WHERE device_secret IS NULL")).fetchall()
    for row in rows:
        secret = secrets.token_hex(32)
        conn.execute(
            sa.text("UPDATE sites SET device_secret = :s WHERE id = :id"),
            {"s": secret, "id": row.id}
        )

def downgrade():
    op.drop_column('sites', 'last_ingest_at')
    op.drop_column('sites', 'device_secret')
```

- [ ] **Step 2: Commit migration file**

```bash
git add sparing_api/alembic/versions/0003_add_site_device_secret.py
git commit -m "feat: migration to add device_secret and last_ingest_at to sites table"
```

---

## Task 3: Update Site model and auto-generate secret on create

**Files:**
- Modify: `sparing_api/app/models/models.py`
- Modify: `sparing_api/app/schemas/site.py`
- Modify: `sparing_api/app/api/routers/sites.py`
- Create: `sparing_api/app/tests/test_device_secret.py`

- [ ] **Step 1: Write failing tests**

Create `sparing_api/app/tests/test_device_secret.py`:

```python
import secrets as _secrets
from app.utils.device_secret import generate_device_secret, mask_secret

def test_generate_device_secret_length():
    s = generate_device_secret()
    assert len(s) == 64

def test_generate_device_secret_hex():
    s = generate_device_secret()
    int(s, 16)  # raises ValueError if not valid hex

def test_generate_device_secret_unique():
    a = generate_device_secret()
    b = generate_device_secret()
    assert a != b

def test_mask_secret_short():
    assert mask_secret("abcdef") == "abcd••••"

def test_mask_secret_normal():
    s = "a" * 64
    result = mask_secret(s)
    assert result.startswith("aaaa")
    assert "•" in result
    assert result.endswith("••••")

def test_mask_secret_empty():
    assert mask_secret("") == "••••••••"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd sparing_api && python -m pytest app/tests/test_device_secret.py -v
```

Expected: `ImportError` — `app.utils.device_secret` doesn't exist yet.

- [ ] **Step 3: Create device_secret utility**

Create `sparing_api/app/utils/device_secret.py`:

```python
import secrets

def generate_device_secret() -> str:
    """Generate a 64-character hex secret for a site's IoT devices."""
    return secrets.token_hex(32)

def mask_secret(secret: str) -> str:
    """Return first 4 chars + bullets, e.g. 'a1b2••••••••'."""
    if not secret:
        return "••••••••"
    visible = secret[:4]
    return visible + "••••••••"
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd sparing_api && python -m pytest app/tests/test_device_secret.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Add device_secret and last_ingest_at to Site model**

Read `sparing_api/app/models/models.py`. In the `Site` class, after the `is_active` field, add:

```python
    device_secret: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 6: Add SiteDeviceKeyOut schema**

Read `sparing_api/app/schemas/site.py`. Append at the end of the file:

```python
class SiteDeviceKeyOut(BaseModel):
    uid: str
    name: str
    device_secret: str
    last_ingest_at: datetime | None = None

    model_config = {"from_attributes": True}
```

Also add `from datetime import datetime` at the top if not already present.

- [ ] **Step 7: Auto-generate secret on create_site**

Read `sparing_api/app/api/routers/sites.py`. Add import at top:

```python
from app.utils.device_secret import generate_device_secret
```

In `create_site`, replace:
```python
    s = Site(**data.model_dump())
```
With:
```python
    s = Site(**data.model_dump(), device_secret=generate_device_secret())
```

- [ ] **Step 8: Verify imports**

```bash
cd sparing_api && python -c "from app.models.models import Site; from app.schemas.site import SiteDeviceKeyOut; from app.api.routers.sites import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add sparing_api/app/utils/device_secret.py sparing_api/app/tests/test_device_secret.py sparing_api/app/models/models.py sparing_api/app/schemas/site.py sparing_api/app/api/routers/sites.py
git commit -m "feat: add device_secret utility, Site model fields, auto-generate on site creation"
```

---

## Task 4: Add device-key endpoints to sites router

**Files:**
- Modify: `sparing_api/app/api/routers/sites.py`

- [ ] **Step 1: Add GET /{uid}/device-key endpoint**

Read `sparing_api/app/api/routers/sites.py`. Add these imports at the top (after existing imports):

```python
from app.schemas.site import SiteCreate, SiteUpdate, SiteOut, SiteDeviceKeyOut
from app.utils.device_secret import generate_device_secret
from datetime import datetime, timezone
```

Append the following two endpoints at the bottom of `sites.py`:

```python
@router.get("/{uid}/device-key", response_model=SiteDeviceKeyOut,
            dependencies=[Depends(require_roles("admin"))])
async def get_site_device_key(uid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid == uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Site not found")
    if not s.device_secret:
        s.device_secret = generate_device_secret()
        await db.commit()
        await db.refresh(s)
    return SiteDeviceKeyOut(
        uid=s.uid,
        name=s.name,
        device_secret=s.device_secret,
        last_ingest_at=s.last_ingest_at,
    )


@router.post("/{uid}/rotate-secret", response_model=SiteDeviceKeyOut,
             dependencies=[Depends(require_roles("admin"))])
async def rotate_site_secret(uid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid == uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Site not found")
    s.device_secret = generate_device_secret()
    await db.commit()
    await db.refresh(s)
    return SiteDeviceKeyOut(
        uid=s.uid,
        name=s.name,
        device_secret=s.device_secret,
        last_ingest_at=s.last_ingest_at,
    )
```

- [ ] **Step 2: Verify imports and router**

```bash
cd sparing_api && python -c "from app.api.routers.sites import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/api/routers/sites.py
git commit -m "feat: add GET/POST device-key endpoints to sites router"
```

---

## Task 5: Update get-key and post-data for per-site secrets

**Files:**
- Modify: `sparing_api/app/api/routers/getdata.py`

- [ ] **Step 1: Update get_key to accept optional uid param**

Read `sparing_api/app/api/routers/getdata.py`. Replace the `get_key` endpoint:

```python
@router.get("/api/get-key", response_class=PlainTextResponse)
async def get_key():
    return _global_secret()
```

With:

```python
@router.get("/api/get-key", response_class=PlainTextResponse)
async def get_key(uid: str | None = None, db: AsyncSession = Depends(get_db)):
    if not uid:
        return _global_secret()
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    return site.device_secret or _global_secret()
```

- [ ] **Step 2: Update post_data for two-step JWT and last_ingest_at**

Still in `getdata.py`, replace the JWT decoding section at the start of `post_data`.

Current code (lines ~30-47):
```python
    try:
        decode = jwt.decode(token, _global_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")
    
    uid = decode.get("uid")
    device_id_str = decode.get("device_id")
    data = decode.get("data")
    
    if not uid or not isinstance(data, list) or len(data) == 0 or len(data) > 30:
        raise HTTPException(400, "Invalid data format")
    
    # Lookup site by uid
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site: 
        raise HTTPException(401, "Invalid UID")
```

Replace with:

```python
    # Step 1: Decode without verification to read uid (safe — we verify below)
    try:
        unverified = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    uid = unverified.get("uid")
    if not uid:
        raise HTTPException(400, "Invalid data format")

    # Step 2: Look up site and determine correct signing secret
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(401, "Invalid UID")

    signing_secret = site.device_secret or _global_secret()

    # Step 3: Verify JWT with the site's secret (raises on invalid/expired)
    try:
        decode = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    device_id_str = decode.get("device_id")
    data = decode.get("data")

    if not isinstance(data, list) or len(data) == 0 or len(data) > 30:
        raise HTTPException(400, "Invalid data format")
```

- [ ] **Step 3: Update last_ingest_at after successful insert**

Still in `post_data`, find the block after `await db.commit()` that follows `await db.execute(insert(SensorData), rows)`. Add the `last_ingest_at` update:

```python
    if rows:
        await db.execute(insert(SensorData), rows)
        await db.commit()
        # Update site's last ingest timestamp
        site.last_ingest_at = datetime.now(timezone.utc)
        await db.commit()
```

- [ ] **Step 4: Verify file imports cleanly**

```bash
cd sparing_api && python -c "from app.api.routers.getdata import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/getdata.py
git commit -m "feat: per-site JWT secret in get-key/post-data with last_ingest_at tracking"
```

---

## Task 6: Frontend — add device-key API methods to useApi.js

**Files:**
- Modify: `sparing_front/resources/js/Composables/useApi.js`

- [ ] **Step 1: Add device-key methods**

Read the file. Inside the `useApi()` function body, after the alert methods block and before the `return {` statement, add:

```javascript
  // Site device-key endpoints (admin only)
  const getSiteDeviceKey = (siteUid) => request('GET', `/sites/${siteUid}/device-key`);
  const rotateSiteSecret = (siteUid) => request('POST', `/sites/${siteUid}/rotate-secret`);
```

Add to the `return` object:
```javascript
    // Site Device Key
    getSiteDeviceKey,
    rotateSiteSecret,
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Composables/useApi.js
git commit -m "feat: add getSiteDeviceKey and rotateSiteSecret to useApi composable"
```

---

## Task 7: Frontend — Device Key tab in Sites edit modal

**Files:**
- Modify: `sparing_front/resources/js/Pages/Sites/Index.vue`

- [ ] **Step 1: Add Device Key state and functions to script setup**

Read the full file first. In the `<script setup>` section:

Find the Vue import line (currently `import { ref, onMounted } from 'vue';`) and add `computed`:
```javascript
import { ref, computed, onMounted } from 'vue';
```

Add to the `useApi()` destructuring (alongside existing methods):
```javascript
const { getSites, createSite, updateSite, deleteSite, getAlertRules, updateAlertRule, createAlertRule, getSiteDeviceKey, rotateSiteSecret } = useApi();
```

After the `showAddRule` / `AVAILABLE_FIELDS` block, add:
```javascript
const deviceKey = ref(null);          // { device_secret, last_ingest_at, name, uid }
const loadingKey = ref(false);
const showSecret = ref(false);
const rotatingSecret = ref(false);

const maskedSecret = computed(() => {
  if (!deviceKey.value?.device_secret) return '••••••••••••';
  const s = deviceKey.value.device_secret;
  return s.slice(0, 8) + '••••••••••••••••••••••••';
});

const loadDeviceKey = async (siteUid) => {
  loadingKey.value = true;
  showSecret.value = false;
  try {
    deviceKey.value = await getSiteDeviceKey(siteUid);
  } catch {
    deviceKey.value = null;
  } finally {
    loadingKey.value = false;
  }
};

const handleRotateSecret = async () => {
  if (!editingSite.value) return;
  const confirmed = await confirm(
    'Perangkat yang menggunakan secret lama akan berhenti mengirim data sampai diperbarui. Lanjutkan?'
  );
  if (!confirmed) return;
  rotatingSecret.value = true;
  try {
    deviceKey.value = await rotateSiteSecret(editingSite.value.uid);
    showSecret.value = true;
    toast.success('Secret berhasil diperbarui');
  } catch {
    toast.error('Gagal memperbarui secret');
  } finally {
    rotatingSecret.value = false;
  }
};

const copySecret = async () => {
  if (!deviceKey.value?.device_secret) return;
  try {
    await navigator.clipboard.writeText(deviceKey.value.device_secret);
    toast.success('Secret disalin ke clipboard');
  } catch {
    toast.error('Gagal menyalin');
  }
};
```

- [ ] **Step 2: Load device key when editing a site**

Update the `editSite` function to also load the device key:
```javascript
const editSite = (site) => {
  editingSite.value = site;
  siteForm.value = { ...site };
  modalTab.value = 'info';
  loadAlertRules(site.uid);
  if (isAdmin.value) loadDeviceKey(site.uid);
};
```

Update `closeModal` to reset device key state:
```javascript
const closeModal = () => {
  showAddModal.value = false;
  editingSite.value = null;
  modalTab.value = 'info';
  showAddRule.value = false;
  deviceKey.value = null;
  showSecret.value = false;
  siteForm.value = { uid: '', name: '', company_name: '', lat: 0, lon: 0, is_active: true };
};
```

- [ ] **Step 3: Add Device Key tab button**

In the tabs `<div v-if="editingSite" class="flex border-b ...">`, add a third tab button after the Baku Mutu button:

```html
            <button
              v-if="isAdmin"
              @click="modalTab = 'device-key'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'device-key' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Device Key
            </button>
```

- [ ] **Step 4: Add Device Key tab panel**

After the closing `</div>` of the Baku Mutu panel (and before the modal white box closing `</div>`), add:

```html
          <!-- Device Key Tab -->
          <div v-if="editingSite && modalTab === 'device-key'" class="p-6">
            <div v-if="loadingKey" class="text-sm text-slate-400 text-center py-6">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
            </div>
            <div v-else-if="!deviceKey" class="text-sm text-slate-400 text-center py-6">
              Gagal memuat device key.
            </div>
            <div v-else class="space-y-5">
              <!-- Secret display -->
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                  Secret Perangkat
                </label>
                <div class="flex items-center gap-2">
                  <div class="flex-1 font-mono text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-slate-800 truncate">
                    {{ showSecret ? deviceKey.device_secret : maskedSecret }}
                  </div>
                  <button
                    @click="showSecret = !showSecret"
                    class="px-3 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors shrink-0"
                  >
                    {{ showSecret ? 'Sembunyikan' : 'Tampilkan' }}
                  </button>
                  <button
                    @click="copySecret"
                    class="px-3 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors shrink-0"
                  >
                    <i class="fas fa-copy mr-1"></i>Copy
                  </button>
                </div>
              </div>

              <!-- Last ingest -->
              <div class="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <i class="fas fa-satellite-dish text-emerald-600 text-xs"></i>
                </div>
                <div>
                  <div class="text-xs text-slate-500">Terakhir menerima data</div>
                  <div class="text-sm font-semibold text-slate-800 font-mono">
                    {{ deviceKey.last_ingest_at ? getRelativeTime(deviceKey.last_ingest_at) : 'Belum pernah' }}
                  </div>
                </div>
              </div>

              <!-- Regenerate -->
              <div class="pt-3 border-t border-slate-100">
                <p class="text-xs text-slate-400 mb-3">
                  Regenerate akan membuat secret baru. Perangkat lama tidak bisa kirim data sampai secret-nya diperbarui.
                </p>
                <button
                  @click="handleRotateSecret"
                  :disabled="rotatingSecret"
                  class="px-4 py-2 rounded-lg text-sm font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  <i class="fas fa-sync-alt mr-1.5" :class="rotatingSecret ? 'fa-spin' : ''"></i>
                  Regenerate Secret
                </button>
              </div>

              <!-- Endpoint hint -->
              <div class="p-3 rounded-lg bg-slate-900 text-xs font-mono text-emerald-400">
                GET /api/get-key?uid={{ deviceKey.uid }}
              </div>
            </div>
          </div>
```

- [ ] **Step 5: Add getRelativeTime import**

In the script setup imports from helpers:
```javascript
import { formatDate, formatNumber, getSensorName, getSensorUnit, getThresholdStatus, downloadCSV, getRelativeTime } from '@/Utils/helpers';
```

(Add `getRelativeTime` to the existing destructuring if it isn't already there.)

- [ ] **Step 6: Commit**

```bash
git add sparing_front/resources/js/Pages/Sites/Index.vue
git commit -m "feat: add Device Key tab to Sites modal with show/copy/regenerate"
```

---

## Post-Implementation Checklist

- [ ] Run migration on server: `cd /opt/sparing/api && sudo -u www-data /opt/sparing/api/.venv/bin/alembic upgrade head`
- [ ] Verify all existing sites have `device_secret` populated after migration
- [ ] Test `GET /api/get-key` (no param) → returns global secret (backward compat)
- [ ] Test `GET /api/get-key?uid=SITE_UID` → returns site-specific 64-char hex secret
- [ ] Test `POST /api/post-data` with token signed using site secret → succeeds
- [ ] Test `POST /api/post-data` with old global secret → still succeeds (for old devices)
- [ ] Test `POST /sites/{uid}/rotate-secret` → returns new secret, old JWT tokens now invalid
- [ ] Open Sites page → edit a site → "Device Key" tab visible (admin only) → shows masked secret → Tampilkan shows full → Copy works
