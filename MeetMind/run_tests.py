"""
Quick test runner script for MeetMind backend.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py --cov        # With coverage
"""

import sys
import subprocess


def main():
    """Run pytest with appropriate arguments"""
    args = ["pytest"]
    
    # Add user arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    else:
        # Default: verbose with summary
        args.extend(["-v", "--tb=short"])
    
    # Run pytest
    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
