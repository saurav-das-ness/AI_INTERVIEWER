"""FastAPI application entrypoint for the AI Interview Tool."""

from fastapi import FastAPI

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.interview import router as interview_router
from app.api.routes.reporting import router as reporting_router


app = FastAPI(title="AI Interview Tool API", version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
	"""Return a lightweight status payload for local development."""

	return {
		"app": "AI Interview Tool API",
		"status": "ok",
	}


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(interview_router)
app.include_router(reporting_router)
