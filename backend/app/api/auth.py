from fastapi import APIRouter, Request, Response


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


USER = {
    "id": "u1",
    "name": "Analyst",
    "role": "analyst",
}


@router.get("/session")
def get_session(request: Request):
    token = request.cookies.get(
        "session_token"
    )

    if token == "valid":
        return {"user": USER}

    return {"user": None}


@router.post("/login")
def login(payload: dict, response: Response):
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        return {"user": None}

    response.set_cookie(
        key="session_token",
        value="valid",
        httponly=True,
        samesite="lax",
    )

    return {"user": USER}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}