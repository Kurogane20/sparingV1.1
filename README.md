# SPARING - Environmental Monitoring System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Vue.js](https://img.shields.io/badge/Vue.js-3.3-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)

**SPARING** (Sistem Pemantauan Air Lingkungan Industri) adalah dashboard monitoring real-time untuk kualitas air limbah industri. Dibangun dengan Vue.js 3 dan FastAPI.

## Screenshots

<!-- Add screenshots here -->

## Features

- 📊 **Real-time Dashboard** - Monitoring parameter air limbah (pH, TSS, COD, NH3-N)
- 📈 **Analytics** - Visualisasi tren dan analisis kepatuhan baku mutu
- 🔐 **Role-based Access** - Admin, Operator, Viewer dengan izin berbeda
- 📱 **Responsive** - Optimized untuk desktop dan mobile
- 🔄 **API Integration** - RESTful API untuk integrasi sensor IoT

## Tech Stack

### Frontend
- Vue.js 3 + Vite
- TailwindCSS
- Chart.js

### Backend  
- FastAPI (Python 3.11)
- SQLAlchemy (Async)
- MySQL 8.0
- JWT Authentication

## Quick Start

### Development

```bash
# Clone repository
git clone https://github.com/yourusername/sparing.git
cd sparing

# Backend
cd sparing_api
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database settings
uvicorn app.main:app --reload

# Frontend (new terminal)
cd sparing_front
npm install
cp .env.example .env
npm run dev
```

### Docker

```bash
docker-compose up --build
```

## Documentation

- [API Documentation](sparing_api/README.md)
- [Deployment Guide](DEPLOYMENT.md)

## Environment Variables

### Backend (`sparing_api/.env`)
```env
DB_URL=mysql+aiomysql://user:pass@localhost:3306/sparing
JWT_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:5173
```

### Frontend (`sparing_front/.env`)
```env
VITE_API_URL=http://localhost:8000
```

## Default Credentials (Development)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | Admin#123 |
| Operator | op@example.com | Op#12345 |
| Viewer | viewer@example.com | Viewer#123 |

## License

MIT License - see [LICENSE](LICENSE) file.
