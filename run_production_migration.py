#!/usr/bin/env python3
"""
Production Migration Script for Enhanced Template Categorization
Run this to apply the migration to production Supabase
"""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Run the production migration"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🚀 Running Production Migration: Enhanced Template Categorization")
        print("=" * 70)
        print(f"📡 Connecting to: {supabase_url}")
        
        # Read the migration SQL file
        migration_file = "src/tools/migrations/001_enhance_template_categorization.sql"
        
        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("\n📋 Migration Steps:")
        print("1. Adding new columns to content_templates table")
        print("2. Removing CHECK constraints")
        print("3. Updating existing records")
        print("4. Creating new indexes")
        print("5. Adding documentation comments")
        
        # Execute the migration
        print("\n🔄 Executing migration...")
        
        # Split SQL into individual statements (Supabase doesn't support multi-statement SQL)
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement.startswith('--') or not statement:
                continue
                
            print(f"   Executing statement {i}/{len(statements)}...")
            
            try:
                # Execute the SQL statement
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                print(f"   ✅ Statement {i} executed successfully")
            except Exception as e:
                # Some statements might fail if columns already exist, which is fine
                if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                    print(f"   ⚠️  Statement {i} skipped (already applied or not needed): {e}")
                else:
                    print(f"   ❌ Statement {i} failed: {e}")
                    return False
        
        print("\n🎉 Migration completed successfully!")
        
        # Test the migration
        print("\n🧪 Testing migration results...")
        return test_migration_results(supabase)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def test_migration_results(supabase: Client):
    """Test that the migration worked correctly"""
    
    try:
        # Test 1: Check if new columns exist
        print("1. Checking new columns...")
        result = supabase.table('content_templates').select('*').limit(1).execute()
        
        if result.data:
            template = result.data[0]
            new_columns = [
                'parent_template_id', 'ai_categorized', 'ai_tags', 
                'custom_category', 'custom_format', 'categorization_confidence'
            ]
            
            for col in new_columns:
                if col in template:
                    print(f"   ✅ {col} column exists")
                else:
                    print(f"   ❌ {col} column missing")
                    return False
        
        # Test 2: Test inserting with new fields
        print("\n2. Testing new field insertion...")
        test_template = {
            'title': 'Migration Test Template',
            'content': 'This is a test template for migration validation',
            'category': 'attract',
            'format': 'belief_shift',
            'author': 'Test Author',
            'ai_categorized': True,
            'ai_tags': ['test-tag1', 'test-tag2'],
            'custom_category': False,
            'custom_format': False,
            'categorization_confidence': 0.95
        }
        
        insert_result = supabase.table('content_templates').insert(test_template).execute()
        
        if insert_result.data:
            test_id = insert_result.data[0]['id']
            print(f"   ✅ Test template created with ID: {test_id}")
            
            # Test 3: Test custom category/format
            print("\n3. Testing custom category/format...")
            custom_template = {
                'title': 'Custom Category Test',
                'content': 'Testing custom categorization',
                'category': 'custom_category_test',
                'format': 'custom_format_test',
                'author': 'Test Author',
                'custom_category': True,
                'custom_format': True,
                'ai_tags': ['custom-test']
            }
            
            custom_result = supabase.table('content_templates').insert(custom_template).execute()
            
            if custom_result.data:
                custom_id = custom_result.data[0]['id']
                print(f"   ✅ Custom template created with ID: {custom_id}")
                
                # Clean up test data
                print("\n4. Cleaning up test data...")
                supabase.table('content_templates').delete().eq('id', test_id).execute()
                supabase.table('content_templates').delete().eq('id', custom_id).execute()
                print("   ✅ Test data cleaned up")
                
                print("\n🎉 Migration validation completed successfully!")
                print("✅ All new columns exist")
                print("✅ Standard categories/formats still work")
                print("✅ Custom categories/formats work")
                print("✅ AI categorization fields work")
                return True
            else:
                print("   ❌ Failed to create custom template")
                return False
        else:
            print("   ❌ Failed to create test template")
            return False
            
    except Exception as e:
        print(f"❌ Migration validation failed: {e}")
        return False

def main():
    """Main function"""
    print("🚨 PRODUCTION MIGRATION WARNING 🚨")
    print("This will modify your production Supabase database!")
    print("Make sure you have the rollback script ready if needed.")
    print("=" * 70)
    
    response = input("\nDo you want to proceed? (yes/no): ").lower().strip()
    
    if response != 'yes':
        print("❌ Migration cancelled by user")
        sys.exit(0)
    
    success = run_migration()
    
    if success:
        print("\n🎉 Production migration completed successfully!")
        print("Next steps:")
        print("1. Test the new functionality in the frontend")
        print("2. Implement copy template functionality")
        print("3. Add AI categorization features")
        print("4. Update frontend to use new fields")
    else:
        print("\n❌ Production migration failed!")
        print("Check the errors above and consider running the rollback script:")
        print("python3 run_rollback_migration.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
