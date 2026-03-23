from fastapi import APIRouter

from tlvflow.api.routers.rides_router import router as rides_router
from tlvflow.api.routers.stations_router import router as stations_router
from tlvflow.api.routers.users_router import router as users_router
from tlvflow.api.routers.vehicles_router import router as vehicles_router

router = APIRouter()
router.include_router(stations_router)
router.include_router(users_router)
router.include_router(vehicles_router)
router.include_router(rides_router, prefix="/ride", tags=["ride"])
