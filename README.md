# 🔋 Battery Monitor Pro (HA Battery Monitor)

A comprehensive, lightweight battery monitoring solution for Windows with system tray integration, configurable toast/balloon notifications, audio alerts, and a modern Qt-based settings dashboard.

---

## 🌟 Features

- **Real-time Monitoring**: Tracks battery percentage, charging state, remaining run/charge time estimates, and discharge rates.
- **Smart System Tray Integration**: Color-coded battery level indicator in the system tray with quick action menu (*Check Now*, *Pause/Resume*, *Snooze*, *Settings*, *Quit*).
- **Multi-tiered Alerts**: Configurable notice, warning, and critical thresholds for both discharging (low battery) and charging (high charge / overcharge prevention).
- **Multi-modal Notifications**: Windows 10/11 modern toast notifications with fallback to system balloon tips and dialogs.
- **Audio Alerts & Headphone Protection**: Customizable frequency and duration beeps, with automatic audio intensity reduction when headphones are connected.
- **Modern Qt Settings GUI**: PySide6 dashboard with dark mode theme, live battery KPI gauges, and persistent JSON configuration management.
- **Single-Instance Protection**: Prevents multiple background instances from running simultaneously.

---

## 📁 Project Structure

```text
BatteryMoniter/
├── src/
│   ├── app_launcher.py       # Main CLI & entry point launcher
│   ├── battery_monitor.py    # Core battery monitoring engine & background service
│   ├── qt_gui.py             # PySide6 settings & dashboard interface
│   ├── qt_tray.py            # Qt-based system tray runner
│   └── splash_screen.py      # Tkinter animated splash screen
├── tests/
│   ├── test_battery_monitor.py # Unit tests for monitoring, config, and alerts
│   ├── test_executable.py      # Binary smoke & execution tests
│   └── final_test.py           # Verification script
├── tools/
│   ├── create_icon.py        # Generates default battery icons
│   └── convert_png_to_ico.py # Converts PNG assets to ICO
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (recommended 3.12+)
- Windows OS (for native Windows notifications and winsound audio)

### Installation
```bash
pip install -r requirements.txt
```

### Usage

#### Start Background Monitoring (Automatic Background Detach)
```bash
python src/app_launcher.py
```
*Launches the monitoring service in the background and immediately frees the terminal. You can safely close the terminal without affecting the system tray icon.*

#### Silent Windows Startup Setup (Zero Console Window on Sign-in)
- Run `setup_silent_startup.bat` (or enable **Start with Windows** in Settings).
- Automatically configures Windows registry with `pythonw.exe` so **no terminal window ever opens on boot**.

#### 100% Windowless Launchers (No Console Flash)
- Double-click `start_background.vbs`
- Or double-click `start_background.bat`
- Or double-click `src/app_launcher.pyw`

#### Foreground Console Mode & Debug Logging
```bash
python src/app_launcher.py --debug
# Or:
python src/app_launcher.py --console
```

#### Open Settings GUI Directly
- Click the battery logo in the system tray, or:
```bash
python src/app_launcher.py --settings
```

---

## 🧪 Running Tests

Run the test suite with unittest:

```bash
python -m unittest discover tests
```

---

## 📄 License
MIT License
