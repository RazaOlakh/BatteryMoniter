import sys
import os
import time
import argparse
import shutil
from pathlib import Path

if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure working directory is project root and add to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    os.chdir(str(PROJECT_ROOT))
except Exception:
    pass

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def ensure_interactive_desktop():
    """No-op desktop check maintained for backward compatibility."""
    pass


def hide_and_detach_console():
    """Hide console window and detach process so closing any terminal does not affect the app."""
    if os.name == 'nt':
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
            null_out = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = null_out
            sys.stderr = null_out
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass


def main():
    """Main application launcher."""
    parser = argparse.ArgumentParser(
        description='Battery Monitor Pro - Complete Battery Management Solution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔋 Battery Monitor Pro v2.0 🔋

A comprehensive battery monitoring solution with:
  • Real-time battery monitoring and alerts
  • System tray integration with visual indicators
  • Configurable notification system
  • Professional GUI for settings management
  • Smart power management recommendations

Usage Examples:
  BatteryMonitor.exe                    # Start monitoring (default settings)
  BatteryMonitor.exe --settings         # Open settings GUI only
  BatteryMonitor.exe --interval 30      # Monitor every 30 seconds
  BatteryMonitor.exe --debug            # Enable verbose logging

System Tray Features:
  • Right-click for quick access to settings and status
  • Visual battery percentage display
  • Color-coded status indicators:
    🔵 Blue: Normal battery level (31-100%)
    🟠 Orange: Low battery warning (21-30%)
    🔴 Red: Critical battery level (≤20%) or system error
    🟢 Green: Charging in progress

Author: Battery Monitor Pro Team
Version: 2.0 Enhanced Edition
"""
    )
    parser.add_argument('--settings', action='store_true', help='Open settings GUI only (does not start monitoring)')
    parser.add_argument('--interval', type=int, default=60, help='Battery check interval in seconds (default: 60, minimum: 10)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose console logging')
    parser.add_argument('--console', '--foreground', action='store_true', help='Keep running in foreground console window (do not detach)')
    parser.add_argument('--service', action='store_true', help='Run directly as background service')
    parser.add_argument('--detach', '-d', action='store_true', help='Launch in detached background mode so closing the terminal does not close the tray')
    parser.add_argument('--fix-startup', action='store_true', help='Configure and repair Windows startup registry for 100%% silent windowless startup')
    parser.add_argument('--version', action='version', version='Battery Monitor Pro v2.0 Enhanced Edition')

    args = parser.parse_args()

    if args.fix_startup:
        print("🔧 Configuring 100% silent Windows startup registry...")
        try:
            from battery_monitor import set_startup_enabled
            if set_startup_enabled(True):
                print("✅ Windows startup registry updated successfully (using windowless pythonw)!")
            else:
                print("❌ Failed to update Windows startup registry.")
        except Exception as e:
            print(f"❌ Error updating startup: {e}")
        launch_detached(args)
        return

    if args.settings:
        print("🔋 Battery Monitor Pro - Opening Settings (Qt)...")
        try:
            import qt_gui
            qt_gui.main()
        except ImportError as e:
            err_msg = f"PySide6 is required to open the Settings GUI.\n\nPlease install it using:\npip install PySide6\n\n(Details: {e})"
            if os.name == "nt":
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, err_msg, "HA Battery Monitor", 0x10)
                except Exception:
                    pass
            print(f"❌ Error: {err_msg}")
            sys.exit(1)
        except Exception as e:
            err_msg = f"Failed to launch Settings GUI:\n\n{e}"
            if os.name == "nt":
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, err_msg, "HA Battery Monitor", 0x10)
                except Exception:
                    pass
            print(f"❌ Error launching Qt Settings: {e}")
            sys.exit(1)
        sys.exit(0)
    elif args.service:
        hide_and_detach_console()
        # Brief pause to let Windows desktop environment settle on logon
        if os.name == "nt":
            time.sleep(1)
        log_file = Path(__file__).parent / "battery_monitor_service.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service started (PID: {os.getpid()}, CWD: {os.getcwd()})\n")
        except Exception:
            pass
        try:
            from battery_monitor import main as monitor_main, check_and_repair_startup_registration
            check_and_repair_startup_registration()
            monitor_main(interval=args.interval, debug_mode=False)
        except Exception as e:
            try:
                import traceback
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service crash: {e}\n")
                    f.write(traceback.format_exc() + "\n")
            except Exception:
                pass
        else:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service exited normally.\n")
            except Exception:
                pass
        sys.exit(0)
    elif args.debug or args.console:
        print("🔋 Battery Monitor Pro - Starting in foreground...")
        print("[INFO] Running in foreground console session. Press Ctrl+C to stop.\n")
        if args.interval < 10:
            print("❌ Error: Minimum monitoring interval is 10 seconds")
            sys.exit(1)
        from battery_monitor import main as monitor_main, check_and_repair_startup_registration
        check_and_repair_startup_registration()
        try:
            monitor_main(interval=args.interval, debug_mode=args.debug)
        except KeyboardInterrupt:
            print("\n✅ Battery Monitor Pro stopped by user.")
            sys.exit(0)
        except ImportError as e:
            print(f"❌ Error: Missing required component - {e}")
            print("Please ensure all application files are present.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: Failed to start Battery Monitor Pro - {e}")
            sys.exit(1)
    else:
        is_windowless = False
        if os.name == 'nt':
            if sys.executable.lower().endswith("pythonw.exe"):
                is_windowless = True
            else:
                try:
                    import ctypes
                    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                    if not hwnd:
                        is_windowless = True
                except Exception:
                    pass

        if is_windowless:
            hide_and_detach_console()
            from battery_monitor import main as monitor_main, check_and_repair_startup_registration
            check_and_repair_startup_registration()
            monitor_main(interval=args.interval, debug_mode=False)
        else:
            launch_detached(args)


def launch_detached(args):
    """Launch the monitoring service in a detached background process."""
    import subprocess
    try:
        from battery_monitor import create_single_instance_check, cleanup_single_instance
        if not create_single_instance_check():
            print("⚠️ HA Battery Monitor is already running in the background.")
            print("💡 Look for the battery icon in your system tray (notification area).")
            sys.exit(0)
        cleanup_single_instance()
    except Exception:
        pass

    launcher_script = Path(__file__).resolve()
    pyw_script = launcher_script.with_suffix(".pyw")
    target_script = pyw_script if pyw_script.exists() else launcher_script

    python_exe = sys.executable

    # Prefer pythonw.exe on Windows for windowless execution
    if os.name == 'nt':
        dirname = os.path.dirname(python_exe)
        basename = os.path.basename(python_exe).lower()
        if basename == "python.exe" and os.path.exists(os.path.join(dirname, "pythonw.exe")):
            python_exe = os.path.join(dirname, "pythonw.exe")
        elif basename == "py.exe" and os.path.exists(os.path.join(dirname, "pyw.exe")):
            python_exe = os.path.join(dirname, "pyw.exe")
        elif not basename.endswith("w.exe"):
            cand = os.path.join(dirname, "pythonw.exe")
            if os.path.exists(cand):
                python_exe = cand
            else:
                which_w = shutil.which("pythonw.exe") or shutil.which("pythonw") or shutil.which("pyw.exe")
                if which_w:
                    python_exe = which_w

    if getattr(sys, "frozen", False):
        cmd = [python_exe, "--interval", str(args.interval), "--service"]
    else:
        cmd = [python_exe, str(target_script), "--interval", str(args.interval), "--service"]

    if args.debug:
        cmd.append("--debug")

    creationflags = 0
    if os.name == 'nt':
        creationflags = (
            getattr(subprocess, 'DETACHED_PROCESS', 0x00000008) |
            getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200) |
            getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        )

    try:
        proc = subprocess.Popen(
            cmd,
            creationflags=creationflags,
            close_fds=True,
            start_new_session=(os.name != 'nt'),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("=" * 60)
        print(f"🔋 Battery Monitor Pro launched in detached background mode (PID: {proc.pid}).")
        print("✨ The system tray icon is active.")
        print("🚪 You can now safely close this terminal window!")
        print("💡 To exit, right-click the system tray icon and select 'Quit'.")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting detached background process: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
