"""
REST API with authentication using FastAPI + JWT.

Run it:
    pip install fastapi uvicorn "python-jose[cryptography]" "passlib[bcrypt]" python-multipart
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs to test everything in the browser.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

# --- Config ---------------------------------------------------------------
# reads SECRET_KEY from the environment (e.g. a .env file) so it's never
# hardcoded/committed; falls back to a dev-only default if not set
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Easiest Auth API")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tells FastAPI where clients should go to get a token (used by the docs UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- "Database" -------------------------------------------------------------
# just a dict in memory -> data disappears when the server restarts.
# swap this for a real DB (SQLite/Postgres) once you need persistence.
fake_users_db: dict[str, dict] = {}


# --- Models -----------------------------------------------------------------
class UserIn(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Helpers ------------------------------------------------------------
def create_access_token(username: str) -> str:
    # JWT payload: who the token is for ("sub") + when it expires ("exp")
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    # decodes/validates the JWT sent in the "Authorization: Bearer <token>" header
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise credentials_error
    except JWTError:
        raise credentials_error
    return fake_users_db[username]


# --- Routes -------------------------------------------------------------
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserIn):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already taken")
    fake_users_db[user.username] = {
        "username": user.username,
        "hashed_password": pwd_context.hash(user.password),
    }
    return {"message": "User created successfully"}


@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm expects standard form fields: username & password
    user = fake_users_db.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=create_access_token(user["username"]))


@app.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}


@app.get("/")
def root():
    return {"message": "API is running. Go to /docs to try it out."}
