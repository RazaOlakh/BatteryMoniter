"""
Battery Monitor Pro - Windowless Python Launcher (.pyw)
Double-clicking this file runs Battery Monitor Pro without any terminal or console window.
"""
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    import app_launcher
    app_launcher.main()
