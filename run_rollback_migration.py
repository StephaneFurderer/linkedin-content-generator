#!/usr/bin/env python3
"""
Rollback Migration Script for Enhanced Template Categorization
Run this if you need to revert the migration
"""

import os

def show_rollback_sql():
    """Display the rollback SQL for manual execution"""
    
    rollback_file = "src/tools/migrations/001_enhance_template_categorization_rollback.sql"
    
    if not os.path.exists(rollback_file):
        print(f"❌ Rollback file not found: {rollback_file}")
        return False
    
    with open(rollback_file, 'r') as f:
        rollback_sql = f.read()
    
    print("🚨 ROLLBACK Migration: Enhanced Template Categorization")
    print("=" * 70)
    print("⚠️  WARNING: This will remove all the new features!")
    print("⚠️  Make sure you want to rollback before proceeding!")
    print("=" * 70)
    print("📋 Execute this SQL in your Supabase SQL Editor:")
    print("=" * 70)
    print()
    print(rollback_sql)
    print("=" * 70)
    print()
    print("🔧 Instructions:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the SQL above")
    print("4. Click 'Run' to execute")
    print("5. Verify the rollback worked")
    print()
    print("🧪 After running the rollback, test with:")
    print("python3 test_template_migration.py")
    
    return True

if __name__ == "__main__":
    show_rollback_sql()
