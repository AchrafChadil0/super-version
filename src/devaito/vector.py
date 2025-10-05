import asyncio
import time
from pprint import pprint

from src.devaito.services.products import (
    get_all_products_for_vectors,
    get_product_for_vector,
)


async def main():
    tenant_id = "picksssss"  # Replace with actual tenant_id

    # Test 1: Get single product by ID
    print("=" * 80)
    print("TEST 1: Get single product for vector by ID")
    print("=" * 80)

    product_id = 15  # Replace with actual product_id
    start_time = time.time()

    product = await get_product_for_vector(tenant_id, product_id)

    elapsed_time = time.time() - start_time

    if product:
        print(f"\nProduct found (ID: {product_id}):")
        pprint(product)
    else:
        print(f"\nProduct not found (ID: {product_id})")

    print(f"\nTime taken: {elapsed_time} seconds")

    # Test 2: Get all products
    print("\n" + "=" * 80)
    print("TEST 2: Get all products for vector")
    print("=" * 80)

    start_time = time.time()

    all_products = await get_all_products_for_vectors(tenant_id)

    elapsed_time = time.time() - start_time

    print(f"\nTotal products found: {len(all_products)}")

    if all_products:
        print("\nFirst 3 products:")
        for product in all_products[:3]:
            pprint(product)
            print("-" * 40)

    print(f"\nTime taken: {elapsed_time} seconds")


if __name__ == "__main__":
    asyncio.run(main())
