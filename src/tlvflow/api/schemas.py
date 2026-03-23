from typing import Literal

from pydantic import BaseModel, ConfigDict, Field  # type: ignore[misc]

# extra="forbid":
# this is a crucial setting that tells Pydantic to reject any fields that are not explicitly defined in the model that are sent by postman, immediately getting a clean 422.
# This is important to ensure that your API is strict and only accepts the fields you expect, which helps catch errors early and maintain a clear contract for your API endpoints.


# Shared / small responses
class OkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detail: str


# Stations : matches stations_service.station_to_dict(...)
class StationNearestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station_id: int
    name: str
    lat: float
    lon: float
    capacity: int
    available_slots: int
    is_full: bool
    is_empty: bool


# Users / Register: (adjust fields to your actual endpoint spec)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    email: str
    password: str
    payment_method_id: str = Field(
        min_length=1, description="Mocked payment token (required for billing)"
    )


class RegisterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    name: str
    is_pro: bool


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    name: str
    email: str
    payment_method_id: str
    is_pro: bool


class UpdatePaymentMethodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_method_id: str = Field(min_length=1)


class UpgradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    license_number: str = Field(min_length=1)
    license_expiry: str = Field(min_length=1)  # ISO date or datetime string
    license_image_url: str | None = None  # optional picture of driver's license


class UpgradeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str


# Rides: PDF spec — POST /ride/start input: user_id, lon, lat (find nearest station with eligible vehicle)
class RideStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    lon: float = Field(ge=-180.0, le=180.0)
    lat: float = Field(ge=-90.0, le=90.0)


class RideStartByStationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    station_id: int = Field(ge=1)


class RideStartByVehicleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    vehicle_id: str = Field(min_length=1)


class RideStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ride_id: str
    vehicle_id: str
    vehicle_type: str
    start_station_id: int


class RideEndRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ride_id: str = Field(min_length=1)
    lon: float
    lat: float


class RideEndResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    end_station_id: int
    payment_charged: float


class ActiveRideResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ride_id: str
    vehicle_id: str
    start_time: str


class RideHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ride_id: str
    vehicle_id: str
    start_time: str
    end_time: str
    fee: float
    status: str


class RideHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rides: list[RideHistoryItem]


# Vehicle report degraded
class ReportDegradedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    vehicle_id: str = Field(min_length=1)
