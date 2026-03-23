import logging

from fastapi import APIRouter, HTTPException, Query, Request

from tlvflow.api.schemas import (
    ActiveRideResponse,
    RideEndRequest,
    RideEndResponse,
    RideHistoryItem,
    RideHistoryResponse,
    RideStartByStationRequest,
    RideStartByVehicleRequest,
    RideStartRequest,
    RideStartResponse,
)
from tlvflow.domain.payment_service import PaymentProcessingError
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.rides_service import (
    _PERMISSION_DENIED_MSG,
    end_ride,
    start_ride,
    start_ride_by_location,
    start_ride_by_vehicle,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start", response_model=RideStartResponse, status_code=201)  # type: ignore[misc]
async def start(request: Request, body: RideStartRequest) -> RideStartResponse:
    """Start a ride from user location (PDF spec): find nearest station with eligible vehicle, assign vehicle, return station."""

    rides_repo = getattr(request.app.state, "rides_repository", None)
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    station_repo = getattr(request.app.state, "station_repository", None)
    users_repo = getattr(request.app.state, "users_repository", None)

    if rides_repo is None or not isinstance(rides_repo, RidesRepository):
        logger.error("rides_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Rides repository not initialized")
    if active_users_repo is None or not isinstance(
        active_users_repo, ActiveUsersRepository
    ):
        logger.error("active_users_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Active users repository not initialized"
        )
    if station_repo is None or not isinstance(station_repo, StationRepository):
        logger.error("station_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Station repository not initialized"
        )
    if users_repo is None or not isinstance(users_repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Users repository not initialized")

    station_locks = getattr(request.app.state, "station_locks", None)
    user_rides_locks = getattr(request.app.state, "user_rides_locks", None)
    if station_locks is None or user_rides_locks is None:
        raise HTTPException(
            status_code=500, detail="Locks not initialized on app.state"
        )

    try:
        async with user_rides_locks[body.user_id]:
            ride_id, vehicle_id, vehicle_type, start_station_id = (
                await start_ride_by_location(
                    user_id=body.user_id,
                    lon=body.lon,
                    lat=body.lat,
                    rides_repo=rides_repo,
                    active_users_repo=active_users_repo,
                    station_repo=station_repo,
                    users_repo=users_repo,
                    station_locks=station_locks,
                )
            )
    except ValueError as exc:
        msg = str(exc)
        if "already has an active ride" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "not found" in msg or "no station" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return RideStartResponse(
        ride_id=ride_id,
        vehicle_id=vehicle_id,
        vehicle_type=vehicle_type,
        start_station_id=start_station_id,
    )


@router.post(
    "/start-by-station",
    response_model=RideStartResponse,
    status_code=201,
)  # type: ignore[misc]
async def start_by_station(
    request: Request, body: RideStartByStationRequest
) -> RideStartResponse:
    """Start a ride from a specific station (by station_id)."""

    rides_repo = getattr(request.app.state, "rides_repository", None)
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    station_repo = getattr(request.app.state, "station_repository", None)
    users_repo = getattr(request.app.state, "users_repository", None)

    if rides_repo is None or not isinstance(rides_repo, RidesRepository):
        raise HTTPException(status_code=500, detail="Rides repository not initialized")
    if active_users_repo is None or not isinstance(
        active_users_repo, ActiveUsersRepository
    ):
        raise HTTPException(
            status_code=500, detail="Active users repository not initialized"
        )
    if station_repo is None or not isinstance(station_repo, StationRepository):
        raise HTTPException(
            status_code=500, detail="Station repository not initialized"
        )
    if users_repo is None or not isinstance(users_repo, UsersRepository):
        raise HTTPException(status_code=500, detail="Users repository not initialized")

    station_locks = getattr(request.app.state, "station_locks", None)
    user_rides_locks = getattr(request.app.state, "user_rides_locks", None)
    if station_locks is None or user_rides_locks is None:
        raise HTTPException(
            status_code=500, detail="Locks not initialized on app.state"
        )

    try:
        async with station_locks[body.station_id], user_rides_locks[body.user_id]:
            ride_id, vehicle_id, vehicle_type, start_station_id = await start_ride(
                user_id=body.user_id,
                station_id=body.station_id,
                rides_repo=rides_repo,
                active_users_repo=active_users_repo,
                station_repo=station_repo,
                users_repo=users_repo,
            )
    except ValueError as exc:
        msg = str(exc)
        if "already has an active ride" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "not found" in msg or "no station" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return RideStartResponse(
        ride_id=ride_id,
        vehicle_id=vehicle_id,
        vehicle_type=vehicle_type,
        start_station_id=start_station_id,
    )


@router.post(
    "/start-by-vehicle",
    response_model=RideStartResponse,
    status_code=201,
)  # type: ignore[misc]
async def start_by_vehicle(
    request: Request, body: RideStartByVehicleRequest
) -> RideStartResponse:
    """Start a ride by vehicle id (user enters vehicle number). Vehicle must be at a station."""
    rides_repo = getattr(request.app.state, "rides_repository", None)
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    station_repo = getattr(request.app.state, "station_repository", None)
    vehicle_repo = getattr(request.app.state, "vehicle_repository", None)
    users_repo = getattr(request.app.state, "users_repository", None)
    if not all(
        (
            rides_repo is not None and isinstance(rides_repo, RidesRepository),
            active_users_repo is not None
            and isinstance(active_users_repo, ActiveUsersRepository),
            station_repo is not None and isinstance(station_repo, StationRepository),
            vehicle_repo is not None and isinstance(vehicle_repo, VehicleRepository),
            users_repo is not None and isinstance(users_repo, UsersRepository),
        )
    ):
        raise HTTPException(status_code=500, detail="Repositories not initialized")
    assert rides_repo is not None
    assert active_users_repo is not None
    assert station_repo is not None
    assert vehicle_repo is not None
    assert users_repo is not None

    vehicle = vehicle_repo.get_by_id(body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    sid = vehicle.station_id
    if sid is None:
        raise HTTPException(status_code=400, detail="Vehicle is not at a station")

    station_locks = getattr(request.app.state, "station_locks", None)
    user_rides_locks = getattr(request.app.state, "user_rides_locks", None)
    if station_locks is None or user_rides_locks is None:
        raise HTTPException(status_code=500, detail="Locks not initialized")

    try:
        async with station_locks[sid], user_rides_locks[body.user_id]:
            ride_id, vehicle_id = await start_ride_by_vehicle(
                user_id=body.user_id,
                vehicle_id=body.vehicle_id,
                rides_repo=rides_repo,
                active_users_repo=active_users_repo,
                station_repo=station_repo,
                vehicle_repo=vehicle_repo,
                users_repo=users_repo,
            )
    except ValueError as exc:
        msg = str(exc)
        if msg == _PERMISSION_DENIED_MSG:
            raise HTTPException(status_code=403, detail=msg)
        if "already has an active ride" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "not found" in msg or "not at a station" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return RideStartResponse(
        ride_id=ride_id,
        vehicle_id=vehicle_id,
        vehicle_type=vehicle.vehicle_type(),
        start_station_id=sid,
    )


@router.get(
    "/rides/active",
    response_model=ActiveRideResponse,
)  # type: ignore[misc]
async def get_active_ride(
    request: Request, user_id: str = Query(..., alias="user_id")
) -> ActiveRideResponse:
    """Return the active ride for the given user, or 404 if none."""
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    rides_repo = getattr(request.app.state, "rides_repository", None)
    if active_users_repo is None or not isinstance(
        active_users_repo, ActiveUsersRepository
    ):
        raise HTTPException(
            status_code=500, detail="Active users repository not initialized"
        )
    if rides_repo is None or not isinstance(rides_repo, RidesRepository):
        raise HTTPException(status_code=500, detail="Rides repository not initialized")

    ride_id = active_users_repo.get_ride_id(user_id)
    if ride_id is None:
        raise HTTPException(status_code=404, detail="No active ride")
    ride = rides_repo.get_by_id(ride_id)
    if ride is None:
        raise HTTPException(status_code=404, detail="Active ride not found")
    return ActiveRideResponse(
        ride_id=ride.ride_id,
        vehicle_id=ride.vehicle_id,
        start_time=ride.start_time.isoformat(),
    )


@router.get(
    "/rides/history",
    response_model=RideHistoryResponse,
)  # type: ignore[misc]
async def get_ride_history(
    request: Request, user_id: str = Query(..., alias="user_id")
) -> RideHistoryResponse:
    """Return completed ride history for the given user (most recent first)."""
    rides_repo = getattr(request.app.state, "rides_repository", None)
    if rides_repo is None or not isinstance(rides_repo, RidesRepository):
        raise HTTPException(status_code=500, detail="Rides repository not initialized")
    all_rides = rides_repo.get_by_user_id(user_id)
    completed = [r for r in all_rides if r.end_time is not None]
    completed.sort(key=lambda r: r.end_time or r.start_time, reverse=True)
    items = [
        RideHistoryItem(
            ride_id=r.ride_id,
            vehicle_id=r.vehicle_id,
            start_time=r.start_time.isoformat(),
            end_time=r.end_time.isoformat() if r.end_time else "",
            fee=r.fee,
            status=r.status().value,
        )
        for r in completed
    ]
    return RideHistoryResponse(rides=items)


@router.post(
    "/end",
    response_model=RideEndResponse,
    status_code=200,
)  # type: ignore[misc]
async def end(request: Request, body: RideEndRequest) -> RideEndResponse:
    """End an active ride, calculate the fee, and release the vehicle."""

    # Fetch repositories from app state
    rides_repo = getattr(request.app.state, "rides_repository", None)
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    users_repo = getattr(request.app.state, "users_repository", None)
    vehicle_repo = getattr(request.app.state, "vehicle_repository", None)

    # Strict type-checking and initialization validation
    if rides_repo is None or not isinstance(rides_repo, RidesRepository):
        logger.error("rides_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Rides repository not initialized")

    if active_users_repo is None or not isinstance(
        active_users_repo, ActiveUsersRepository
    ):
        logger.error("active_users_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Active users repository not initialized"
        )

    if users_repo is None or not isinstance(users_repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Users repository not initialized")

    if vehicle_repo is None or not isinstance(vehicle_repo, VehicleRepository):
        logger.error("vehicle_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Vehicle repository not initialized"
        )

    station_repo = getattr(request.app.state, "station_repository", None)
    if station_repo is None or not isinstance(station_repo, StationRepository):
        logger.error("station_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Station repository not initialized"
        )

    payment_service = getattr(request.app.state, "payment_service", None)
    if payment_service is None:
        logger.error("payment_service not initialized on app.state")
        raise HTTPException(status_code=500, detail="Payment service not initialized")

    station_locks = getattr(request.app.state, "station_locks", None)
    user_rides_locks = getattr(request.app.state, "user_rides_locks", None)
    if station_locks is None or user_rides_locks is None:
        raise HTTPException(
            status_code=500, detail="Locks not initialized on app.state"
        )

    ride = rides_repo.get_by_id(body.ride_id)
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    user_id = ride.user_id

    try:
        async with user_rides_locks[user_id]:
            end_station_id, payment_charged = await end_ride(
                ride_id=body.ride_id,
                lon=body.lon,
                lat=body.lat,
                rides_repo=rides_repo,
                active_users_repo=active_users_repo,
                station_repo=station_repo,
                users_repo=users_repo,
                vehicle_repo=vehicle_repo,
                payment_service=payment_service,
                station_locks=station_locks,
            )
    except ValueError as exc:
        msg = str(exc)
        if (
            "not found" in msg
            or "does not have an active ride" in msg
            or "is not active" in msg
            or "no station" in msg.lower()
        ):
            raise HTTPException(status_code=404, detail=msg)
        if "is full" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except PaymentProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return RideEndResponse(
        end_station_id=end_station_id, payment_charged=payment_charged
    )
