from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import json

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, "secret-key-change-in-production", algorithm="HS256")

DATABASE_URL = "postgresql+asyncpg://orizon:orizon_secure_2024@localhost:5432/orizon_ztc"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Orizon Zero Trust Connect")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str = "dummy-refresh-token"

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.post("/api/v1/auth/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    email = None
    password = None

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.body()
        try:
            json_data = json.loads(body)
            email = json_data.get("email")
            password = json_data.get("password")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    elif "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
    else:
        raise HTTPException(status_code=400, detail="Content-Type must be application/json or application/x-www-form-urlencoded")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    result = await db.execute(
        text("SELECT id, email, full_name, hashed_password, is_active, role FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": "dummy-refresh-token",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "orizon-ztc"}

@app.get("/api/v1/health")
def api_health():
    return {"status": "ok", "version": "1.0.0"}
