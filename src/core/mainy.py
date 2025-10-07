import asyncio
from pprint import pprint

from src.devaito.services.products import get_basic_variant_product_detail

tenantid = "picksssss"


async def main():
    details = await get_basic_variant_product_detail(tenant_id=tenantid, product_id=120)
    pprint(details)


if __name__ == "__main__":
    asyncio.run(main())
