# TLVFlow

A vehicle-sharing management system for Tel Aviv, built as a RESTful API with a React frontend.
Users can register, rent bikes, e-bikes and scooters from docking stations across the city, and return them to any station with available capacity.
The system handles the full ride lifecycle including payments, vehicle maintenance, degradation reporting, and persistent state across restarts.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Running the Project](#running-the-project)
- [Domain Model](#domain-model)
- [API Endpoints](#api-endpoints)
- [Vehicle Selection Logic](#vehicle-selection-logic)
- [Running Tests](#running-tests)
- [Data Files](#data-files)
- [Design Patterns & OOP Principles](#design-patterns--oop-principles)
- [State Persistence](#state-persistence)

## Features

- **User management** — registration with hashed passwords (PBKDF2-SHA256), email uniqueness enforcement, and upgrade path from regular to Pro accounts.
- **Ride lifecycle** — start a ride from the nearest station with an eligible vehicle, end at the nearest station with capacity, automatic fee calculation and payment processing.
- **Three vehicle types** — Bikes, E-Bikes, and Scooters with type-specific maintenance treatments and rental eligibility rules.
- **1,000 stations / 18,754 vehicles** — loaded from CSV on cold start; linked to stations with capacity enforcement.
- **Pro users** — license-validated users who can rent all vehicle types (including electric); regular users are limited to non-electric bikes.
- **Payment processing** — mocked async payment service supporting charges, receipts, and refunds tied to a user's stored payment token.
- **Vehicle degradation** — report a vehicle as degraded only during an active ride; ride ends fee-free, vehicle moves to a degraded pool.
- **Maintenance pipeline** — batch treatment of eligible vehicles (7+ rides since last treatment or degraded), with type-specific treatments (chain lubrication, battery inspection, firmware update, etc.).
- **Concurrency safety** — async locks per station and per user to prevent double-booking, station overflow, and duplicate ride starts.
- **State persistence** — full application state serialized to JSON on shutdown and restored on startup (atomic writes via temp file + rename).
- **Web UI** — React frontend for registration, starting/ending rides (with “use my location” or enter latitude/longitude), and viewing stations and vehicles. Report degraded is available only during an active ride.

## Tech Stack

| Component       | Technology            |
|-----------------|------------------------|
| Backend         | Python 3.12, FastAPI, Uvicorn (ASGI), Pydantic v2 |
| Frontend        | React 18, TypeScript, Vite 6 |
| Testing         | pytest, httpx         |
| Linting         | Ruff                  |
| Type Checking   | mypy (backend), TypeScript (frontend) |
| Build & Env     | setuptools + uv (backend), Vite (frontend) |

## Architecture

The backend follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────┐
│          API Layer              │  FastAPI routers, Pydantic schemas,
│   (routes, schemas, routers)    │  request/response validation
├─────────────────────────────────┤
│        Service Layer            │  Business logic orchestration,
│   (rides, users, vehicles,      │  coordinates domain + persistence
│    stations, degraded)          │
├─────────────────────────────────┤
│        Domain Layer             │  Core entities, enums, business rules,
│   (vehicles, stations, rides,   │  validation, factory methods
│    users, payments, reports)    │
├─────────────────────────────────┤
│      Persistence Layer          │  In-memory repositories with
│   (repositories, state store,   │  snapshot/restore, CSV loaders,
│    loaders)                     │  Protocol-based interfaces
└─────────────────────────────────┘
```

The frontend is a single-page React app that talks to the API at `http://localhost:8000` by default (configurable via `VITE_API_URL`).

## Project Structure

```
advanced-programming-project/
├── data/
│   ├── vehicles.csv              # 18,754 vehicles with type, status, station
│   ├── stations.csv              # 1,000 stations with coordinates and capacity
│   └── state.json                # Auto-generated application state snapshot
├── src/
│   └── tlvflow/                  # Backend (Python)
│       ├── api/
│       │   ├── app.py            # FastAPI app, lifespan (startup/shutdown)
│       │   ├── routes.py        # Top-level router aggregation
│       │   ├── schemas.py       # Pydantic request/response models
│       │   └── routers/
│       │       ├── users_router.py
│       │       ├── vehicles_router.py
│       │       ├── rides_router.py
│       │       └── stations_router.py
│       ├── domain/
│       │   ├── enums.py
│       │   ├── vehicles.py       # Vehicle ABC, Bike, EBike, Scooter, VehicleFactory
│       │   ├── stations.py
│       │   ├── rides.py
│       │   ├── users.py
│       │   ├── payment.py
│       │   ├── payment_service.py
│       │   ├── reports.py
│       │   └── maintenance_event.py
│       ├── services/
│       │   ├── rides_service.py
│       │   ├── users_service.py
│       │   ├── vehicles_service.py
│       │   ├── stations_service.py
│       │   ├── link_vehicles.py
│       │   └── degraded_vehicles_service.py
│       ├── persistence/
│       │   ├── in_memory.py
│       │   ├── users_repository.py
│       │   ├── rides_repository.py
│       │   ├── payments_repository.py
│       │   ├── maintenance_repository.py
│       │   ├── active_users_repository.py
│       │   ├── degraded_vehicles_repository.py
│       │   ├── state_store.py
│       │   └── loaders.py
│       ├── repositories/
│       │   └── interfaces.py
│       └── logging.py
├── frontend/                     # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css
│   │   ├── api.ts                # API base URL and helpers
│   │   └── Toast.tsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── README.md
```

## Running the Project

You need both the **backend API** and the **frontend** running. The frontend calls the API at `http://localhost:8000` by default.

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 18+ (for the frontend)

---

### 1. Run the backend (API)

From the **project root**:

```bash
cd advanced-programming-project
```

Create and activate a virtual environment with `uv`:

```bash
uv venv
source .venv/bin/activate   # macOS/Linux
```

On Windows: `.venv\Scripts\activate`

Install backend dependencies and start the API server:

```bash
uv sync --extra dev
uvicorn tlvflow.api.app:app --reload
```

The API will be at **http://localhost:8000**.

- **Swagger UI:** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  

On first launch, the server loads vehicles and stations from `data/`. On later runs it restores state from `data/state.json` if present.

---

### 2. Run the frontend

Open a **second terminal**. From the project root:

```bash
cd advanced-programming-project/frontend
npm install
npm run dev
```

The frontend will be at **http://localhost:5173** (or the port Vite prints). Use this URL in the browser; it will talk to the API on port 8000.

To point the frontend at a different API URL, set `VITE_API_URL` before starting:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

---

### Summary

| Service   | Directory        | Command                          | URL                  |
|----------|-------------------|----------------------------------|----------------------|
| Backend  | project root      | `uvicorn tlvflow.api.app:app --reload` | http://localhost:8000 |
| Frontend | `frontend/`       | `npm run dev`                    | http://localhost:5173 |

Run the backend first, then the frontend. Use the frontend URL in the browser.

## Domain Model

### Entities

| Entity              | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| **Vehicle** (ABC)   | Abstract base with `Bike`, `EBike`, `Scooter` subclasses. Tracks status, ride count, station assignment, and maintenance eligibility. |
| **Station**         | Docking station with coordinates, capacity, and a managed list of docked vehicles. Supports dock/undock/checkout operations. |
| **Ride**            | Represents a single ride with start/end locations, timestamps, status, fee calculation, and associated user/vehicle. |
| **User**            | Regular user with hashed credentials, payment token, ride history. Limited to non-electric vehicles. |
| **ProUser**         | Extends User with a validated driver's license. Can rent all vehicle types. |
| **Payment**         | Immutable record for charges, receipts, or refunds linked to a ride.       |
| **VehicleReport**   | User-submitted damage report with mock AI verification.                    |
| **MaintenanceEvent**| Tracks a maintenance episode with treatments, timestamps, and status.      |

### Enums

| Enum              | Values                                                    |
|-------------------|-----------------------------------------------------------|
| `VehicleStatus`   | AVAILABLE, IN_USE, AWAITING_REPORT_REVIEW, DEGRADED       |
| `RideStatus`      | ACTIVE, COMPLETED, CANCELLED                              |
| `PaymentKind`     | CHARGE, RECEIPT, REFUND                                   |
| `ReportStatus`    | SUBMITTED, UNDER_REVIEW, VERIFIED, REJECTED               |
| `EventStatus`     | OPEN, IN_PROGRESS, CLOSED                                 |
| `TreatmentType`   | GENERAL_INSPECTION, CHAIN_LUBRICATION, BATTERY_INSPECTION, SCOOTER_FIRMWARE_UPDATE |

## API Endpoints

| Method | Path                                 | Description                                              |
|--------|--------------------------------------|----------------------------------------------------------|
| POST   | `/register`                          | Register a new user (name, email, password, payment token) |
| POST   | `/login`                             | Authenticate by email and password; returns `user_id`, `name`, `is_pro` |
| GET    | `/users/me`                          | Return the profile for a given `user_id` (query param)   |
| PATCH  | `/users/{user_id}/payment-method`    | Update a user's stored payment method token              |
| POST   | `/user/upgrade`                      | Upgrade a user to Pro with license details               |
| GET    | `/rides/active-users`                | List all users with an active ride                       |
| POST   | `/ride/start`                        | Start a ride from user location: body `{ user_id, lon, lat }`; finds nearest station with eligible vehicle, assigns vehicle, returns `ride_id`, `vehicle_id`, `vehicle_type`, `start_station_id` |
| POST   | `/ride/start-by-station`             | Start a ride from a specific station (body `{ user_id, station_id }`) |
| POST   | `/ride/start-by-vehicle`             | Start a ride by vehicle ID (body `{ user_id, vehicle_id }`); vehicle must be at a station; enforces user-type permissions via `can_rent()` |
| GET    | `/ride/rides/active`                 | Return the active ride for a given `user_id` (query param), or 404 if none |
| GET    | `/ride/rides/history`                | Return completed ride history for a given `user_id` (most recent first) |
| POST   | `/ride/end`                          | End a ride — body `{ ride_id, lon, lat }`; must be within 5 m of a station; docks at nearest with free slot, processes payment |
| POST   | `/vehicle/treat`                     | Batch-treat eligible and degraded vehicles; returns list of treated vehicle IDs |
| POST   | `/vehicle/report-degraded`           | Report current vehicle as degraded during an active ride only (ends ride at no charge) |
| GET    | `/stations/nearest`                  | Find the nearest station to given coordinates            |

All request/response bodies are validated with Pydantic (`extra="forbid"` rejects unknown fields).

## Vehicle Selection Logic

When a ride starts, the system finds the nearest station (by Euclidean distance) that has an eligible vehicle. A vehicle is eligible to rent if:

- `status == AVAILABLE`
- `rides_since_last_treated <= 10` (so 10 rides is still rentable; it becomes unrentable after the 11th)

User-type permissions (`can_rent()`) are enforced only in the `/ride/start-by-vehicle` flow — regular users are blocked from renting electric vehicles there. The `/ride/start` and `/ride/start-by-station` flows select vehicles by station eligibility without a per-user type check.

Treatment can be initiated on vehicles with **7 or more** rides since last treatment (`rides_since_last_treated >= 7`). Unrentable vehicles (`> 10` rides) stay docked until treated.

When multiple eligible vehicles exist at a station, a **deterministic selection rule** applies:

1. Prefer **bike**, then **ebike**, then **scooter** (fixed type priority).
2. Within the same type, choose the vehicle with the **smallest `vehicle_id`** (lexicographic order).

## Running Tests

Backend tests only (run from project root):

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/unit/
uv run pytest tests/integration/
```

The test suite includes **27 test files** organized into:

- **Unit tests** — domain entities, services, repositories, and loaders tested in isolation.
- **Integration tests** — full API tests using FastAPI's `TestClient` via httpx, covering users, vehicles, stations, and rides endpoints.

## Data Files

| File              | Records | Description                                                    |
|-------------------|---------|----------------------------------------------------------------|
| `vehicles.csv`    | 18,754  | Vehicle ID, station ID, type (scooter/electric_bicycle/bicycle), status, rides since last treated, last treated date |
| `stations.csv`    | 1,000   | Station ID, name, latitude, longitude, max capacity            |
| `state.json`      | —       | Auto-generated on shutdown; contains full serialized application state |

## Design Patterns & OOP Principles

| Pattern / Principle       | Where Applied                                                                 |
|---------------------------|-------------------------------------------------------------------------------|
| **Abstract Base Class**   | `Vehicle` ABC with `Bike`, `EBike`, `Scooter` concrete implementations        |
| **Factory**               | `VehicleFactory.create_vehicle()` with a type registry                        |
| **Inheritance**           | `ProUser` extends `User` with license validation and expanded permissions     |
| **Polymorphism**          | `can_rent()` differs between User (non-electric only) and ProUser (all types); `get_required_treatments()` differs per vehicle type; `is_electric` property differs per subclass |
| **Encapsulation**         | Protected (`_`) and private (`__`) attributes with read-only properties throughout all domain entities |
| **Protocol (Structural Typing)** | Repository interfaces defined as `Protocol` classes for loose coupling |
| **Repository Pattern**    | Each entity has a dedicated repository with consistent `add`/`get`/`snapshot`/`restore` interface |
| **Dependency Injection**  | Services receive repositories and external services as function parameters     |
| **Async Concurrency**     | `asyncio.Lock` per station and per user to prevent race conditions            |
| **Atomic Persistence**    | State saved via temp file + `os.rename` to prevent corruption                 |

## State Persistence

The application maintains full state across restarts:

**Shutdown:** all repositories serialize their state into a single JSON snapshot saved atomically to `data/state.json`.

**Startup:** if `state.json` exists, all repositories restore from it. Vehicles are re-linked to stations, and degraded vehicles are moved to the degraded pool. If no snapshot exists (cold start), data is loaded from the CSV files.

**Snapshot keys:** `vehicles`, `stations`, `users`, `active_users`, `rides`, `maintenance`, `payments`, `degraded_vehicles`.
