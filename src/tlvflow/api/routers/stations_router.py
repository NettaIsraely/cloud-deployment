import logging

from fastapi import APIRouter, HTTPException, Query, Request

from tlvflow.api.schemas import StationNearestResponse
from tlvflow.persistence.in_memory import StationRepository
from tlvflow.services.stations_service import find_nearest_station

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stations"])


@router.get(
    "/stations/nearest", response_model=StationNearestResponse
)  # type: ignore[misc]
async def nearest_station(
    request: Request,
    lon: float = Query(..., ge=-180.0, le=180.0),
    lat: float = Query(..., ge=-90.0, le=90.0),
) -> StationNearestResponse:
    """
    Return the nearest station to (lon, lat)
    """

    repo = getattr(request.app.state, "station_repository", None)
    if repo is None or not isinstance(repo, StationRepository):
        logger.error("station_repository not initialized on app.state")
        raise HTTPException(
            status_code=500, detail="Station repository not initialized"
        )

    station = await find_nearest_station(repo, lon=lon, lat=lat)
    if station is None:
        raise HTTPException(status_code=404, detail="No stations available")

    return StationNearestResponse(
        station_id=station.station_id,
        name=station.name,
        lat=station.latitude,
        lon=station.longitude,
        capacity=station.capacity,
        available_slots=station.available_slots,
        is_full=station.available_slots == 0,
        is_empty=station.available_slots == station.capacity,
    )
