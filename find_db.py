import os
import glob

# Search for the database file
print("🔍 Searching for database files...")

# Check current directory
current_dir = os.getcwd()
print(f"\n📂 Current directory: {current_dir}")

# List all .db files
db_files = glob.glob("**/*.db", recursive=True)
print(f"\n📦 Database files found: {db_files}")

# Also check for .db-shm and .db-wal (SQLite journals)
journal_files = glob.glob("**/*.db-*", recursive=True)
print(f"📄 Journal files: {journal_files}")

# List all files
print("\n📋 All files in current directory:")
for f in os.listdir('.'):
    print(f"  - {f}")