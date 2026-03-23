import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from tlvflow.api.schemas import OkResponse, ReportDegradedRequest
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.maintenance_repository import MaintenanceRepository
from tlvflow.services.vehicles_service import (
    report_degraded_vehicle,
    treat_vehicles,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vehicles"])


@router.post("/vehicle/treat")  # type: ignore[misc]
async def treat(request: Request) -> JSONResponse:
    """Treat all eligible vehicles and return their IDs."""
    vehicles_repo = getattr(request.app.state, "vehicle_repository", None)
    stations_repo = getattr(request.app.state, "station_repository", None)

    if vehicles_repo is None or not isinstance(vehicles_repo, VehicleRepository):
        logger.error("vehicle_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Vehicle repository not initialized"},
        )

    if stations_repo is None or not isinstance(stations_repo, StationRepository):
        logger.error("station_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Station repository not initialized"},
        )

    maintenance_repo = getattr(request.app.state, "maintenance_repository", None)
    if maintenance_repo is None or not isinstance(
        maintenance_repo, MaintenanceRepository
    ):
        logger.error("maintenance_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Maintenance repository not initialized"},
        )

    degraded_repo = getattr(request.app.state, "degraded_vehicles_repository", None)
    if degraded_repo is None or not isinstance(
        degraded_repo, DegradedVehiclesRepository
    ):
        logger.error("degraded_vehicles_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Degraded vehicles repository not initialized"},
        )

    treat_lock = getattr(request.app.state, "treat_vehicles_lock", None)
    if treat_lock is None:
        return JSONResponse(
            status_code=500,
            content={"detail": "Locks not initialized on app.state"},
        )

    async with treat_lock:
        treated_ids = await treat_vehicles(
            vehicles_repo, stations_repo, maintenance_repo, degraded_repo
        )
    return JSONResponse(content=treated_ids)


@router.post("/vehicle/report-degraded", response_model=OkResponse)  # type: ignore[misc]
async def report_degraded(
    request: Request,
    body: ReportDegradedRequest,
) -> OkResponse:
    """Report a vehicle as degraded during an active ride only (ends ride at no charge)."""

    rides_repo = getattr(request.app.state, "rides_repository", None)
    vehicles_repo = getattr(request.app.state, "vehicle_repository", None)
    degraded_repo = getattr(request.app.state, "degraded_vehicles_repository", None)
    active_users_repo = getattr(request.app.state, "active_users_repository", None)

    if rides_repo is None:
        raise RuntimeError("rides_repository not initialized")

    if vehicles_repo is None:
        raise RuntimeError("vehicle_repository not initialized")

    if degraded_repo is None:
        raise RuntimeError("degraded_vehicles_repository not initialized")

    if active_users_repo is None:
        raise RuntimeError("active_users_repository not initialized")

    user_rides_locks = getattr(request.app.state, "user_rides_locks", None)
    if user_rides_locks is None:
        raise RuntimeError("user_rides_locks not initialized on app.state")

    try:
        async with user_rides_locks[body.user_id]:
            await report_degraded_vehicle(
                user_id=body.user_id,
                vehicle_id=body.vehicle_id,
                rides_repo=rides_repo,
                vehicles_repo=vehicles_repo,
                degraded_repo=degraded_repo,
                active_users_repo=active_users_repo,
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        msg = str(exc)

        if msg == "no active ride":
            raise HTTPException(status_code=409, detail=msg) from exc

        raise HTTPException(status_code=400, detail=msg) from exc

    return OkResponse()
