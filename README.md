# Laptop Allocation Management System

A professional Laptop Allocation Management System for managing laptop assignments to interns.

**Phase 1:** Project structure, models, API, seed data.
**Phase 2:** Secure JWT authentication, protected routes, professional dashboard layout, laptop & intern management with validation.
**Phase 3:** Complete laptop allocation system — Allocate Laptop page, real-time availability, Active Allocations, Return Laptop, and Cancel Allocation.
**Phase 4:** Professional admin dashboard with KPI cards and Recharts visualizations (auto-updating), Allocation History with search/pagination/filters, and a Reports page with summary statistics and CSV/Excel export.

## Tech Stack

- **Frontend:** React.js + Vite + Tailwind CSS + React Router + Recharts
- **Backend:** Python FastAPI + SQLAlchemy + JWT (python-jose) + bcrypt (passlib)
- **Database:** MySQL / PostgreSQL (with SQLite fallback for local development)

## Project Structure

```
laptop_allocate/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # App configuration & environment settings
│   │   │   ├── database.py     # SQLAlchemy engine, session, Base
│   │   │   └── security.py     # JWT creation/verification, password hashing, auth deps
│   │   ├── models/
│   │   │   ├── user.py         # User model
│   │   │   ├── laptop.py       # Laptop model
│   │   │   ├── intern.py       # Intern model
│   │   │   ├── allocation.py   # Allocation model
│   │   │   └── seed.py         # Admin user seed only (no dummy laptops/interns)
│   │   ├── routes/
│   │   │   ├── auth.py         # Register, Login, Current user
│   │   │   ├── laptops.py      # Laptop CRUD + status/deactivate (protected)
│   │   │   ├── interns.py      # Intern CRUD + search (protected)
│   │   │   ├── allocations.py  # Allocation API endpoints (protected)
│   │   │   ├── dashboard.py    # KPI + chart stats (protected)
│   │   │   └── excel_io.py     # Excel import / export / template (protected)
│   │   └── main.py             # FastAPI app entrypoint
│   ├── scripts/
│   │   ├── mysql_dataset.sql        # MySQL schema + seed dataset
│   │   ├── build_mysql_dataset.py   # Regenerate the dataset from SQLite
│   │   └── load_mysql_dataset.py    # Load the dataset into a MySQL server
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── context/
    │   │   └── AuthContext.jsx # Auth state + token storage
    │   ├── components/
    │   │   ├── Layout.jsx      # Sidebar + topbar responsive layout
    │   │   └── ProtectedRoute.jsx
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── Laptops.jsx     # Add/Edit/Deactivate/Status/Search
    │   │   ├── Interns.jsx     # Add/Edit/Delete/Search
    │   │   └── Allocations.jsx
    │   └── services/
    │       └── api.js          # Axios client + auth interceptor
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

## Authentication

JWT-based authentication. All laptop, intern, and allocation endpoints are protected and require a valid `Bearer` token.

**Default admin user (seeded on first run):**
- Username: `admin`
- Password: `admin123`

## Database Models

### Laptop
- laptop_number (unique), brand, model, serial_number (unique), status, processor, RAM, storage, operating_system
- Status: **FREE, ALLOCATED, MAINTENANCE, INACTIVE**

### Intern
- intern_id (unique), name, email (unique), phone, batch, domain
- Batch: Morning, Afternoon
- Domain: Cloud, Data Analytics, Full Stack, AI & ML, Digital Marketing, UI/UX

### Allocation
- laptop (FK), intern (FK), batch, allocation_date, start_time, end_time, status
- Status: Active, Completed, Cancelled, Returned

### User
- username, email, hashed_password, full_name, role (admin/staff)

## Setup & Installation

### Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env
cp .env.example .env

# Run server
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Access the app at `http://localhost:5173` and sign in with `admin` / `admin123`.

## Configuration

### SQLite (default)

No setup required — the backend creates `backend/laptop_allocation.db` automatically.

### MySQL

```bash
cd backend

# Option A: load the bundled dataset (schema + seed data) with the loader script
python scripts/load_mysql_dataset.py                       # or pass --host/--port/--user/--password/--database

# Option B: load the raw SQL file with the mysql client
mysql -u root -p < scripts/mysql_dataset.sql
```

Then update `DATABASE_URL` in `backend/.env`:

```
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/laptop_allocation
```

Restart the backend. The dataset contains 1 admin user, 20 laptops (with specs), 10 interns, and sample allocations. To (re)generate the dataset file from the current SQLite database, run `python scripts/build_mysql_dataset.py`.

> Note: MySQL has no partial/filtered indexes. The dataset replaces the app's "one ACTIVE allocation per laptop" partial unique index with a generated-column unique key (`uq_allocations_active_laptop`), and the API's double-allocation check stays active as the runtime guard.

### PostgreSQL

1. Create a database: `createdb laptop_allocation`
2. Update `DATABASE_URL` in `backend/.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/laptop_allocation
   ```
3. Restart the backend.

## Validation Rules

- **Laptop:** duplicate `laptop_number` and duplicate `serial_number` are rejected; status must be one of `FREE`, `ALLOCATED`, `MAINTENANCE`, `INACTIVE`.
- **Intern:** duplicate `intern_id`, duplicate `email`, invalid `batch`, and invalid `domain` are rejected.
- **Search:** laptops searchable by number/brand/model/serial; interns searchable by ID/name/email/phone.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | public | Register a user |
| POST | `/api/v1/auth/login` | public | Login, returns JWT |
| GET | `/api/v1/auth/me` | token | Current user |
| GET | `/api/v1/laptops/` | token | List/search laptops |
| POST | `/api/v1/laptops/` | token | Create a laptop |
| PUT | `/api/v1/laptops/{id}` | token | Edit a laptop |
| PUT | `/api/v1/laptops/{id}/status` | token | Update laptop status |
| PUT | `/api/v1/laptops/{id}/deactivate` | token | Deactivate laptop |
| PUT | `/api/v1/laptops/{id}/activate` | token | Activate laptop |
| GET | `/api/v1/interns/` | token | List/search interns |
| POST | `/api/v1/interns/` | token | Create an intern |
| PUT | `/api/v1/interns/{id}` | token | Edit an intern |
| DELETE | `/api/v1/interns/{id}` | token | Delete an intern |
| GET | `/api/v1/allocations/` | token | List all allocations |
| GET | `/api/v1/allocations/active` | token | List active allocations |
| GET | `/api/v1/allocations/available-laptops` | token | List FREE laptops with no ACTIVE allocation |
| GET | `/api/v1/allocations/allocatable-interns` | token | List interns with batch/domain & allocation status |
| POST | `/api/v1/allocations/` | token | Allocate a laptop (creates ACTIVE allocation) |
| PUT | `/api/v1/allocations/{id}/return` | token | Return a laptop (→ RETURNED, laptop → FREE) |
| PUT | `/api/v1/allocations/{id}/cancel` | token | Cancel an allocation (→ CANCELLED, laptop → FREE) |
| GET | `/api/v1/allocations/history` | token | Paginated allocation history with search/filters |
| GET | `/api/v1/allocations/reports` | token | Summary statistics for Reports page |
| GET | `/api/v1/allocations/export` | token | CSV export (respects filters) |
| GET | `/api/v1/dashboard/stats` | token | KPI + chart data for the admin dashboard |
| POST | `/api/v1/import/excel` | token | Bulk-import laptops/interns/allocations from an `.xlsx` / `.xls` file |
| GET | `/api/v1/export/excel` | token | Download all records as an Excel workbook |
| GET | `/api/v1/export/template` | token | Download the import template (.xlsx) |

Filters for `history` / `reports` / `export`: `allocation_date`, `batch`, `domain`, `laptop_number`, `intern_name`, `status` (plus `search`, `page`, `page_size` for history).

Swagger docs available at: `http://localhost:8000/docs`

## Laptop Allocation Flow

1. **Allocate Laptop page:** Admin selects an intern; the system automatically shows that intern's **Batch** and **Domain**.
2. The available laptop list is fetched **dynamically from the database** — only laptops that are `FREE` **and** have no active allocation. Both Morning and Afternoon batches share this same real-time list (no hardcoded per-batch lists).
3. If `LAP-001` is allocated to a Morning intern, it immediately disappears from the available list and is unavailable to the Afternoon batch while the allocation is **ACTIVE**.
4. Before every allocation, the backend checks the database to **prevent double allocation**. If a laptop is already allocated, it returns `400` with `"Laptop LAP-001 is already allocated."`
5. On success, an **ACTIVE** allocation record is created and the laptop status becomes **ALLOCATED**.
6. **Return Laptop** sets the allocation status to **RETURNED**, records `returned_at`, sets the laptop status to **FREE**, and makes it available again.
7. **Cancel Allocation** sets the status to **CANCELLED** and frees the laptop.
8. **Active Allocations** page shows Laptop, Intern, Batch, Domain, Start Time, and Status with Return/Cancel actions.

## Seed Data

On startup the backend only guarantees the default admin account — **no laptops, interns or allocations are auto-created**:

- 1 admin user (`admin` / `admin123`)

The laptop inventory is populated exclusively from the admin-imported Excel file (see `/api/v1/import/excel` and the **Import Data** / Settings page). Records that arrive without a Brand / Model keep those fields empty and are shown as `—`. Demo records exist only for the automated test suite (`seed_demo_data`, never called by the app).

## License

Internal use.
