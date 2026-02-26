#!/usr/bin/env python
"""Simple wrapper to run main.py with proper output handling"""

import sys
import os

# Add UTF-8 support
import io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Import and run main
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    try:
        from main import main
        main()
    except SystemExit:
        pass
