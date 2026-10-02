from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def get_health():
    """Health check endpoint.
    
    Returns:
        dict: {"status": "ok"} with HTTP 200 status code.
    """
    return {"status": "ok"}
