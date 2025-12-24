from fastapi import APIRouter

router = APIRouter(prefix="/misc", tags=["misc"])


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
