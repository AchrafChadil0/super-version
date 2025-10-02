from fastapi import APIRouter, Header, HTTPException

from src.devaito.config.cache_config import cache_manager
from src.devaito.config.global_config import GlobalConfig

router = APIRouter(prefix="/cache")
config = GlobalConfig()


@router.delete("/tenant/all")
async def clear_all_tenant_cache(tenant_id: str = Header(alias="x-tenant-id")) -> dict:
    """Clear all cache entries for the tenant"""
    try:
        deleted_count = await cache_manager.delete_tenant_cache(tenant_id)
        return {
            "message": f"Successfully cleared cache for tenant {tenant_id}",
            "deleted_keys": deleted_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear cache: {str(e)}"
        ) from e


@router.delete("/tenant/pattern")
async def clear_tenant_cache_pattern(
    pattern: str, tenant_id: str = Header(alias="x-tenant-id", example="picksssss")
) -> dict:
    """Clear cache entries matching a pattern for the tenant"""
    try:
        deleted_count = await cache_manager.delete_tenant_cache(tenant_id, pattern)
        return {
            "message": f"Successfully cleared cache pattern '{pattern}' for tenant {tenant_id}",
            "deleted_keys": deleted_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear cache: {str(e)}"
        ) from e


@router.delete("/function/{function_name}")
async def clear_specific_function_cache(
    function_name: str,
    tenant_id: str = Header(alias="x-tenant-id", example="picksssss"),
) -> dict:
    """Clear cache for a specific function"""
    try:
        deleted = await cache_manager.delete_cache_by_function(
            tenant_id,
            function_name,
        )

        if deleted:
            return {"message": f"Successfully cleared cache for {function_name}"}
        else:
            return {"message": f"No cache found for {function_name}"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear cache: {str(e)}"
        ) from e


@router.get("/tenant/keys")
async def list_tenant_cache_keys(
    pattern: str = "*",
    tenant_id: str = Header(alias="x-tenant-id", example="picksssss"),
) -> dict:
    """List all cache keys for the tenant"""
    try:
        keys = await cache_manager.list_tenant_cache_keys(tenant_id, pattern)
        return {
            "client": config.AGENT_CLIENT,
            "tenant_id": tenant_id,
            "pattern": pattern,
            "keys": keys,
            "count": len(keys),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list cache keys: {str(e)}"
        ) from e


@router.get("/tenant/stats")
async def get_tenant_cache_stats(
    tenant_id: str = Header(alias="x-tenant-id", example="picksssss")
) -> dict:
    """Get cache statistics for the tenant"""
    try:
        stats = await cache_manager.get_cache_stats(tenant_id)
        return {"client": config.AGENT_CLIENT, "tenant_id": tenant_id, "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache stats: {str(e)}"
        ) from e
