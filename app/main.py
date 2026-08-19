from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.users import router as users_router
from app.routes.system import router as system_router
from app.config.database import ensure_indexes

app = FastAPI(
    title="FastAPI Backend with MongoDB",
    version="1.0.0",
    description="Authentication, user management, IT Admin, audit logs, rate limiting and system settings.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    ensure_indexes()

@app.get("/", tags=["health"])
def root():
    return {"message": "FastAPI is running!"}

@app.get("/api/v1/health", tags=["health"])
def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(system_router)
