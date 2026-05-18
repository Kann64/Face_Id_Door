import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - optional import during docs-only checks
    Client = Any  # type: ignore
    create_client = None  # type: ignore


JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))
UNLOCK_DURATION_SECONDS = 5
LINK_VALIDITY_HOURS = 2
MAX_FACE_UPLOAD_MB = 5


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=3)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class GuestCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    note: Optional[str] = Field(default=None, max_length=300)


class GuestUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    enabled: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=300)


class RegistrationLinkRequest(BaseModel):
    guest_id: str


class NotificationResponse(BaseModel):
    id: str
    message: str
    kind: str
    created_at: str
    is_read: bool


class SimpleDataStore:
    """Fallback in-memory storage used when Supabase is unavailable."""

    def __init__(self) -> None:
        self.guests: Dict[str, Dict[str, Any]] = {}
        self.links: Dict[str, Dict[str, Any]] = {}
        self.notifications: List[Dict[str, Any]] = []


class SupabaseGateway:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.bucket = os.getenv("SUPABASE_FACE_BUCKET", "faces")
        self.client: Optional[Client] = None
        if self.url and self.key and create_client:
            self.client = create_client(self.url, self.key)

    @property
    def connected(self) -> bool:
        return self.client is not None


app = FastAPI(title="Face ID Door API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="web/static"), name="static")

supabase_gateway = SupabaseGateway()
store = SimpleDataStore()
unlocked_until: Optional[datetime] = None
revoked_tokens: set[str] = set()


def now_utc() -> datetime:
    return datetime.now(UTC)


def jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "change_me_in_production")


def admin_seed() -> Dict[str, str]:
    return {
        "id": "admin-1",
        "email": os.getenv("ADMIN_EMAIL", "admin@example.com"),
        "password": os.getenv("ADMIN_PASSWORD", "admin"),
        "name": os.getenv("ADMIN_NAME", "Admin"),
    }


def create_token(user_id: str, email: str) -> str:
    expires_at = now_utc() + timedelta(hours=JWT_EXPIRES_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expires_at}
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def auth_token_from_header(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token in revoked_tokens:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    return token


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    token = auth_token_from_header(authorization)
    payload = decode_token(token)
    return {
        "id": payload.get("sub", "admin-1"),
        "email": payload.get("email", admin_seed()["email"]),
        "name": admin_seed()["name"],
        "token": token,
    }


def add_notification(message: str, kind: str) -> None:
    entry = {
        "id": secrets.token_hex(8),
        "message": message,
        "kind": kind,
        "created_at": now_utc().isoformat(),
        "is_read": False,
    }
    if supabase_gateway.connected:
        try:
            supabase_gateway.client.table("notifications").insert(
                {"kind": kind, "message": message}
            ).execute()
        except Exception:
            store.notifications.insert(0, entry)
    else:
        store.notifications.insert(0, entry)


def ensure_guest(guest_id: str) -> Dict[str, Any]:
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("guests")
                .select("*")
                .eq("id", guest_id)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
        except Exception:
            pass
    guest = store.guests.get(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    return guest


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "supabase_connected": supabase_gateway.connected}


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    admin = admin_seed()
    if payload.email != admin["email"] or payload.password != admin["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(admin["id"], admin["email"])
    add_notification("Admin logged in", "auth")
    return AuthResponse(
        access_token=token,
        expires_in_seconds=JWT_EXPIRES_HOURS * 3600,
    )


@app.post("/auth/logout")
def logout(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    revoked_tokens.add(user["token"])
    add_notification("Admin logged out", "auth")
    return {"message": "Logged out"}


@app.get("/auth/me", response_model=UserResponse)
def me(user: Dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user["id"], email=user["email"], name=user["name"])


@app.post("/door/unlock")
def unlock_door(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    global unlocked_until
    unlocked_until = now_utc() + timedelta(seconds=UNLOCK_DURATION_SECONDS)
    add_notification(f"Door unlocked by {user['name']} for 5 seconds", "door")
    return {
        "status": "unlocked",
        "unlock_duration_seconds": UNLOCK_DURATION_SECONDS,
        "unlock_until": unlocked_until.isoformat(),
    }


@app.get("/door/status")
def door_status(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    _ = user
    is_unlocked = bool(unlocked_until and unlocked_until > now_utc())
    return {
        "is_unlocked": is_unlocked,
        "unlock_duration_seconds": UNLOCK_DURATION_SECONDS,
        "unlock_until": unlocked_until.isoformat() if unlocked_until else None,
    }


@app.get("/guests")
def list_guests(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("guests")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return {"items": response.data or []}
        except Exception:
            pass
    return {"items": list(store.guests.values())}


@app.post("/guests", status_code=201)
def create_guest(payload: GuestCreate, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("guests")
                .insert(
                    {
                        "full_name": payload.full_name,
                        "note": payload.note,
                        "enabled": True,
                    }
                )
                .execute()
            )
            guest = (response.data or [None])[0]
            if guest:
                add_notification(f"Guest created: {payload.full_name}", "guest")
                return guest
        except Exception:
            pass

    guest_id = secrets.token_hex(8)
    guest = {
        "id": guest_id,
        "full_name": payload.full_name,
        "enabled": True,
        "note": payload.note,
        "face_image_path": None,
        "created_at": now_utc().isoformat(),
    }
    store.guests[guest_id] = guest
    add_notification(f"Guest created: {payload.full_name}", "guest")
    return guest


@app.get("/guests/{guest_id}")
def get_guest(guest_id: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    _ = user
    return ensure_guest(guest_id)


@app.patch("/guests/{guest_id}")
def update_guest(
    guest_id: str,
    payload: GuestUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("guests")
                .update(payload.model_dump(exclude_none=True))
                .eq("id", guest_id)
                .execute()
            )
            updated = (response.data or [None])[0]
            if not updated:
                raise HTTPException(status_code=404, detail="Guest not found")
            add_notification(f"Guest updated: {updated['full_name']}", "guest")
            return updated
        except HTTPException:
            raise
        except Exception:
            pass

    guest = ensure_guest(guest_id)
    updates = payload.model_dump(exclude_none=True)
    guest.update(updates)
    add_notification(f"Guest updated: {guest['full_name']}", "guest")
    return guest


@app.delete("/guests/{guest_id}", status_code=204)
def delete_guest(guest_id: str, user: Dict[str, Any] = Depends(get_current_user)) -> None:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("guests")
                .delete()
                .eq("id", guest_id)
                .execute()
            )
            deleted = (response.data or [None])[0]
            if not deleted:
                raise HTTPException(status_code=404, detail="Guest not found")
            add_notification(f"Guest deleted: {deleted['full_name']}", "guest")
            return
        except HTTPException:
            raise
        except Exception:
            pass

    guest = ensure_guest(guest_id)
    del store.guests[guest_id]
    add_notification(f"Guest deleted: {guest['full_name']}", "guest")


@app.post("/registration/generate-link")
def generate_registration_link(
    payload: RegistrationLinkRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    _ = user
    guest = ensure_guest(payload.guest_id)
    token = secrets.token_urlsafe(24)
    expires_at = now_utc() + timedelta(hours=LINK_VALIDITY_HOURS)
    if supabase_gateway.connected:
        try:
            supabase_gateway.client.table("registration_links").insert(
                {
                    "token": token,
                    "guest_id": payload.guest_id,
                    "expires_at": expires_at.isoformat(),
                    "used": False,
                }
            ).execute()
            url = f"/register/{token}"
            add_notification(f"Registration link generated for {guest['full_name']}", "registration")
            return {
                "token": token,
                "registration_url": url,
                "expires_in_seconds": LINK_VALIDITY_HOURS * 3600,
                "one_time_use": True,
            }
        except Exception:
            pass

    link_data = {
        "token": token,
        "guest_id": payload.guest_id,
        "guest_name": guest["full_name"],
        "expires_at": expires_at.isoformat(),
        "used": False,
    }
    store.links[token] = link_data
    url = f"/register/{token}"
    add_notification(f"Registration link generated for {guest['full_name']}", "registration")
    return {
        "token": token,
        "registration_url": url,
        "expires_in_seconds": LINK_VALIDITY_HOURS * 3600,
        "one_time_use": True,
    }


@app.get("/registration/link/{token}")
def validate_registration_link(token: str) -> Dict[str, Any]:
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("registration_links")
                .select("token, guest_id, expires_at, used, guests(full_name)")
                .eq("token", token)
                .limit(1)
                .execute()
            )
            if response.data:
                row = response.data[0]
                if row["used"]:
                    raise HTTPException(status_code=410, detail="Link already used")
                if datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) <= now_utc():
                    raise HTTPException(status_code=410, detail="Link expired")
                return {
                    "valid": True,
                    "guest_id": row["guest_id"],
                    "guest_name": row.get("guests", {}).get("full_name", "Guest"),
                    "expires_at": row["expires_at"],
                }
        except HTTPException:
            raise
        except Exception:
            pass

    link = store.links.get(token)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link["used"]:
        raise HTTPException(status_code=410, detail="Link already used")

    if datetime.fromisoformat(link["expires_at"]) <= now_utc():
        raise HTTPException(status_code=410, detail="Link expired")

    return {
        "valid": True,
        "guest_id": link["guest_id"],
        "guest_name": link["guest_name"],
        "expires_at": link["expires_at"],
    }


@app.post("/registration/upload-face")
async def upload_face(token: str = Form(...), image: UploadFile = File(...)) -> Dict[str, Any]:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    content = await image.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Image is empty")
    if len(content) > MAX_FACE_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image exceeds 5MB limit")

    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("registration_links")
                .select("token, guest_id, expires_at, used")
                .eq("token", token)
                .limit(1)
                .execute()
            )
            if not response.data:
                raise HTTPException(status_code=404, detail="Link not found")
            link = response.data[0]
            if link["used"]:
                raise HTTPException(status_code=410, detail="Link already used")
            if datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00")) <= now_utc():
                raise HTTPException(status_code=410, detail="Link expired")

            guest = ensure_guest(link["guest_id"])
            filename = f"{guest['id']}_{int(now_utc().timestamp())}.jpg"
            supabase_gateway.client.storage.from_(supabase_gateway.bucket).upload(
                filename,
                content,
                {"content-type": image.content_type},
            )
            supabase_gateway.client.table("guests").update(
                {"face_image_path": f"{supabase_gateway.bucket}/{filename}"}
            ).eq("id", guest["id"]).execute()
            supabase_gateway.client.table("registration_links").update(
                {"used": True, "used_at": now_utc().isoformat()}
            ).eq("token", token).execute()

            add_notification(
                f"Face registration completed for {guest['full_name']}",
                "registration",
            )
            return {"message": "Face uploaded successfully", "guest_id": guest["id"]}
        except HTTPException:
            raise
        except Exception:
            pass

    link = store.links.get(token)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link["used"]:
        raise HTTPException(status_code=410, detail="Link already used")
    if datetime.fromisoformat(link["expires_at"]) <= now_utc():
        raise HTTPException(status_code=410, detail="Link expired")

    guest = ensure_guest(link["guest_id"])
    filename = f"{guest['id']}_{int(now_utc().timestamp())}.jpg"
    guest["face_image_path"] = f"{supabase_gateway.bucket}/{filename}"
    link["used"] = True

    add_notification(f"Face registration completed for {guest['full_name']}", "registration")
    return {"message": "Face uploaded successfully", "guest_id": guest["id"]}


@app.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(user: Dict[str, Any] = Depends(get_current_user)) -> List[NotificationResponse]:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("notifications")
                .select("id, message, kind, created_at, is_read")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            return [NotificationResponse(**item) for item in (response.data or [])]
        except Exception:
            pass
    return [NotificationResponse(**item) for item in store.notifications]


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    _ = user
    if supabase_gateway.connected:
        try:
            response = (
                supabase_gateway.client.table("notifications")
                .update({"is_read": True})
                .eq("id", notification_id)
                .execute()
            )
            updated = (response.data or [None])[0]
            if updated:
                return updated
        except Exception:
            pass

    for item in store.notifications:
        if item["id"] == notification_id:
            item["is_read"] = True
            return item
    raise HTTPException(status_code=404, detail="Notification not found")


@app.get("/register/{token}", response_class=HTMLResponse)
def registration_page(token: str) -> str:
    template_path = "web/templates/register.html"
    with open(template_path, "r", encoding="utf-8") as template_file:
        html = template_file.read()
    return html.replace("{{TOKEN}}", token)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
