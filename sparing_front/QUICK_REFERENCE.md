# 🚀 SPARING - Quick Reference Card

## 📌 URL Halaman

| Halaman | URL | Deskripsi |
|---------|-----|-----------|
| **Login** | `/login` | Halaman masuk sistem |
| **Dashboard** | `/dashboard` | Monitoring real-time sensor pH, TSS, COD, NH3-N |
| **Analisis** | `/analytics` | Statistik & compliance baku mutu |
| **Riwayat Data** | `/history` | Data historis dengan filter & export CSV |
| **Lokasi** | `/sites` | Manajemen lokasi monitoring |
| **Perangkat** | `/devices` | Manajemen perangkat IoT |
| **Pengguna** | `/users` | Manajemen user (admin only) |
| **Pengaturan** | `/settings` | Konfigurasi sistem & profil |

---

## 🎯 Sensor Parameters

### Parameter Air Limbah (Dashboard)
1. **pH** - Keasaman air (0-14)
2. **TSS** - Total Suspended Solids (mg/L)
3. **COD** - Chemical Oxygen Demand (mg/L)
4. **NH3-N** - Amonia Nitrogen (mg/L)

### Parameter Tambahan
5. **Debit** - Aliran air (L/min)
6. **Voltage** - Tegangan listrik (V)
7. **Current** - Arus listrik (A)
8. **Temperature** - Suhu (°C)

---

## 📊 Baku Mutu (Standar Compliance)

| Parameter | Baku Mutu | Status |
|-----------|-----------|--------|
| pH | 6.0 - 9.0 | Normal jika dalam range |
| TSS | < 100 mg/L | Normal jika di bawah |
| COD | < 200 mg/L | Normal jika di bawah |
| NH3-N | < 10 mg/L | Normal jika di bawah |

**Color Coding**:
- 🟢 Green (≥90%): Sesuai baku mutu
- 🟡 Yellow (70-89%): Mendekati batas
- 🔴 Red (<70%): Melampaui batas

---

## 👤 User Roles

| Role | Dashboard | Analisis | History | Sites | Devices | Users | Settings |
|------|-----------|----------|---------|-------|---------|-------|----------|
| **Viewer** | View | View | View | View | View | ❌ | View |
| **Operator** | View | View | View | Edit | Edit | ❌ | View |
| **Admin** | Full | Full | Full | Full | Full | ✅ | Full |

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Logout | `Ctrl + Shift + L` |
| Refresh Dashboard | `F5` |
| Export CSV (History) | `Ctrl + E` |
| Search | `Ctrl + K` |

---

## 🔧 Admin Tasks

### Tambah User Baru
1. Login sebagai Admin
2. Buka menu **Pengguna**
3. Klik **Tambah Pengguna**
4. Isi: Nama, Email, Password, Role
5. Klik **Tambah**

### Tambah Lokasi Baru
1. Buka menu **Lokasi**
2. Klik **Tambah Lokasi**
3. Isi: UID, Nama, Perusahaan, Koordinat
4. Centang **Lokasi Aktif**
5. Klik **Tambah**

### Tambah Perangkat Baru
1. Buka menu **Perangkat**
2. Pilih lokasi dari dropdown
3. Klik **Tambah Perangkat**
4. Isi: Nama, Model, Serial, Modbus Address
5. Klik **Tambah Perangkat**

---

## 📈 Fitur Analytics

### Filter Data
- **Lokasi**: Pilih site tertentu atau semua
- **Periode**: Harian, Mingguan, Bulanan, Tahunan
- **Tanggal**: Custom date range

### Charts Tersedia
1. **Trend Chart** - Line chart perubahan parameter
2. **Bar Chart** - Perbandingan rata-rata
3. **Compliance Bars** - Visual kepatuhan baku mutu

### Export
- Click **Unduh Laporan PDF** untuk download (coming soon)

---

## 🔄 Auto-Refresh

Dashboard auto-refresh setiap **30 detik** untuk data terbaru.

Untuk menonaktifkan:
1. Buka **Pengaturan**
2. Scroll ke **Pengaturan Sistem**
3. Uncheck **Enable Auto Refresh**

---

## 📱 Responsive Breakpoints

| Device | Width | Layout |
|--------|-------|--------|
| **Mobile** | < 768px | Stacked, hamburger menu |
| **Tablet** | 768px - 1024px | 2 columns |
| **Desktop** | > 1024px | Full grid (4 columns) |

---

## 🐛 Troubleshooting

### "No data" di Dashboard
- **Check**: Pastikan ada minimal 1 site aktif
- **Check**: Pastikan perangkat mengirim data
- **Fix**: Refresh halaman atau clear cache

### Export CSV tidak bekerja
- **Check**: Pastikan ada data yang difilter
- **Check**: Browser support download
- **Fix**: Coba browser lain (Chrome recommended)

### Chart tidak muncul
- **Check**: Console browser (F12) untuk errors
- **Check**: Data tersedia di periode yang dipilih
- **Fix**: Reload page

### User tidak bisa login
- **Check**: Email dan password benar
- **Check**: User status aktif
- **Fix**: Reset password via admin

---

## 📞 Support

**Email**: support@sparing.com
**Phone**: +62 xxx xxxx xxxx
**Documentation**: [README.md](README.md)

---

## 🎓 Training Resources

1. **Video Tutorial**: Coming soon
2. **User Manual**: [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
3. **API Docs**: [API.md](API.md)
4. **Component Reference**: [COMPONENT_API_REFERENCE.md](COMPONENT_API_REFERENCE.md)

---

## 🔑 Default Credentials

**Development Only**:
```
Admin:
  Email: admin@example.com
  Password: Admin#12345

Operator:
  Email: op@example.com
  Password: Op#12345
```

⚠️ **PENTING**: Ganti password default di production!

---

**Quick Start**: `npm run dev` → Open `http://localhost:3000` → Login → Explore! 🚀
