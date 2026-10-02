from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
title="LabGuardian AI API",
description="API para control inteligente, trazabilidad y análisis de riesgo de muestras clínicas.",
version="1.0.0",
)

# ─────────────────────────────────────────────

# CORS

# ─────────────────────────────────────────────

app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:5173"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

# ─────────────────────────────────────────────

# Root

# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
return {
"application": "LabGuardian AI",
"message": "LabGuardian AI API is running",
"version": "1.0.0",
"status": "online",
}

# ─────────────────────────────────────────────

# Health Check

# ─────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
return {
"status": "healthy",
"service": "LabGuardian AI API",
}
