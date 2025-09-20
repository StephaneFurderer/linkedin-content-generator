#!/usr/bin/env python3
"""
Simple Production Migration Script for Enhanced Template Categorization
This script will show you the SQL to run manually in Supabase dashboard
"""

import os

def show_migration_sql():
    """Display the migration SQL for manual execution"""
    
    migration_file = "src/tools/migrations/001_enhance_template_categorization.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("🚀 Production Migration: Enhanced Template Categorization")
    print("=" * 70)
    print("📋 Execute this SQL in your Supabase SQL Editor:")
    print("=" * 70)
    print()
    print(migration_sql)
    print("=" * 70)
    print()
    print("🔧 Instructions:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the SQL above")
    print("4. Click 'Run' to execute")
    print("5. Verify the migration worked")
    print()
    print("🧪 After running the SQL, test with:")
    print("python3 test_template_migration.py")
    print()
    print("🚨 If something goes wrong, rollback with:")
    print("python3 run_rollback_migration.py")
    
    return True

if __name__ == "__main__":
    show_migration_sql()
