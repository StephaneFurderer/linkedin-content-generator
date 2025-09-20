#!/usr/bin/env python3
"""
Test script for template categorization migration
Run this locally to test the database changes before deploying
"""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_migration():
    """Test the template categorization migration locally"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        print("Required: SUPABASE_URL and SUPABASE_ANON_KEY")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔍 Testing template categorization migration...")
        
        # Test 1: Check if new columns exist
        print("\n1. Checking new columns...")
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
            'category': 'attract',  # Should still work
            'format': 'belief_shift',  # Should still work
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
                'category': 'custom_category_test',  # Should work now
                'format': 'custom_format_test',  # Should work now
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
                
                print("\n🎉 Migration test completed successfully!")
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
        print(f"❌ Migration test failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Template Categorization Migration Test")
    print("=" * 50)
    
    success = test_migration()
    
    if success:
        print("\n✅ Migration is ready for deployment!")
        print("Next steps:")
        print("1. Test the frontend changes locally")
        print("2. Test AI categorization functionality")
        print("3. Deploy to staging environment")
        print("4. Deploy to production")
    else:
        print("\n❌ Migration test failed!")
        print("Please check the database schema and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
