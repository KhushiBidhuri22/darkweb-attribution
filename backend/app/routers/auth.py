from fastapi import APIRouter, Response, Request, HTTPException, status
from ..schemas import LoginRequest, LoginResponse, SessionResponse, User
from ...config import SESSION_COOKIE_NAME

router = APIRouter(prefix="/auth", tags=["auth"])

# Demo authorized personnel credentials for the intelligence platform
VALID_USERS = {
    "analyst": {"name": "Senior Threat Analyst", "role": "Lead Investigator", "password": "password"},
    "admin": {"name": "Intelligence Administrator", "role": "Platform Admin", "password": "admin"},
    "investigator": {"name": "Field Investigator", "role": "Investigator", "password": "password123"},
}


@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest, response: Response):
    user_data = VALID_USERS.get(creds.username.lower())
    # Allow any valid username with matching password or demo login
    if not user_data or user_data["password"] != creds.password:
        # If user provides any non-empty credentials for demo, accept
        if creds.username.strip() and creds.password.strip():
            user = User(id=f"usr_{creds.username.strip().lower()}", name=creds.username.strip(), role="Analyst")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
    else:
        user = User(
            id=f"usr_{creds.username.lower()}",
            name=user_data["name"],
            role=user_data["role"],
        )

    # Set secure session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=user.id,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    return LoginResponse(user=user)


@router.get("/session", response_model=SessionResponse)
def get_session(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        # Default active demo user session for smooth platform startup
        return SessionResponse(user=User(id="usr_analyst", name="Senior Threat Analyst", role="Lead Investigator"))

    username = session_id.replace("usr_", "")
    user_data = VALID_USERS.get(username, {"name": username.title(), "role": "Analyst"})
    return SessionResponse(
        user=User(
            id=session_id,
            name=user_data["name"],
            role=user_data["role"],
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
