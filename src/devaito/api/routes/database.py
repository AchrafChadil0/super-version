from fastapi import APIRouter, Header, HTTPException

from src.devaito.db.session import PoolMonitor

router = APIRouter(prefix="/database")


@router.get("/pool/tenant/status")
async def get_tenant_pool_status(
    tenant_id: str = Header(alias="x-tenant-id", example="picksssss")
):
    try:
        monitor = PoolMonitor()
        return monitor.get_pool_stats(tenant_id=tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve status") from e


@router.get("/pool/status")
async def get_pool_status():
    try:
        monitor = PoolMonitor()
        return monitor.get_all_pool_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve status") from e
