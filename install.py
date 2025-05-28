#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installation Script - LensCRL v1.0
===================================

Automatic installation and configuration of LensCRL,
a practical PDF image extraction tool.

Author: Arien Reibel
Version: 1.0
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class Colors:
    """Cross-platform colors for display."""
    
    def __init__(self):
        self.enabled = self._supports_color()
    
    def _supports_color(self):
        """Checks if terminal supports colors."""
        return (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() and
            os.environ.get('TERM') != 'dumb'
        ) or os.environ.get('FORCE_COLOR') == '1'
    
    def _colorize(self, text, color_code):
        if self.enabled:
            return f"\033[{color_code}m{text}\033[0m"
        return text
    
    def red(self, text): return self._colorize(text, "91")
    def green(self, text): return self._colorize(text, "92")
    def yellow(self, text): return self._colorize(text, "93")
    def blue(self, text): return self._colorize(text, "94")
    def magenta(self, text): return self._colorize(text, "95")
    def cyan(self, text): return self._colorize(text, "96")

colors = Colors()

def print_info(message):
    print(f"{colors.blue('ℹ️')}  {message}")

def print_success(message):
    print(f"{colors.green('✅')} {message}")

def print_warning(message):
    print(f"{colors.yellow('⚠️')}  {message}")

def print_error(message):
    print(f"{colors.red('❌')} {message}")

def print_header(title):
    print("\n" + "=" * 60)
    print(f"{colors.magenta(title.center(60))}")
    print("=" * 60)

def run_command(command, description="", check=True):
    """Executes a command with error handling."""
    if description:
        print_info(f"{description}...")
    
    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, check=check, 
                                  capture_output=True, text=True)
        else:
            result = subprocess.run(command, check=check, 
                                  capture_output=True, text=True)
        
        if result.returncode == 0 and description:
            print_success(f"{description} completed")
        
        return result
    
    except subprocess.CalledProcessError as e:
        if description:
            print_error(f"Failed: {description}")
        print_error(f"Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return None

def check_python_version():
    """Checks Python version."""
    print_info("Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print_error(f"Python {version.major}.{version.minor} detected")
        print_error("Python 3.7+ required for LensCRL")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_pip():
    """Checks if pip is available."""
    print_info("Checking pip...")
    
    try:
        import pip
        print_success("pip is available")
        return True
    except ImportError:
        print_warning("pip is not available as module")
        
        # Try pip command
        result = run_command([sys.executable, "-m", "pip", "--version"], check=False)
        if result and result.returncode == 0:
            print_success("pip is available via command")
            return True
        
        print_error("pip is not installed")
        return False

def install_pymupdf():
    """Installs PyMuPDF."""
    print_info("Checking PyMuPDF...")
    
    try:
        import fitz
        version = fitz.version[0] if hasattr(fitz, 'version') else "unknown version"
        print_success(f"PyMuPDF already installed (version {version})")
        return True
    except ImportError:
        print_warning("PyMuPDF is not installed")
    
    print_info("Installing PyMuPDF...")
    
    # Try different installation methods
    commands = [
        [sys.executable, "-m", "pip", "install", "PyMuPDF"],
        [sys.executable, "-m", "pip", "install", "--user", "PyMuPDF"],
    ]
    
    for cmd in commands:
        result = run_command(cmd, check=False)
        if result and result.returncode == 0:
            # Verify installation
            try:
                import fitz
                print_success("PyMuPDF installed successfully")
                return True
            except ImportError:
                continue
    
    print_error("Unable to install PyMuPDF automatically")
    print_info("Try manually:")
    print_info("  pip install PyMuPDF")
    print_info("  or: python -m pip install --user PyMuPDF")
    return False

def check_required_files():
    """Checks for required files."""
    print_info("Checking required files...")
    
    script_dir = Path(__file__).parent
    required_files = [
        "lenscrl.py",
        "extract_images.sh",
        "extract_images.bat"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = script_dir / file_name
        if file_path.exists():
            print_success(f"Found: {file_name}")
        else:
            print_warning(f"Missing: {file_name}")
            missing_files.append(file_name)
    
    if missing_files:
        print_warning(f"{len(missing_files)} file(s) missing")
        return False
    
    print_success("All required files are present")
    return True

def make_scripts_executable():
    """Makes scripts executable on Unix."""
    if platform.system() in ['Linux', 'Darwin']:  # Linux or macOS
        print_info("Setting execution permissions...")
        
        script_dir = Path(__file__).parent
        scripts = ["extract_images.sh"]
        
        for script in scripts:
            script_path = script_dir / script
            if script_path.exists():
                try:
                    os.chmod(script_path, 0o755)
                    print_success(f"Permissions set: {script}")
                except OSError as e:
                    print_warning(f"Unable to modify permissions for {script}: {e}")

def create_desktop_shortcuts():
    """Creates desktop shortcuts (optional)."""
    response = input("\nCreate desktop shortcuts? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        return
    
    print_info("Creating shortcuts...")
    
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = Path.home() / "Bureau"  # French
    
    if not desktop.exists():
        print_warning("Desktop directory not found")
        return
    
    script_dir = Path(__file__).parent
    
    if platform.system() == "Windows":
        # Windows shortcut (.bat)
        shortcut_content = f'''@echo off
cd /d "{script_dir}"
call extract_images.bat
pause'''
        
        shortcut_path = desktop / "LensCRL.bat"
        try:
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(shortcut_content)
            print_success(f"Shortcut created: {shortcut_path}")
        except Exception as e:
            print_warning(f"Error creating shortcut: {e}")
    
    else:
        # Unix shortcut (.desktop)
        shortcut_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=LensCRL
Comment=PDF image extractor with CRL nomenclature
Exec=gnome-terminal --working-directory="{script_dir}" -- bash extract_images.sh
Icon=application-pdf
Terminal=true
Categories=Office;
'''
        
        shortcut_path = desktop / "LensCRL.desktop"
        try:
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(shortcut_content)
            os.chmod(shortcut_path, 0o755)
            print_success(f"Shortcut created: {shortcut_path}")
        except Exception as e:
            print_warning(f"Error creating shortcut: {e}")

def show_usage_instructions():
    """Shows usage instructions."""
    print_header("USAGE INSTRUCTIONS")
    
    print_info("LensCRL v1.0 is now ready!")
    print()
    
    script_dir = Path(__file__).parent
    
    print(colors.cyan("📋 USAGE:"))
    print()
    
    if platform.system() == "Windows":
        print("  🖱️  Simple mode:")
        print(f"     Double-click: {script_dir / 'extract_images.bat'}")
        print()
        print("  💻 Command line:")
        print(f"     extract_images.bat -p \"my_file.pdf\" -o \"./output\" -r")
    
    else:
        print("  🖱️  Simple mode:")
        print(f"     Double-click: {script_dir / 'extract_images.sh'}")
        print()
        print("  💻 Command line:")
        print(f"     ./extract_images.sh -p \"my_file.pdf\" -o \"./output\" -r")
    
    print()
    print("  🐍 Direct Python:")
    print("     python3 lenscrl.py --pdf \"file.pdf\" --output \"./images\" --report")
    print()
    
    print(colors.cyan("📝 NOMENCLATURE:"))
    print("  • CRL-[MANUALNAME]-[SECTION#].{ext}          (1 image)")
    print("  • CRL-[MANUALNAME]-[SECTION#] n_[POS].{ext}  (multiple images)")
    print()
    
    print(colors.cyan("🎯 FEATURES:"))
    print("  • Automatic PDF image extraction")
    print("  • Document section detection")
    print("  • Automatic CRL nomenclature")
    print("  • Duplicate filtering")
    print("  • Cross-platform support")

def main():
    """Main installation function."""
    print_header("LENSCRL v1.0 INSTALLATION")
    
    print_info(f"System: {platform.system()} {platform.release()}")
    print_info(f"Architecture: {platform.machine()}")
    print()
    
    # Checks
    steps = [
        ("Python verification", check_python_version),
        ("pip verification", check_pip),
        ("PyMuPDF installation", install_pymupdf),
        ("File verification", check_required_files),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print_error(f"Failed: {step_name}")
            print_error("Installation interrupted")
            return False
    
    # Configuration
    make_scripts_executable()
    
    print_header("INSTALLATION COMPLETED")
    print_success("LensCRL v1.0 installed successfully!")
    
    # Optional shortcuts
    create_desktop_shortcuts()
    
    # Instructions
    show_usage_instructions()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print()
            print_success("🎉 Installation successful!")
        else:
            print()
            print_error("❌ Installation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print()
        print_warning("Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        sys.exit(1) 