import os
import glob

# Remove all test files
test_files = glob.glob("test_*.py") + glob.glob("clean_*.py")
for file in test_files:
    if os.path.exists(file):
        os.remove(file)
        print(f"Removed {file}")

# Also remove this cleanup script
if os.path.exists("cleanup_temp_files.py"):
    os.remove("cleanup_temp_files.py")

print("Cleanup complete!")