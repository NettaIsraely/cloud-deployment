"""FastAPI application entrypoint."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tlvflow.api.routes import router as api_router
from tlvflow.domain.payment_service import PaymentService
from tlvflow.logging import setup_logging
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.maintenance_repository import MaintenanceRepository
from tlvflow.persistence.payments_repository import PaymentsRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.state_store import StateStore
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.degraded_vehicles_service import restore_degraded
from tlvflow.services.link_vehicles import link_vehicles_to_stations

setup_logging()
logger = logging.getLogger(__name__)

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VEHICLES_CSV = PROJECT_ROOT / "data" / "vehicles.csv"
STATIONS_CSV = PROJECT_ROOT / "data" / "stations.csv"
STATE_JSON = PROJECT_ROOT / "data" / "state.json"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    logger.info("Application starting")

    state_store = StateStore(path=STATE_JSON)
    snapshot = state_store.load()

    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    users_repo = UsersRepository()
    active_users_repo = ActiveUsersRepository()
    rides_repo = RidesRepository()
    maintenance_repo = MaintenanceRepository()
    payments_repo = PaymentsRepository()

    degraded_vehicles_repo = DegradedVehiclesRepository()

    if snapshot:
        logger.info("Loading application state from %s", STATE_JSON)
        vehicle_repo.restore(snapshot.get("vehicles", {}))
        station_repo.restore(snapshot.get("stations", {}), vehicle_repo=vehicle_repo)
        users_repo.restore(snapshot.get("users", {}))
        active_users_repo.restore(snapshot.get("active_users", {}))
        rides_repo.restore(snapshot.get("rides", {}))
        maintenance_repo.restore(snapshot.get("maintenance", {}))
        payments_repo.restore(snapshot.get("payments", {}))
        # Stations already have vehicles docked from restore; do not run link_vehicles (would skip vehicles with no station_id and log warnings).
        await restore_degraded(
            station_repo,
            vehicle_repo,
            degraded_vehicles_repo,
            snapshot.get("degraded_vehicles", {}),
        )
    else:
        vehicle_count = vehicle_repo.load_from_csv(VEHICLES_CSV)
        logger.info("Loaded %d vehicles into memory", vehicle_count)

        station_count = station_repo.load_from_csv(STATIONS_CSV)
        logger.info("Loaded %d stations into memory", station_count)

        await link_vehicles_to_stations(
            vehicle_repo, station_repo, degraded_vehicles_repo
        )

    app.state.vehicle_repository = vehicle_repo
    app.state.station_repository = station_repo
    app.state.users_repository = users_repo
    app.state.active_users_repository = active_users_repo
    app.state.state_store = state_store
    app.state.rides_repository = rides_repo
    app.state.maintenance_repository = maintenance_repo
    app.state.payments_repository = payments_repo
    app.state.payment_service = PaymentService()
    app.state.degraded_vehicles_repository = degraded_vehicles_repo
    # Async locks to prevent race conditions: double-booking, station overflow, duplicate ride starts
    app.state.station_locks = defaultdict(asyncio.Lock)
    app.state.user_rides_locks = defaultdict(asyncio.Lock)
    app.state.treat_vehicles_lock = asyncio.Lock()

    try:
        yield
    finally:
        logger.info("Application shutting down; saving state to %s", STATE_JSON)
        state_store.save(
            {
                "vehicles": vehicle_repo.snapshot(),
                "stations": station_repo.snapshot(),
                "users": users_repo.snapshot(),
                "active_users": active_users_repo.snapshot(),
                "rides": rides_repo.snapshot(),
                "maintenance": maintenance_repo.snapshot(),
                "payments": payments_repo.snapshot(),
                "degraded_vehicles": degraded_vehicles_repo.snapshot(),
            }
        )


app = FastAPI(title="TLVFlow API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(api_router)
