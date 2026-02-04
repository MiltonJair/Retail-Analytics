"""
REST API for Walmart Analytics
Run: uvicorn src.api.main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Walmart Analytics API",
    version="1.0.0",
    description="REST API for retail analytics"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/segments")
async def get_segments() -> Dict[str, Any]:
    """Get customer segments (RFM)"""
    return {
        "segments": [
            "Champions", "Loyal Customers", "Potential Loyalists",
            "At Risk", "Can't Lose Them", "Need Attention", "Lost"
        ],
        "count": 7
    }


@app.get("/api/churn-risk")
async def get_churn_risk() -> Dict[str, Any]:
    """Get churn risk distribution"""
    return {
        "categories": ["High", "Medium", "Low"],
        "distribution": {"High": 32, "Medium": 9, "Low": 6}
    }


@app.get("/api/forecasts")
async def get_forecasts(method: str = "sarima") -> Dict[str, Any]:
    """Get forecast by method"""
    forecasts = {
        "bottom-up": {"forecast": 2050000, "unit": "USD"},
        "top-down": {"forecast": 3130000, "unit": "USD"},
        "arima": {"forecast": 2400000, "unit": "USD"},
        "sarima": {"forecast": 2400000, "unit": "USD"}
    }
    
    if method not in forecasts:
        raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
    
    return {
        "method": method,
        "forecast": forecasts[method],
        "period": "30 days forward"
    }


@app.get("/api/kpis")
async def get_kpis() -> Dict[str, Any]:
    """Get key performance indicators"""
    return {
        "customers": 47,
        "stores": 20,
        "transactions": 10619,
        "departments": 7,
        "items": 26
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
