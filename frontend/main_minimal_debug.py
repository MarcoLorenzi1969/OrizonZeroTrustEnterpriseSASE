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
import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("orizon_backend")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    logger.debug(f"Verifying password for user")
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, "secret-key-change-in-production", algorithm="HS256")
    logger.debug(f"Created access token for user: {data.get('sub')}")
    return token

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
    logger.info("=== LOGIN REQUEST RECEIVED ===")
    logger.debug(f"Request headers: {dict(request.headers)}")

    email = None
    password = None

    content_type = request.headers.get("content-type", "")
    logger.debug(f"Content-Type: {content_type}")

    if "application/json" in content_type:
        body = await request.body()
        logger.debug(f"Raw body received (first 100 chars): {body[:100]}")
        try:
            json_data = json.loads(body)
            email = json_data.get("email")
            password = json_data.get("password")
            logger.info(f"JSON login attempt for email: {email}")
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
    elif "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        logger.info(f"Form login attempt for email: {email}")
    else:
        logger.error(f"Invalid Content-Type: {content_type}")
        raise HTTPException(status_code=400, detail="Content-Type must be application/json or application/x-www-form-urlencoded")

    if not email or not password:
        logger.warning("Missing email or password")
        raise HTTPException(status_code=400, detail="Email and password required")

    logger.debug(f"Querying database for user: {email}")
    result = await db.execute(
        text("SELECT id, email, full_name, hashed_password, is_active, role FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.first()

    if not user:
        logger.warning(f"User not found: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    logger.debug(f"User found: {user.email}, role: {user.role}, active: {user.is_active}")

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Invalid password for user: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {email}")
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": "dummy-refresh-token",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }

    logger.info(f"=== LOGIN SUCCESS for {email} ===")
    logger.debug(f"Response data: {json.dumps({**response_data, 'access_token': access_token[:20] + '...'}, indent=2)}")

    return response_data

@app.get("/health")
def health():
    logger.debug("Health check endpoint called")
    return {"status": "ok", "service": "orizon-ztc"}

@app.get("/api/v1/health")
def api_health():
    logger.debug("API health check endpoint called")
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/v1/debug/test")
def debug_test():
    """Debug endpoint to test API connectivity"""
    logger.info("Debug test endpoint called")
    return {
        "status": "ok",
        "message": "Backend is working",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f">>> Incoming request: {request.method} {request.url.path}")
    logger.debug(f">>> Client: {request.client.host if request.client else 'unknown'}")

    response = await call_next(request)

    logger.info(f"<<< Response status: {response.status_code}")
    return response
