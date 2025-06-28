#!/usr/bin/env python3
"""
Verify Upload State

Check what happened after uploading from draft to cloud.
"""

import os
import sys

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

def verify_upload_state():
    """Verify the state after uploading from draft"""
    
    print("🔍 VERIFYING POST-UPLOAD STATE")
    print("=" * 50)
    
    try:
        # Check temp directory
        print("📂 CHECKING TEMP DIRECTORY:")
        temp_dir = "/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system/temp"
        
        if os.path.exists(temp_dir):
            items = list(os.listdir(temp_dir))
            print(f"   Found {len(items)} items in temp:")
            
            db_files = [f for f in items if f.endswith('.db') and 'CAESER_GENERAL' in f]
            draft_dirs = [f for f in items if f == 'drafts']
            
            print(f"   🗄️  Database files: {len(db_files)}")
            for db in db_files[:3]:  # Show first 3
                print(f"      • {db}")
            if len(db_files) > 3:
                print(f"      ... and {len(db_files) - 3} more")
                
            print(f"   📝 Draft directories: {len(draft_dirs)}")
            
        # Check draft status
        print("\n📝 CHECKING DRAFT STATUS:")
        try:
            from src.gui.handlers.draft_manager import DraftManager
            draft_manager = DraftManager(temp_dir)
            
            has_draft = draft_manager.has_draft("CAESER_GENERAL")
            print(f"   Draft exists: {'✅ YES' if has_draft else '❌ NO'}")
            
            if has_draft:
                draft_info = draft_manager.get_draft_info("CAESER_GENERAL")
                print(f"   Draft created: {draft_info.get('draft_created_at', 'Unknown')}")
                print(f"   Has changes: {draft_info.get('has_unsaved_changes', 'Unknown')}")
                print("   ⚠️  Draft still exists after upload!")
            else:
                print("   ✅ Draft properly cleaned up after upload")
                
        except Exception as e:
            print(f"   ❌ Error checking draft: {e}")
        
        print("\n🎯 EXPECTED BEHAVIOR WHEN YOU REOPEN APP:")
        print("-" * 40)
        
        if has_draft:
            print("🔄 SCENARIO 1: Draft Still Exists (Cleanup Issue)")
            print("   1. Launch app: python3 src/main.py")
            print("   2. Go to Cloud Database → CAESER_GENERAL")
            print("   3. May see draft dialog (shouldn't happen)")
            print("   4. Choose 'Download Fresh' to get latest cloud version")
            print("   5. Should load with your uploaded changes")
            print("")
            print("   🚨 NOTE: Draft should have been cleaned up after upload")
        else:
            print("✅ SCENARIO 2: Draft Cleaned Up (Correct)")
            print("   1. Launch app: python3 src/main.py")
            print("   2. Go to Cloud Database → CAESER_GENERAL")
            print("   3. Should download directly (no draft dialog)")
            print("   4. Should load with your uploaded changes")
            print("   5. Save button should be DISABLED (no changes)")
            print("   6. Title should show 'CAESER_GENERAL (Cloud)'")
        
        print("\n🔬 WHAT YOU SHOULD SEE IN THE APP:")
        print("-" * 35)
        print("• Your flagged wells should be visible")
        print("• Changes you made should be preserved")
        print("• Save button DISABLED (no new changes)")
        print("• Title: 'CAESER_GENERAL (Cloud)' (not Draft)")
        print("• Local temp DB matches cloud version")
        
        print("\n🎯 NEXT TEST STEPS:")
        print("-" * 20)
        print("1. Launch app and load CAESER_GENERAL")
        print("2. Verify your changes are there")
        print("3. Make NEW changes")
        print("4. Close app → Choose 'Save as Draft'")
        print("5. Reopen → Should see draft dialog")
        print("6. Test choosing 'Continue with Draft' vs 'Download Fresh'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying upload state: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_upload_state()
    sys.exit(0 if success else 1)