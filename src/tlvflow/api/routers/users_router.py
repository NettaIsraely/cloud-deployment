import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from tlvflow.api.schemas import (
    LoginRequest,
    LoginResponse,
    ProfileResponse,
    RegisterRequest,
    RegisterResponse,
    UpdatePaymentMethodRequest,
    UpgradeRequest,
    UpgradeResponse,
)
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.users_service import (
    get_active_users,
    get_profile,
    login_user,
    register_user,
    update_payment_method,
    upgrade_user_to_pro,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)  # type: ignore[misc]
async def register(request: Request, body: RegisterRequest) -> RegisterResponse:
    """Register a new AmateurUser and return their generated user_id."""

    repo = getattr(request.app.state, "users_repository", None)
    if repo is None or not isinstance(repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise RuntimeError("Users repository not initialized")

    try:
        user_id = await register_user(
            repo,
            name=body.name,
            email=body.email,
            password=body.password,
            payment_method_id=body.payment_method_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "email already registered":
            raise HTTPException(status_code=409, detail=msg)

        if msg == "email must be a valid email address":
            raise HTTPException(status_code=422, detail=msg)

        raise HTTPException(status_code=400, detail=msg)

    return RegisterResponse(user_id=user_id)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=200,
)  # type: ignore[misc]
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    """Authenticate by email and password. Returns user_id, name, is_pro."""
    repo = getattr(request.app.state, "users_repository", None)
    if repo is None or not isinstance(repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Users repository not initialized")
    try:
        data = login_user(repo, email=body.email, password=body.password)
        return LoginResponse(
            user_id=data["user_id"],
            name=data["name"],
            is_pro=data["is_pro"],
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )


@router.get(
    "/users/me",
    response_model=ProfileResponse,
)  # type: ignore[misc]
async def me(
    request: Request, user_id: str = Query(..., alias="user_id")
) -> ProfileResponse:
    """Return the profile for the given user_id (non-sensitive)."""
    repo = getattr(request.app.state, "users_repository", None)
    if repo is None or not isinstance(repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Users repository not initialized")
    profile_data = get_profile(repo, user_id)
    if profile_data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ProfileResponse(
        user_id=profile_data["user_id"],
        name=profile_data["name"],
        email=profile_data["email"],
        payment_method_id=profile_data["payment_method_id"],
        is_pro=profile_data["is_pro"],
    )


@router.patch(
    "/users/{user_id}/payment-method",
    status_code=200,
)  # type: ignore[misc]
async def patch_payment_method(
    request: Request,
    user_id: str,
    body: UpdatePaymentMethodRequest,
) -> RegisterResponse:
    """Update the user's payment method."""
    repo = getattr(request.app.state, "users_repository", None)
    if repo is None or not isinstance(repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise HTTPException(status_code=500, detail="Users repository not initialized")
    try:
        update_payment_method(
            repo,
            user_id=user_id,
            payment_method_id=body.payment_method_id,
        )
        return RegisterResponse(user_id=user_id)
    except ValueError as exc:
        if str(exc) == "User not found":
            raise HTTPException(status_code=404, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/user/upgrade",
    response_model=UpgradeResponse,
    status_code=200,
)  # type: ignore[misc]
async def upgrade(request: Request, body: UpgradeRequest) -> UpgradeResponse:
    """Upgrade a regular user to Pro. Provide license_number and license_expiry; optionally license_image_url (picture of driver's license)."""
    repo = getattr(request.app.state, "users_repository", None)
    if repo is None or not isinstance(repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        raise RuntimeError("Users repository not initialized")

    try:
        license_expiry = datetime.fromisoformat(
            body.license_expiry.replace("Z", "+00:00")
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="license_expiry must be an ISO 8601 date or datetime string",
        )

    try:
        user_id = await upgrade_user_to_pro(
            repo,
            user_id=body.user_id,
            license_number=body.license_number,
            license_expiry=license_expiry,
            license_image_url=body.license_image_url,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "User not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "User is already a Pro user":
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return UpgradeResponse(user_id=user_id)


@router.get("/rides/active-users")  # type: ignore[misc]
async def active_users(request: Request) -> JSONResponse:
    """Return all users who currently have an active ride."""
    active_users_repo = getattr(request.app.state, "active_users_repository", None)
    if active_users_repo is None or not isinstance(
        active_users_repo, ActiveUsersRepository
    ):
        logger.error("active_users_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Active users repository not initialized"},
        )

    users_repo = getattr(request.app.state, "users_repository", None)
    if users_repo is None or not isinstance(users_repo, UsersRepository):
        logger.error("users_repository not initialized on app.state")
        return JSONResponse(
            status_code=500,
            content={"detail": "Users repository not initialized"},
        )

    users = await get_active_users(active_users_repo, users_repo)
    return JSONResponse(content={"users": users})
