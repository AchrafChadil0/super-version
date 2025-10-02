import asyncio
import time
import csv
from datetime import datetime
from pprint import pprint
from typing import Any, Dict

from src.devaito.db.session import dispose_tenant_engine
from src.devaito.schemas.products import CustomizableProductDetailDict
from src.devaito.services.products import (
    get_customizable_product_detail,
    warm_up_db,
    get_basic_single_product_detail,
    get_basic_variant_product_detail
)


class TestResult:
    """Store test result data."""

    def __init__(self, tenant_id: str, test_type: str, product_id: int,
                 elapsed_time: float, success: bool, error: str = None):
        self.tenant_id = tenant_id
        self.test_type = test_type
        self.product_id = product_id
        self.elapsed_time = elapsed_time
        self.success = success
        self.error = error
        self.timestamp = datetime.now().isoformat()


async def time_async_function(func, *args, **kwargs):
    """Helper to time async function execution."""
    start = time.perf_counter()
    try:
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed, True, None
    except Exception as e:
        elapsed = time.perf_counter() - start
        return None, elapsed, False, str(e)


async def test_tenant(tenant_id: str, product_ids: dict, results_list: list):
    """Test all product operations for a single tenant."""
    print(f"\n{'=' * 60}")
    print(f"Starting tests for tenant: {tenant_id}")
    print(f"{'=' * 60}")

    try:
        # Warm up database for this tenant
        await warm_up_db(tenant_id=tenant_id)
        print(f"✓ Database warmed up for {tenant_id}\n")

        # Test basic single product
        print(f"[{tenant_id}] Testing: get_basic_single_product_detail (product_id={product_ids['single']})")
        details, elapsed, success, error = await time_async_function(
            get_basic_single_product_detail,
            tenant_id=tenant_id,
            product_id=product_ids['single']
        )
        results_list.append(TestResult(
            tenant_id, "basic_single", product_ids['single'], elapsed, success, error
        ))
        if success:
            pprint(details)
            print(f"⏱️  Time taken: {elapsed:.4f} seconds\n")
        else:
            print(f"❌ Error: {error}\n")

        # Test basic variant product
        print(f"[{tenant_id}] Testing: get_basic_variant_product_detail (product_id={product_ids['variant']})")
        details, elapsed, success, error = await time_async_function(
            get_basic_variant_product_detail,
            tenant_id=tenant_id,
            product_id=product_ids['variant']
        )
        results_list.append(TestResult(
            tenant_id, "basic_variant", product_ids['variant'], elapsed, success, error
        ))
        if success:
            pprint(details)
            print(f"⏱️  Time taken: {elapsed:.4f} seconds\n")
        else:
            print(f"❌ Error: {error}\n")

        # Test customizable product
        print(f"[{tenant_id}] Testing: get_customizable_product_detail (product_id={product_ids['customizable']})")
        details, elapsed, success, error = await time_async_function(
            get_customizable_product_detail,
            tenant_id=tenant_id,
            product_id=product_ids['customizable']
        )
        results_list.append(TestResult(
            tenant_id, "customizable", product_ids['customizable'], elapsed, success, error
        ))
        if success:
            pprint(details)
            print(f"⏱️  Time taken: {elapsed:.4f} seconds\n")
        else:
            print(f"❌ Error: {error}\n")

        print(f"✓ All tests completed for {tenant_id}")

    except Exception as e:
        print(f"❌ Error occurred for tenant {tenant_id}: {e}")
    finally:
        await dispose_tenant_engine(tenant_id)
        print(f"✓ Cleanup complete for {tenant_id}")


def save_results_to_csv(results: list, filename: str = None):
    """Save test results to a CSV file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'tenant_id', 'test_type', 'product_id',
                      'elapsed_time_seconds', 'success', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow({
                'timestamp': result.timestamp,
                'tenant_id': result.tenant_id,
                'test_type': result.test_type,
                'product_id': result.product_id,
                'elapsed_time_seconds': f"{result.elapsed_time:.4f}",
                'success': result.success,
                'error': result.error or ''
            })

    print(f"\n✓ Results saved to: {filename}")
    return filename


async def main():
    # Define tenant configurations
    tenants = {
        "donotremove": {
            "single": 2,
            "variant": 8,
            "customizable": 62
        },
        "picksssss": {
            "single": 112,
            "variant": 51,
            "customizable": 62
        }
    }

    # List to store all test results
    results = []

    print("\n" + "=" * 60)
    print("MULTI-TENANT CONCURRENT TEST")
    print("=" * 60)
    print(f"Testing {len(tenants)} tenants concurrently...")

    start_total = time.perf_counter()

    # Run all tenant tests concurrently
    tasks = [
        test_tenant(tenant_id, product_ids, results)
        for tenant_id, product_ids in tenants.items()
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_total = time.perf_counter() - start_total

    print("\n" + "=" * 60)
    print(f"✓ ALL TESTS COMPLETED")
    print(f"⏱️  Total time for concurrent multi-tenant test: {elapsed_total:.4f} seconds")
    print("=" * 60)

    # Save results to CSV
    csv_filename = save_results_to_csv(results)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    print(f"Total tests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Average time: {sum(r.elapsed_time for r in results) / len(results):.4f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())