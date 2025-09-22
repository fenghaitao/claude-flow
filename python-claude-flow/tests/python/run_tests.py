"""
Test runner and utilities for Claude-Flow testing.

Provides convenient test execution with different test suites,
reporting, and coverage analysis.
"""

import asyncio
import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestRunner:
    """Comprehensive test runner for Claude-Flow."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests" / "python"
        self.src_dir = project_root / "src"
        self.results = {}
    
    def run_unit_tests(self, coverage: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """Run unit tests."""
        print("🧪 Running unit tests...")
        
        cmd = ["python", "-m", "pytest", str(self.test_dir / "unit")]
        
        if coverage:
            cmd.extend(["--cov=claude_flow", "--cov-report=html", "--cov-report=term"])
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-x", "--tb=short"])  # Stop on first failure, short traceback
        
        result = self._run_command(cmd)
        self.results["unit_tests"] = result
        return result
    
    def run_integration_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        cmd = ["python", "-m", "pytest", str(self.test_dir / "integration")]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-m", "integration", "--tb=short"])
        
        result = self._run_command(cmd)
        self.results["integration_tests"] = result
        return result
    
    def run_e2e_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("🌍 Running end-to-end tests...")
        
        cmd = ["python", "-m", "pytest", str(self.test_dir / "e2e")]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-m", "e2e", "--tb=short"])
        
        result = self._run_command(cmd)
        self.results["e2e_tests"] = result
        return result
    
    def run_performance_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = ["python", "-m", "pytest", str(self.test_dir / "performance")]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-m", "performance", "--tb=short", "--benchmark-only"])
        
        result = self._run_command(cmd)
        self.results["performance_tests"] = result
        return result
    
    def run_all_tests(self, coverage: bool = True, verbose: bool = False) -> Dict[str, Any]:
        """Run all test suites."""
        print("🚀 Running complete test suite...")
        
        start_time = time.time()
        
        # Run each test suite
        self.run_unit_tests(coverage=coverage, verbose=verbose)
        self.run_integration_tests(verbose=verbose)
        self.run_e2e_tests(verbose=verbose)
        
        total_time = time.time() - start_time
        
        # Generate summary
        summary = self._generate_summary(total_time)
        self.results["summary"] = summary
        
        return self.results
    
    def run_quick_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run quick test suite (unit tests only)."""
        print("⚡ Running quick test suite...")
        
        cmd = ["python", "-m", "pytest", str(self.test_dir / "unit")]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["-x", "--tb=line", "-q"])  # Quick mode
        
        result = self._run_command(cmd)
        self.results["quick_tests"] = result
        return result
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> Dict[str, Any]:
        """Run specific test file or test function."""
        print(f"🎯 Running specific test: {test_path}")
        
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["--tb=short"])
        
        result = self._run_command(cmd)
        self.results["specific_test"] = result
        return result
    
    def check_code_quality(self) -> Dict[str, Any]:
        """Check code quality with linting and formatting."""
        print("🔍 Checking code quality...")
        
        quality_results = {}
        
        # Check with flake8 if available
        try:
            flake8_result = self._run_command([
                "python", "-m", "flake8", str(self.src_dir),
                "--max-line-length=100",
                "--ignore=E203,W503"
            ])
            quality_results["flake8"] = flake8_result
        except FileNotFoundError:
            quality_results["flake8"] = {"status": "skipped", "message": "flake8 not installed"}
        
        # Check with black if available
        try:
            black_result = self._run_command([
                "python", "-m", "black", "--check", str(self.src_dir)
            ])
            quality_results["black"] = black_result
        except FileNotFoundError:
            quality_results["black"] = {"status": "skipped", "message": "black not installed"}
        
        self.results["code_quality"] = quality_results
        return quality_results
    
    def generate_test_report(self, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        report = {
            "timestamp": time.time(),
            "project_root": str(self.project_root),
            "test_results": self.results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cwd": os.getcwd()
            }
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"📊 Test report saved to: {output_file}")
        
        return report
    
    def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run shell command and capture result."""
        try:
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            end_time = time.time()
            
            return {
                "command": " ".join(cmd),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": end_time - start_time,
                "success": result.returncode == 0
            }
        
        except Exception as e:
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0,
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate test execution summary."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for suite_name, result in self.results.items():
            if suite_name == "summary":
                continue
            
            if result.get("success"):
                # Parse pytest output for test counts (simplified)
                stdout = result.get("stdout", "")
                if "passed" in stdout:
                    # Basic parsing - could be enhanced
                    passed_tests += 1
            else:
                failed_tests += 1
            
            total_tests += 1
        
        return {
            "total_time": total_time,
            "total_suites": total_tests,
            "passed_suites": passed_tests,
            "failed_suites": failed_tests,
            "success_rate": passed_tests / max(1, total_tests),
            "overall_success": failed_tests == 0
        }
    
    def print_summary(self):
        """Print test execution summary."""
        if "summary" not in self.results:
            print("❌ No test summary available")
            return
        
        summary = self.results["summary"]
        
        print("\\n" + "="*60)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*60)
        
        print(f"Total execution time: {summary['total_time']:.2f} seconds")
        print(f"Total test suites: {summary['total_suites']}")
        print(f"Passed suites: {summary['passed_suites']}")
        print(f"Failed suites: {summary['failed_suites']}")
        print(f"Success rate: {summary['success_rate']:.1%}")
        
        if summary["overall_success"]:
            print("✅ All test suites passed!")
        else:
            print("❌ Some test suites failed")
        
        print("="*60)
        
        # Print individual suite results
        for suite_name, result in self.results.items():
            if suite_name == "summary":
                continue
            
            status = "✅ PASSED" if result.get("success") else "❌ FAILED"
            duration = result.get("duration", 0)
            print(f"{suite_name:20} {status} ({duration:.2f}s)")


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Claude-Flow Test Runner")
    
    parser.add_argument(
        "suite",
        nargs="?",
        default="all",
        choices=["unit", "integration", "e2e", "performance", "all", "quick"],
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting"
    )
    
    parser.add_argument(
        "--report",
        type=Path,
        help="Generate JSON report file"
    )
    
    parser.add_argument(
        "--quality-check",
        action="store_true",
        help="Run code quality checks"
    )
    
    parser.add_argument(
        "--test-path",
        help="Specific test file or function to run"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent.parent
    
    # Create test runner
    runner = TestRunner(project_root)
    
    # Run requested tests
    if args.test_path:
        runner.run_specific_test(args.test_path, verbose=args.verbose)
    elif args.suite == "unit":
        runner.run_unit_tests(coverage=not args.no_coverage, verbose=args.verbose)
    elif args.suite == "integration":
        runner.run_integration_tests(verbose=args.verbose)
    elif args.suite == "e2e":
        runner.run_e2e_tests(verbose=args.verbose)
    elif args.suite == "performance":
        runner.run_performance_tests(verbose=args.verbose)
    elif args.suite == "quick":
        runner.run_quick_tests(verbose=args.verbose)
    elif args.suite == "all":
        runner.run_all_tests(coverage=not args.no_coverage, verbose=args.verbose)
    
    # Run quality checks if requested
    if args.quality_check:
        runner.check_code_quality()
    
    # Generate report if requested
    if args.report:
        runner.generate_test_report(args.report)
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    if "summary" in runner.results:
        success = runner.results["summary"]["overall_success"]
        sys.exit(0 if success else 1)
    else:
        # Check individual test result
        for result in runner.results.values():
            if not result.get("success", True):
                sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()