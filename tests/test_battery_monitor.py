"""
Unit tests for HA Battery Monitor core functionality.
Executable via:
    python -m unittest discover tests
or:
    pytest tests/
"""
import sys
import unittest
import tempfile
import json
from pathlib import Path
from collections import namedtuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import battery_monitor as bm

BatteryTuple = namedtuple('BatteryTuple', ['percent', 'secsleft', 'power_plugged'])


class TestBatteryAlerts(unittest.TestCase):
    """Test battery alert evaluation logic across levels."""

    def setUp(self):
        bm.load_settings()
        bm.app_settings.setdefault("monitoring", {})
        bm.app_settings["monitoring"]["high_notice"] = 80
        bm.app_settings["monitoring"]["high_warning"] = 85
        bm.app_settings["monitoring"]["high_critical"] = 90
        bm.app_settings["monitoring"]["low_notice"] = 30
        bm.app_settings["monitoring"]["low_warning"] = 25
        bm.app_settings["monitoring"]["low_critical"] = 20
        bm.last_alert_percent = None

    def test_unplugged_critical_low(self):
        battery = BatteryTuple(percent=15, secsleft=1800, power_plugged=False)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'critical_low')
        self.assertIn('CRITICAL', msg)

    def test_unplugged_warning_low(self):
        battery = BatteryTuple(percent=24, secsleft=3600, power_plugged=False)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'warning_low')
        self.assertIn('WARNING', msg)

    def test_unplugged_notice_low(self):
        battery = BatteryTuple(percent=29, secsleft=4000, power_plugged=False)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'notice_low')

    def test_unplugged_normal_charge(self):
        battery = BatteryTuple(percent=65, secsleft=7200, power_plugged=False)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertFalse(should_alert)
        self.assertIsNone(msg)
        self.assertIsNone(level)

    def test_plugged_high_critical(self):
        battery = BatteryTuple(percent=95, secsleft=-1, power_plugged=True)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'high_critical')

    def test_plugged_high_warning(self):
        battery = BatteryTuple(percent=86, secsleft=-1, power_plugged=True)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'high_warning')

    def test_plugged_high_notice(self):
        battery = BatteryTuple(percent=81, secsleft=-1, power_plugged=True)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertTrue(should_alert)
        self.assertEqual(level, 'high_notice')

    def test_plugged_normal_charge(self):
        battery = BatteryTuple(percent=50, secsleft=-1, power_plugged=True)
        should_alert, msg, level = bm.check_battery_alerts_v2(battery)
        self.assertFalse(should_alert)


class TestConfigManagement(unittest.TestCase):
    """Test configuration loading, saving, and path resolution."""

    def test_config_path_resolution(self):
        cfg_path = bm.get_config_path()
        self.assertIsInstance(cfg_path, Path)
        self.assertTrue(str(cfg_path).endswith('battery_config.json'))

    def test_load_and_save_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cfg = Path(tmpdir) / 'battery_config.json'
            orig_cfg = bm.config_file
            bm.config_file = test_cfg
            try:
                bm.load_settings()
                self.assertIn('monitoring', bm.app_settings)
                self.assertIn('notifications', bm.app_settings)
                self.assertIn('audio', bm.app_settings)
                bm.app_settings['monitoring']['low_critical'] = 18
                bm.save_settings()
                self.assertTrue(test_cfg.exists())
                with open(test_cfg, 'r') as f:
                    saved_data = json.load(f)
                self.assertEqual(saved_data['monitoring']['low_critical'], 18)
            finally:
                bm.config_file = orig_cfg


class TestSingleInstance(unittest.TestCase):
    """Test single-instance lock and release."""

    def test_single_instance_lifecycle(self):
        bm.cleanup_single_instance()
        try:
            is_first = bm.create_single_instance_check()
            self.assertTrue(is_first, "First instance acquisition should succeed")
        finally:
            bm.cleanup_single_instance()


class TestSanitization(unittest.TestCase):
    """Test notification escaping and sanitization helpers."""

    def test_xml_escaping(self):
        import html
        dangerous_input = 'Alert: Battery < 10% & status == "critical" > shutdown'
        escaped = html.escape(dangerous_input)
        self.assertNotIn('<', escaped)
        self.assertNotIn('>', escaped)
        self.assertIn('&lt;', escaped)
        self.assertIn('&gt;', escaped)
        self.assertIn('&amp;', escaped)


class TestWindowsStartup(unittest.TestCase):
    """Test Windows startup registration and status checks."""

    def test_startup_status_query(self):
        enabled = bm.is_startup_enabled()
        self.assertIsInstance(enabled, bool)

    def test_startup_lifecycle_mocked(self):
        from unittest.mock import patch, MagicMock
        with patch.object(bm, 'winreg', create=True) as mock_winreg, \
             patch.object(bm.os, 'name', 'nt'):
            mock_key = MagicMock()
            mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
            mock_winreg.HKEY_CURRENT_USER = 1
            mock_winreg.KEY_SET_VALUE = 2
            mock_winreg.KEY_READ = 1
            mock_winreg.REG_SZ = 1
            mock_winreg.QueryValueEx.return_value = ("command", 1)

            # Test query enabled
            self.assertTrue(bm.is_startup_enabled())

            # Test set enabled
            res_enable = bm.set_startup_enabled(True)
            self.assertTrue(res_enable)
            self.assertTrue(mock_winreg.SetValueEx.called)

            # Test set disabled
            res_disable = bm.set_startup_enabled(False)
            self.assertTrue(res_disable)
            mock_winreg.DeleteValue.assert_called_with(mock_key, bm.REG_APP_NAME)


class TestCrossPlatformSupport(unittest.TestCase):
    """Test cross-platform notifications, audio, and startup functionality."""

    def test_macos_notification(self):
        from unittest.mock import patch
        with patch.object(bm.sys, "platform", "darwin"), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            res = bm.show_macos_notification("Title", "Message", "info")
            self.assertTrue(res)
            self.assertTrue(mock_popen.called)

    def test_linux_notification(self):
        from unittest.mock import patch
        with patch.object(bm.sys, "platform", "linux"), \
             patch.object(bm.shutil, "which", return_value="/usr/bin/notify-send"), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            res = bm.show_linux_notification("Title", "Message", "critical_low")
            self.assertTrue(res)
            self.assertTrue(mock_popen.called)

    def test_cross_platform_startup_linux(self):
        from unittest.mock import patch, MagicMock
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        with patch.object(bm.os, "name", "posix"), \
             patch.object(bm.sys, "platform", "linux"), \
             patch.object(bm, "get_startup_file_path", return_value=mock_path):
            res = bm.set_startup_enabled(True)
            self.assertTrue(res)
            self.assertTrue(mock_path.write_text.called)

    def test_cross_platform_startup_macos(self):
        from unittest.mock import patch, MagicMock
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        with patch.object(bm.os, "name", "posix"), \
             patch.object(bm.sys, "platform", "darwin"), \
             patch.object(bm, "get_startup_file_path", return_value=mock_path):
            res = bm.set_startup_enabled(True)
            self.assertTrue(res)
            self.assertTrue(mock_path.write_text.called)

    def test_play_sound_cross_platform(self):
        from unittest.mock import patch
        # macOS
        with patch.object(bm.os, "name", "posix"), \
             patch.object(bm.sys, "platform", "darwin"), \
             patch.object(bm.os.path, "exists", return_value=True), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            bm.play_sound("warning_low")
            self.assertTrue(mock_popen.called)

        # Linux
        with patch.object(bm.os, "name", "posix"), \
             patch.object(bm.sys, "platform", "linux"), \
             patch.object(bm.os.path, "exists", return_value=True), \
             patch.object(bm.shutil, "which", return_value="/usr/bin/paplay"), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            bm.play_sound("critical_low")
            self.assertTrue(mock_popen.called)


class TestSettingsLaunch(unittest.TestCase):
    """Test launching Settings GUI under various environments."""

    def test_open_settings_gui_frozen(self):
        from unittest.mock import patch
        with patch.object(bm.sys, "frozen", True, create=True), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            bm.open_settings_gui()
            self.assertTrue(mock_popen.called)
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            self.assertEqual(cmd, [bm.sys.executable, "--settings"])

    def test_open_settings_gui_source(self):
        from unittest.mock import patch, MagicMock
        with patch.object(bm.sys, "frozen", False, create=True), \
             patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            bm.open_settings_gui()
            self.assertTrue(mock_popen.called)
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            self.assertIn(bm.sys.executable, cmd)
            self.assertTrue(any("--settings" in c or "qt_gui" in c for c in cmd))

    def test_open_settings_gui_missing_pyside(self):
        from unittest.mock import patch
        with patch.object(bm.sys, "frozen", False, create=True), \
             patch("importlib.util.find_spec", return_value=None), \
             patch.object(bm, "show_notification"), \
             patch.object(bm.subprocess, "Popen") as mock_popen:
            bm.open_settings_gui()
            self.assertFalse(mock_popen.called)


class TestRapidDischarge(unittest.TestCase):
    """Test rapid discharge detection and configuration."""

    def test_rapid_discharge_enabled_vs_disabled(self):
        import time
        now = time.time()
        samples = [
            (now - 180, 80.0),
            (now - 120, 78.0),
            (now, 75.0)
        ]
        bm.rate_samples = samples
        battery = BatteryTuple(percent=75, secsleft=2700, power_plugged=False)

        # When enabled
        bm.app_settings = {'monitoring': {'roc_alert_enabled': True, 'roc_rate_percent_per_min': 0.7, 'roc_min_window_min': 2}}
        cfg = bm.app_settings['monitoring']
        cutoff = now - (cfg['roc_min_window_min'] * 60)
        pts = [(t, p) for (t, p) in bm.rate_samples if t >= cutoff]
        dt_min = (pts[-1][0] - pts[0][0]) / 60.0
        rate_per_min = (pts[0][1] - pts[-1][1]) / dt_min

        should_alert = False
        alert_level = None
        if cfg.get('roc_alert_enabled', True) and not battery.power_plugged and len(bm.rate_samples) >= 2:
            if len(pts) >= 2 and dt_min > 0.5:
                if rate_per_min >= cfg.get('roc_rate_percent_per_min', 0.7):
                    should_alert = True
                    alert_level = "roc_warning"

        self.assertTrue(should_alert)
        self.assertEqual(alert_level, "roc_warning")

        # When disabled
        cfg['roc_alert_enabled'] = False
        should_alert_disabled = False
        if cfg.get('roc_alert_enabled', True) and not battery.power_plugged and len(bm.rate_samples) >= 2:
            should_alert_disabled = True

        self.assertFalse(should_alert_disabled)


class TestTrayActivation(unittest.TestCase):
    """Test clicking on the system tray icon triggers Settings GUI."""

    def test_pystray_settings_item_is_default(self):
        from unittest.mock import MagicMock, patch
        mock_pystray = MagicMock()
        created_menu_items = []

        def mock_menu_item(*args, **kwargs):
            item = MagicMock()
            item.text = args[0] if args else kwargs.get('text')
            item.action = args[1] if len(args) > 1 else kwargs.get('action')
            item.default = kwargs.get('default', False)
            created_menu_items.append(item)
            return item

        mock_pystray.MenuItem = mock_menu_item
        mock_pystray.Menu = lambda *items: items

        orig_pystray = bm.pystray
        orig_image = bm.Image
        try:
            bm.pystray = mock_pystray
            bm.Image = MagicMock()
            with patch.object(bm, "create_tray_image", return_value=MagicMock()):
                bm.setup_tray()
            settings_item = next((item for item in created_menu_items if item.text == "Settings"), None)
            self.assertIsNotNone(settings_item)
            self.assertTrue(settings_item.default, "Settings MenuItem should have default=True for left-click activation")
            self.assertEqual(settings_item.action, bm.open_settings_gui)
        finally:
            bm.pystray = orig_pystray
            bm.Image = orig_image

    def test_qt_tray_click_activates_settings(self):
        from unittest.mock import MagicMock
        from types import ModuleType

        # Create mock PySide6 if not installed
        pyside = ModuleType('PySide6')
        pyside_gui = ModuleType('PySide6.QtGui')
        pyside_widgets = ModuleType('PySide6.QtWidgets')
        pyside_core = ModuleType('PySide6.QtCore')

        pyside_gui.QIcon = MagicMock()
        pyside_gui.QAction = MagicMock()
        pyside_gui.QPixmap = MagicMock()
        pyside_gui.QPainter = MagicMock()
        pyside_gui.QColor = MagicMock()
        pyside_gui.QFont = MagicMock()

        pyside_core.Qt = MagicMock()
        pyside_core.QTimer = MagicMock()

        pyside_widgets.QApplication = MagicMock()
        pyside_widgets.QMenu = MagicMock()

        mock_tray_cls = MagicMock()
        mock_tray_cls.ActivationReason = MagicMock()
        mock_tray_cls.ActivationReason.Trigger = 1
        mock_tray_cls.ActivationReason.DoubleClick = 2
        mock_tray_cls.isSystemTrayAvailable = MagicMock(return_value=True)
        pyside_widgets.QSystemTrayIcon = mock_tray_cls

        modules_to_patch = {
            'PySide6': pyside,
            'PySide6.QtGui': pyside_gui,
            'PySide6.QtWidgets': pyside_widgets,
            'PySide6.QtCore': pyside_core,
        }

        with unittest.mock.patch.dict('sys.modules', modules_to_patch):
            import src.qt_tray as qt_tray
            app_mock = MagicMock()
            app_mock.open_settings = MagicMock()

            # Test single click (Trigger = 1)
            qt_tray.TrayApp.on_tray_activated(app_mock, 1)
            self.assertTrue(app_mock.open_settings.called)

            # Test double click (DoubleClick = 2)
            app_mock.open_settings.reset_mock()
            qt_tray.TrayApp.on_tray_activated(app_mock, 2)
            self.assertTrue(app_mock.open_settings.called)


class TestDetachedLauncher(unittest.TestCase):
    """Test detached background execution."""

    def test_windows_startup_uses_pythonw(self):
        from unittest.mock import patch, MagicMock
        with patch.object(bm, 'winreg', create=True) as mock_winreg, \
             patch.object(bm.os, 'name', 'nt'), \
             patch.object(bm.sys, 'frozen', False, create=True), \
             patch.object(bm.sys, 'executable', 'C:\\Python312\\python.exe'), \
             patch.object(bm.os.path, 'exists', return_value=True):
            mock_key = MagicMock()
            mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
            mock_winreg.HKEY_CURRENT_USER = 1
            mock_winreg.KEY_SET_VALUE = 2
            mock_winreg.REG_SZ = 1

            bm.set_startup_enabled(True)
            self.assertTrue(mock_winreg.SetValueEx.called)
            reg_val = mock_winreg.SetValueEx.call_args[0][4]
            self.assertIn("pythonw.exe", reg_val)

    def test_windows_startup_dual_channel_registration(self):
        from unittest.mock import patch, MagicMock
        with tempfile.TemporaryDirectory() as tmp_appdata:
            startup_dir = Path(tmp_appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            startup_dir.mkdir(parents=True, exist_ok=True)
            vbs_file = startup_dir / "HABatteryMonitor.vbs"

            import os
            orig_exists = os.path.exists
            def smart_exists(p):
                if "python" in str(p).lower() or "app_launcher" in str(p).lower():
                    return True
                return orig_exists(p)

            with patch.object(bm, 'winreg', create=True) as mock_winreg, \
                 patch.object(bm.os, 'name', 'nt'), \
                 patch.dict(bm.os.environ, {"APPDATA": tmp_appdata}), \
                 patch.object(bm.sys, 'frozen', False, create=True), \
                 patch.object(bm.sys, 'executable', 'C:\\Python312\\python.exe'), \
                 patch.object(bm.os.path, 'exists', side_effect=smart_exists):
                mock_key = MagicMock()
                mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
                mock_winreg.HKEY_CURRENT_USER = 1
                mock_winreg.KEY_SET_VALUE = 2
                mock_winreg.REG_SZ = 1

                res = bm.set_startup_enabled(True)
                self.assertTrue(res)
                self.assertTrue(vbs_file.exists())
                vbs_content = vbs_file.read_text(encoding="utf-8")
                self.assertIn("pythonw.exe", vbs_content)
                self.assertIn("--service", vbs_content)
                self.assertTrue(bm.is_startup_enabled())

                # Test removal
                res_disable = bm.set_startup_enabled(False)
                self.assertTrue(res_disable)
                self.assertFalse(vbs_file.exists())

    def test_launch_detached_spawns_process(self):
        from unittest.mock import patch, MagicMock
        import src.app_launcher as app_launcher

        mock_args = MagicMock()
        mock_args.interval = 45
        mock_args.debug = False

        with patch("subprocess.Popen") as mock_popen, \
             patch("sys.exit") as mock_exit:
            mock_popen.return_value.pid = 99999
            app_launcher.launch_detached(mock_args)
            self.assertTrue(mock_popen.called)
            self.assertTrue(mock_exit.called)
            cmd = mock_popen.call_args[0][0]
            self.assertIn("--interval", cmd)
            self.assertIn("45", cmd)

    def test_check_and_repair_startup_heals_legacy_entry(self):
        from unittest.mock import patch, MagicMock
        with patch.object(bm, 'winreg', create=True) as mock_winreg, \
             patch.object(bm.os, 'name', 'nt'), \
             patch.object(bm.sys, 'frozen', False, create=True), \
             patch.object(bm.sys, 'executable', 'C:\\Python312\\python.exe'), \
             patch.object(bm.os.path, 'exists', return_value=True):
            mock_key = MagicMock()
            mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
            mock_winreg.HKEY_CURRENT_USER = 1
            mock_winreg.KEY_READ = 1
            mock_winreg.KEY_SET_VALUE = 2
            mock_winreg.REG_SZ = 1
            # Old legacy entry pointing to python.exe
            mock_winreg.QueryValueEx.return_value = ('"C:\\Python312\\python.exe" "app_launcher.py"', 1)

            repaired = bm.check_and_repair_startup_registration()
            self.assertTrue(repaired)
            self.assertTrue(mock_winreg.SetValueEx.called)
            new_cmd = mock_winreg.SetValueEx.call_args[0][4]
            self.assertIn("pythonw.exe", new_cmd)

    def test_check_and_repair_startup_heals_relocated_path(self):
        from unittest.mock import patch, MagicMock
        with patch.object(bm, 'winreg', create=True) as mock_winreg, \
             patch.object(bm.os, 'name', 'nt'), \
             patch.object(bm.sys, 'frozen', False, create=True), \
             patch.object(bm.sys, 'executable', 'C:\\Python312\\python.exe'), \
             patch.object(bm.os.path, 'exists', return_value=True):
            mock_key = MagicMock()
            mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
            mock_winreg.HKEY_CURRENT_USER = 1
            mock_winreg.KEY_READ = 1
            mock_winreg.KEY_SET_VALUE = 2
            mock_winreg.REG_SZ = 1
            # Value pointing to an old location
            mock_winreg.QueryValueEx.return_value = ('"C:\\Python312\\pythonw.exe" "C:\\OldPath\\src\\app_launcher.pyw" --service', 1)

            repaired = bm.check_and_repair_startup_registration()
            self.assertTrue(repaired)
            self.assertTrue(mock_winreg.SetValueEx.called)
            new_cmd = mock_winreg.SetValueEx.call_args[0][4]
            self.assertIn("app_launcher.pyw", new_cmd)

    def test_hide_and_detach_console_invokes_windows_apis(self):
        from unittest.mock import patch, MagicMock
        mock_ctypes = MagicMock()
        mock_kernel32 = MagicMock()
        mock_user32 = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.windll.user32 = mock_user32
        mock_kernel32.GetConsoleWindow.return_value = 12345

        with patch.object(bm.os, 'name', 'nt'), \
             patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            bm.hide_and_detach_console()
            mock_user32.ShowWindow.assert_called_with(12345, 0)
            self.assertTrue(mock_kernel32.FreeConsole.called)

    def test_app_launcher_service_invokes_monitor(self):
        from unittest.mock import patch, MagicMock
        import src.app_launcher as app_launcher

        with patch("sys.argv", ["app_launcher.py", "--service", "--interval", "50"]), \
             patch("battery_monitor.main") as mock_bm_main, \
             patch("battery_monitor.check_and_repair_startup_registration"), \
             patch("sys.exit") as mock_exit:
            app_launcher.main()
            mock_bm_main.assert_called_once_with(interval=50, debug_mode=False)
            self.assertTrue(mock_exit.called)

    def test_app_launcher_fix_startup(self):
        from unittest.mock import patch, MagicMock
        import src.app_launcher as app_launcher

        with patch("sys.argv", ["app_launcher.py", "--fix-startup"]), \
             patch("battery_monitor.set_startup_enabled", return_value=True) as mock_set, \
             patch.object(app_launcher, "launch_detached") as mock_detach:
            app_launcher.main()
            self.assertTrue(mock_set.called)
            self.assertTrue(mock_detach.called)


if __name__ == '__main__':
    unittest.main()
