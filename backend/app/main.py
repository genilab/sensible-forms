"""
Application entry point.

Responsible for:
- Creating the FastAPI application instance
- Registering API routers
- Attaching middleware (if needed)

This file should NOT contain business logic.
It is the composition root where components are wired together.
"""

# Example Code:
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import question_generation, form_deployment, analysis_assistant, uploads
from app.middleware.guardrails import GuardrailsMiddleware
from app.infrastructure.config.settings import settings

app = FastAPI(title="Sensible Forms API", version="1.0.0")

cors_origins = [
    origin.strip()
    for origin in settings.CORS_ALLOW_ORIGINS.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Minimal example of attaching cross-cutting middleware.
app.add_middleware(GuardrailsMiddleware)

# Register API routers
app.include_router(question_generation.router)
app.include_router(form_deployment.router)
app.include_router(analysis_assistant.router)
app.include_router(uploads.router)

# Health check endpoint for monitoring and testing purposes.
@app.get("/health")
def health_check():
    return {"status": "ok"}
