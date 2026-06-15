#!/usr/bin/env python3

"""

Simple Database Update Script

Quick and easy way to update the HuggingFace models database

"""

 

import argparse

import sys

from pathlib import Path

 

def main():

    parser = argparse.ArgumentParser(description="Update HuggingFace Models Database")

    parser.add_argument("--quick", action="store_true", help="Quick update with popular models only")

    parser.add_argument("--full", action="store_true", help="Full database update (all models)")

    parser.add_argument("--search", type=str, help="Search and update specific model types")

    parser.add_argument("--limit", type=int, default=1000, help="Limit number of models to update")

    parser.add_argument("--db-path", type=str, default="db/hf_models.db", help="Database path")

   

    args = parser.parse_args()

   

    print("🗄️ HuggingFace Database Update Tool")

    print("=" * 50)

   

    # Ensure db directory exists

    db_dir = Path(args.db_path).parent

    db_dir.mkdir(exist_ok=True)

    print(f"📁 Database location: {args.db_path}")

   

    if args.quick:

        print("\n🚀 Quick Update Mode")

        print("   Updating with popular models only...")

        try:

            from populate_hf_database import HuggingFaceDatabasePopulator

            populator = HuggingFaceDatabasePopulator(args.db_path)

            populator.populate_popular_models(limit=args.limit)

            print("✅ Quick update completed!")

        except ImportError:

            print("❌ Error: populate_hf_database.py not found")

            return 1

   

    elif args.full:

        print("\n🔄 Full Update Mode")

        print("   Updating entire database (this may take a while)...")

        try:

            from populate_hf_database import HuggingFaceDatabasePopulator

            populator = HuggingFaceDatabasePopulator(args.db_path)

            populator.populate_all_models()

            print("✅ Full update completed!")

        except ImportError:

            print("❌ Error: populate_hf_database.py not found")

            return 1

   

    elif args.search:

        print(f"\n🔍 Search Update Mode")

        print(f"   Searching for: {args.search}")

        try:

            from populate_hf_database import HuggingFaceDatabasePopulator

            populator = HuggingFaceDatabasePopulator(args.db_path)

            populator.populate_models_by_search(args.search, limit=args.limit)

            print(f"✅ Search update completed for '{args.search}'!")

        except ImportError:

            print("❌ Error: populate_hf_database.py not found")

            return 1

   

    else:

        print("\n📋 Available Options:")

        print("   --quick     Quick update with popular models")

        print("   --full      Full database update (all models)")

        print("   --search    Search and update specific model types")

        print("   --limit     Limit number of models (default: 1000)")

        print("\n💡 Example usage:")

        print("   python update_database.py --quick")

        print("   python update_database.py --search image-classification")

        print("   python update_database.py --full --limit 5000")

   

    # Show database stats

    try:

        import sqlite3

        with sqlite3.connect(args.db_path) as conn:

            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM models')

            count = cursor.fetchone()[0]

            print(f"\n📊 Database contains {count:,} models")

    except Exception as e:

        print(f"\n⚠️ Could not read database stats: {e}")

   

    return 0

 

if __name__ == "__main__":

    sys.exit(main())