from __future__ import annotations

import sys
import os
import threading
from pathlib import Path

from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QTimer

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import battery_monitor as bm


def create_qt_battery_icon(percent: int, is_charging: bool, has_error: bool = False) -> QIcon:
    """Draw a crisp, high-DPI battery tray icon with percentage and charge indicator."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if has_error:
        fill_color = QColor(230, 50, 50)       # Red
    elif is_charging:
        fill_color = QColor(40, 190, 70)       # Green
    elif percent <= 20:
        fill_color = QColor(230, 50, 50)       # Red
    elif percent <= 30:
        fill_color = QColor(240, 140, 20)      # Orange
    else:
        fill_color = QColor(30, 140, 240)      # Bright Blue

    # Battery body outline (rounded box)
    painter.setPen(fill_color)
    painter.setBrush(QColor(35, 35, 35, 230))
    painter.drawRoundedRect(6, 12, 48, 32, 4, 4)

    # Terminal cap on the right
    painter.setPen(Qt.NoPen)
    painter.setBrush(fill_color)
    painter.drawRoundedRect(54, 22, 6, 12, 2, 2)

    # Fill level inside battery
    fill_width = int((max(0, min(100, percent)) / 100.0) * 42)
    if fill_width > 0:
        painter.fillRect(9, 15, fill_width, 26, fill_color)

    # Percentage text below battery body
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 9, QFont.Bold)
    painter.setFont(font)
    text = f"{percent}%"
    painter.drawText(0, 44, 64, 20, Qt.AlignCenter, text)

    painter.end()
    return QIcon(pixmap)


class TrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon()
        self.menu = QMenu()
        self.is_running = False
        self.monitor_thread = None

        self.action_check = QAction("Check Now")
        self.action_pause = QAction("Pause Monitoring")
        self.action_startup = QAction("Start with Windows")
        self.action_startup.setCheckable(True)
        self.action_startup.setChecked(bm.is_startup_enabled())
        self.action_snooze_30 = QAction("Snooze 30 min")
        self.action_snooze_60 = QAction("Snooze 60 min")
        self.action_snooze_120 = QAction("Snooze 120 min")
        self.action_settings = QAction("Settings")
        self.action_quit = QAction("Quit")

        self.action_check.triggered.connect(self.check_now)
        self.action_pause.triggered.connect(self.toggle_pause)
        self.action_startup.triggered.connect(self.toggle_startup)
        self.action_settings.triggered.connect(self.open_settings)
        self.action_quit.triggered.connect(self.quit)

        self.action_snooze_30.triggered.connect(lambda: self.snooze(30))
        self.action_snooze_60.triggered.connect(lambda: self.snooze(60))
        self.action_snooze_120.triggered.connect(lambda: self.snooze(120))

        snooze_menu = QMenu("Snooze", self.menu)
        snooze_menu.addAction(self.action_snooze_30)
        snooze_menu.addAction(self.action_snooze_60)
        snooze_menu.addAction(self.action_snooze_120)

        self.menu.addAction(self.action_check)
        self.menu.addAction(self.action_pause)
        self.menu.addAction(self.action_startup)
        self.menu.addMenu(snooze_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_settings)
        self.menu.addSeparator()
        self.menu.addAction(self.action_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("HA Battery Monitor - Starting...")

        bm.load_settings()

        # Fallback default icon before first battery check
        self.tray.setIcon(create_qt_battery_icon(100, False, False))

        # Initial icon display
        self.update_tray_display()
        self.tray.activated.connect(self.on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

        # Connect battery_monitor tray updates directly to Qt
        bm.update_tray_icon = self.update_tray_display
        bm.setup_tray = lambda: None

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=bm.run_monitoring,
            args=(bm.app_settings.get("monitoring", {}).get("check_interval", 60),),
            daemon=True
        )
        self.monitor_thread.start()
        self.refresh_pause_label()

        # Periodic refresh timer on Qt event loop (every 3 seconds)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_tray_display)
        self.ui_timer.start(3000)

    def update_tray_display(self):
        """Update system tray icon, tooltip, and menu state from current battery status."""
        try:
            # Re-check visibility in case explorer.exe tray was not yet ready during initial boot
            if not self.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray.show()

            battery = bm.check_battery_status()
            if battery:
                percent = int(battery.percent)
                is_charging = battery.power_plugged
                has_error = bm.last_error is not None
                icon = create_qt_battery_icon(percent, is_charging, has_error)
                self.tray.setIcon(icon)

                status_text = f"Battery: {percent}% ({'Charging' if is_charging else 'Not Charging'})"
                if bm.last_error:
                    status_text += f"\nError: {bm.last_error}"
                self.tray.setToolTip(status_text)
            else:
                self.tray.setToolTip("HA Battery Monitor - No battery detected")
        except Exception:
            pass

    def refresh_pause_label(self):
        paused = bm.app_settings.get("advanced", {}).get("paused", False)
        self.action_pause.setText("Resume Monitoring" if paused else "Pause Monitoring")

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings()

    def check_now(self):
        try:
            battery = bm.check_battery_status()
            if not battery:
                bm.show_notification("No battery detected on this system", alert_level="warning")
                return
            status_msg = f"Battery: {battery.percent}% ({'Charging' if battery.power_plugged else 'Not Charging'})"
            bm.show_notification(status_msg, alert_level="info")

            if not bm.app_settings.get("advanced", {}).get("paused", False):
                should_alert, alert_message, alert_level = bm.check_battery_alerts_v2(battery)
                if should_alert:
                    bm.show_notification(alert_message, alert_level=alert_level)
                    if bm.app_settings.get("audio", {}).get("enabled", True):
                        bm.play_sound(alert_level)
        except Exception as e:
            self.tray.showMessage("HA Battery Monitor", f"Check failed: {e}", QSystemTrayIcon.MessageIcon.Critical, 3000)

    def snooze(self, minutes: int):
        try:
            bm.set_snooze(minutes)
            self.tray.showMessage("HA Battery Monitor", f"Alerts snoozed for {minutes} minutes", QSystemTrayIcon.MessageIcon.Information, 3000)
        except Exception as e:
            self.tray.showMessage("HA Battery Monitor", f"Failed to snooze: {e}", QSystemTrayIcon.MessageIcon.Critical, 3000)

    def toggle_pause(self):
        try:
            adv = bm.app_settings.setdefault("advanced", {})
            adv["paused"] = not adv.get("paused", False)
            bm.save_settings()
            self.refresh_pause_label()
            bm.show_notification("Monitoring paused" if adv["paused"] else "Monitoring resumed", alert_level="info")
        except Exception as e:
            self.tray.showMessage("HA Battery Monitor", f"Pause toggle failed: {e}", QSystemTrayIcon.MessageIcon.Critical, 3000)

    def toggle_startup(self, checked: bool):
        try:
            bm.set_startup_enabled(checked)
            adv = bm.app_settings.setdefault("advanced", {})
            adv["start_with_windows"] = checked
            bm.save_settings()
            msg = "Start with Windows enabled" if checked else "Start with Windows disabled"
            self.tray.showMessage("HA Battery Monitor", msg, QSystemTrayIcon.MessageIcon.Information, 3000)
        except Exception as e:
            self.tray.showMessage("HA Battery Monitor", f"Failed to toggle startup: {e}", QSystemTrayIcon.MessageIcon.Critical, 3000)

    def open_settings(self):
        try:
            import subprocess
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--settings"]
            else:
                launcher = BASE_DIR / "app_launcher.py"
                if launcher.exists():
                    cmd = [sys.executable, str(launcher), "--settings"]
                else:
                    cmd = [sys.executable, str(BASE_DIR / "qt_gui.py")]
            subprocess.Popen(cmd, creationflags=creationflags)
        except Exception as e:
            self.tray.showMessage("HA Battery Monitor", f"Failed to open Settings: {e}", QSystemTrayIcon.MessageIcon.Critical, 3000)

    def quit(self):
        self.is_running = False
        self.tray.hide()
        QApplication.quit()

    def run(self):
        sys.exit(self.app.exec())


def main():
    app = TrayApp()
    app.run()


if __name__ == '__main__':
    main()
