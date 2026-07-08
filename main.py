import asyncio
import argparse
from src.models import ensure_indexes
from src.pipeline.loader import load_csv_to_db
from src.pipeline.processor import run_pipeline


async def main():
    parser = argparse.ArgumentParser(description="Saral Data Pipeline")
    parser.add_argument("--init-db", action="store_true", help="Initialize MongoDB indexes")
    parser.add_argument("--load-csv", action="store_true", help="Load CSV to MongoDB")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline in dry-run mode (first 10)")
    parser.add_argument("--run", action="store_true", help="Run the full pipeline")

    args = parser.parse_args()

    if args.init_db:
        print("Initializing MongoDB indexes...")
        await ensure_indexes()
        print("Indexes created successfully")

    if args.load_csv:
        print("Loading CSV to MongoDB...")
        count = await load_csv_to_db()
        print(f"Loaded {count} candidates to MongoDB")

    if args.run or args.dry_run:
        dry_run = bool(args.dry_run)
        print(f"Running pipeline (dry_run={dry_run})...")
        result = await run_pipeline(dry_run=dry_run)
        print(f"\nPipeline Results:")
        print(f"  Success: {result['success_count']}")
        print(f"  Failures: {result['failure_count']}")
        print(f"  Halted: {result['halted']}")
        print(f"  Threshold Met (950+): {result['threshold_met']}")

    if not any([args.init_db, args.load_csv, args.run, args.dry_run]):
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
