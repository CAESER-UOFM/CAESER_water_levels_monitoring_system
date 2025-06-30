#!/usr/bin/env python3
"""
Master Test Runner
Runs all recharge system tests and generates comprehensive report.

Created by Claude Code for validation testing.
"""

import sys
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MASTER] %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'claude_testing' / 'master_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MasterTestRunner:
    """Runs all tests and generates comprehensive report."""
    
    def __init__(self):
        self.test_scripts = [
            'test_recharge_integration.py',
            'test_calculation_accuracy.py'
        ]
        self.results = {}
        
    def run_test_script(self, script_name):
        """Run a single test script."""
        logger.info(f"🚀 Running: {script_name}")
        
        script_path = PROJECT_ROOT / 'claude_testing' / script_name
        
        try:
            # Run the test script
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            success = result.returncode == 0
            
            self.results[script_name] = {
                'status': 'PASS' if success else 'FAIL',
                'returncode': result.returncode,
                'stdout_lines': len(result.stdout.splitlines()),
                'stderr_lines': len(result.stderr.splitlines()),
                'has_errors': len(result.stderr) > 0
            }
            
            if success:
                logger.info(f"✅ {script_name} completed successfully")
            else:
                logger.warning(f"⚠️ {script_name} failed with code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output preview: {result.stderr[:200]}...")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {script_name} timed out after 5 minutes")
            self.results[script_name] = {
                'status': 'TIMEOUT',
                'error': 'Test timed out after 5 minutes'
            }
            return False
            
        except Exception as e:
            logger.error(f"❌ {script_name} execution error: {e}")
            self.results[script_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            return False
    
    def check_dependencies(self):
        """Check if required dependencies are available."""
        logger.info("🔍 Checking dependencies...")
        
        required_modules = [
            'numpy', 'pandas', 'matplotlib', 'PyQt5'
        ]
        
        missing = []
        for module in required_modules:
            try:
                __import__(module)
                logger.debug(f"✅ {module} available")
            except ImportError:
                missing.append(module)
                logger.warning(f"❌ {module} missing")
        
        if missing:
            logger.error(f"Missing required modules: {missing}")
            return False
        
        logger.info("✅ All dependencies available")
        return True
    
    def check_database_availability(self):
        """Check if test databases are available."""
        logger.info("🗄️ Checking database availability...")
        
        db_paths = [
            PROJECT_ROOT / "databases" / "temp" / "CAESER_GENERAL.db",
            PROJECT_ROOT / "databases" / "CAESER_GENERAL.db",
        ]
        
        available_dbs = []
        for db_path in db_paths:
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                available_dbs.append((str(db_path), size_mb))
                logger.info(f"✅ Found database: {db_path.name} ({size_mb:.1f} MB)")
        
        if not available_dbs:
            logger.warning("⚠️ No test databases found - some tests may fail")
            
            # List what's actually in the databases folder
            db_dir = PROJECT_ROOT / "databases"
            if db_dir.exists():
                db_files = list(db_dir.glob("**/*.db"))
                if db_files:
                    logger.info("Available database files:")
                    for db_file in db_files:
                        logger.info(f"  - {db_file}")
                else:
                    logger.warning("No .db files found in databases folder")
            else:
                logger.warning("Databases folder not found")
        
        return len(available_dbs) > 0
    
    def generate_summary_report(self):
        """Generate comprehensive test summary."""
        logger.info("📊 Generating test summary report...")
        
        report_path = PROJECT_ROOT / 'claude_testing' / 'test_summary_report.md'
        
        # Count results
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results.values() if r.get('status') == 'PASS'])
        failed_tests = total_tests - passed_tests
        
        # Generate markdown report
        report_content = f"""# Recharge System Test Summary Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

- **Total Test Scripts:** {total_tests}
- **Passed:** {passed_tests}
- **Failed:** {failed_tests}
- **Success Rate:** {(passed_tests/total_tests*100):.1f}%

## Test Results

"""
        
        for script, result in self.results.items():
            status_emoji = "✅" if result.get('status') == 'PASS' else "❌"
            report_content += f"""### {status_emoji} {script}

- **Status:** {result.get('status', 'UNKNOWN')}
- **Return Code:** {result.get('returncode', 'N/A')}
"""
            
            if result.get('error'):
                report_content += f"- **Error:** {result['error']}\n"
            
            report_content += "\n"
        
        # Add recommendations
        report_content += """## Recommendations

"""
        
        if passed_tests == total_tests:
            report_content += """🎉 **All tests passed!** The recharge system appears to be working correctly.

✅ **Ready for Demo:** The system is ready for demonstration and production use.
"""
        else:
            report_content += f"""⚠️ **{failed_tests} test(s) failed.** Review the detailed logs for specific issues.

🔧 **Action Required:** Address the failing tests before demo/production use.
"""
        
        report_content += """
## Test Files Generated

- `test_results.log` - Detailed integration test logs
- `test_results.json` - Integration test results (JSON)
- `calculation_test_results.json` - Calculation accuracy results (JSON)
- `master_test.log` - Master test runner logs

## Next Steps

1. Review any failed tests and address issues
2. Run tests again after fixes
3. Consider additional edge case testing if needed
4. Document any limitations or requirements discovered

---
*Generated by Claude Code Testing Framework*
"""
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        logger.info(f"📄 Summary report saved to: {report_path}")
        
        # Also print summary to console
        print("\n" + "="*60)
        print("🏁 MASTER TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! System ready for demo.")
        else:
            print(f"\n⚠️ {failed_tests} TESTS FAILED. Check logs for details.")
        
        print("="*60)
    
    def run_all_tests(self):
        """Run all tests with comprehensive setup and reporting."""
        logger.info("🚀 Starting Master Test Suite")
        logger.info("="*80)
        
        # Pre-flight checks
        if not self.check_dependencies():
            logger.error("❌ Dependency check failed - aborting tests")
            return False
        
        db_available = self.check_database_availability()
        if not db_available:
            logger.warning("⚠️ No databases available - some tests may fail")
        
        # Run all test scripts
        all_passed = True
        for script in self.test_scripts:
            script_path = PROJECT_ROOT / 'claude_testing' / script
            if not script_path.exists():
                logger.error(f"❌ Test script not found: {script}")
                all_passed = False
                continue
                
            success = self.run_test_script(script)
            if not success:
                all_passed = False
            
            logger.info("-" * 40)
        
        # Generate comprehensive report
        self.generate_summary_report()
        
        return all_passed


if __name__ == "__main__":
    runner = MasterTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)