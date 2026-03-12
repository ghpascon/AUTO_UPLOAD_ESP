import subprocess
import json
import os
import sys
import glob
import time
import shutil
import importlib.util
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

try:
    import serial.tools.list_ports
except ImportError:
    serial = None


def _is_linux() -> bool:
    """Return True when running on Linux."""
    return sys.platform.startswith("linux")


def _ensure_wine_available() -> str:
    """Ensure wine is installed on Linux and return the wine executable name."""
    wine_cmd = shutil.which("wine") or shutil.which("wine64")
    if wine_cmd:
        return wine_cmd

    print("Wine nao encontrado. Tentando instalar com: sudo apt install -y wine64")
    try:
        subprocess.run(["sudo", "apt", "install", "-y", "wine64"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Falha ao instalar wine64 automaticamente. Execute manualmente: sudo apt install -y wine64"
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError(
            "Comando apt/sudo nao encontrado. Instale o Wine manualmente para continuar."
        ) from e

    wine_cmd = shutil.which("wine") or shutil.which("wine64")
    if not wine_cmd:
        raise RuntimeError(
            "Wine ainda nao foi encontrado apos a instalacao. Verifique sua instalacao do wine64."
        )

    return wine_cmd


def _build_platform_command(executable_path: str, args: List[str]) -> List[str]:
    """Build command list considering Linux + .exe compatibility via Wine."""
    if _is_linux() and executable_path.lower().endswith(".exe"):
        wine_cmd = _ensure_wine_available()
        return [wine_cmd, os.path.abspath(executable_path), *args]
    return [os.path.abspath(executable_path), *args]


def _resolve_esptool_runner(bundled_exe_path: str) -> List[str]:
    """Resolve how to execute esptool in a cross-platform way."""
    bundled_exe_abs = os.path.abspath(bundled_exe_path)
    bundled_native_abs = os.path.splitext(bundled_exe_abs)[0]
    is_frozen = bool(getattr(sys, "frozen", False))

    # On Windows, prefer bundled executable when available.
    if sys.platform.startswith("win") and os.path.exists(bundled_exe_abs):
        return [bundled_exe_abs]

    # On Linux/macOS, accept bundled native binary (without .exe) when present.
    if not sys.platform.startswith("win") and os.path.exists(bundled_native_abs):
        return [bundled_native_abs]

    # First choice for Linux/macOS/Windows: esptool command from PATH/venv.
    esptool_cmd = shutil.which("esptool")
    if esptool_cmd:
        return [esptool_cmd]

    # Script mode only: run Python package as a module.
    # In frozen mode, sys.executable points to this app binary, so "-m esptool"
    # would recursively invoke this program instead of Python.
    if not is_frozen and importlib.util.find_spec("esptool") is not None:
        return [sys.executable, "-m", "esptool"]

    # Legacy fallback: run bundled .exe through Wine on Linux.
    if _is_linux() and os.path.exists(bundled_exe_abs):
        wine_cmd = _ensure_wine_available()
        return [wine_cmd, bundled_exe_abs]

    raise FileNotFoundError(
        "Esptool nao encontrado. Instale com 'poetry add esptool' ou forneca esp_depend/esptool.exe."
    )


def _resolve_mklittlefs_runner(bundled_exe_path: str) -> List[str]:
    """Resolve how to execute mklittlefs in a cross-platform way."""
    bundled_exe_abs = os.path.abspath(bundled_exe_path)

    # Prefer native command in PATH when available (Linux/macOS/Windows).
    native_cmd = shutil.which("mklittlefs")
    if native_cmd:
        return [native_cmd]

    # Windows fallback: use bundled executable directly.
    if sys.platform.startswith("win") and os.path.exists(bundled_exe_abs):
        return [bundled_exe_abs]

    # Linux fallback: run bundled .exe through Wine.
    if _is_linux() and os.path.exists(bundled_exe_abs):
        wine_cmd = _ensure_wine_available()
        return [wine_cmd, bundled_exe_abs]

    raise FileNotFoundError(
        "mklittlefs nao encontrado. Instale/binario no PATH ou forneca esp_depend/mklittlefs.exe."
    )


def _show_linux_serial_permission_hint(port_name: str):
    """Print actionable guidance when a Linux serial device is not readable."""
    print(f"Sem permissao para acessar a porta serial: {port_name}")
    print("No Linux, normalmente a porta pertence ao grupo 'dialout'.")
    print("Execute:")
    print("  sudo usermod -aG dialout $USER")
    print("Depois, faca logout/login (ou reinicie) e tente novamente.")


def _can_access_serial_port(port_name: str) -> bool:
    """Return True when the current user can read/write the serial port."""
    if not _is_linux() or not port_name.startswith("/dev/"):
        return True

    if not os.path.exists(port_name):
        print(f"Porta serial nao encontrada: {port_name}")
        return False

    can_access = os.access(port_name, os.R_OK | os.W_OK)
    if can_access:
        return True

    _show_linux_serial_permission_hint(port_name)
    return False


def get_frozen_path(relative_path: str) -> str:
    """Resolve resource path, using PyInstaller temp dir when running as frozen executable."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        resolved_path = os.path.join(getattr(sys, "_MEIPASS"), relative_path)
        print(f"[PATH] Frozen mode detected. Using temp path: {resolved_path}")
        return resolved_path

    resolved_path = os.path.abspath(relative_path)
    print(f"[PATH] Script mode detected. Using local path: {resolved_path}")
    return resolved_path


@dataclass
class FlashConfig:
    """Configuration for ESP32 flashing operations"""

    port: str
    esp32s3: bool
    baud_rate: str = "921600"
    flash_mode: str = "keep"
    flash_freq: str = "keep"
    flash_size: str = "detect"

    @property
    def boot_location(self) -> str:
        return "0x0" if self.esp32s3 else "0x1000"

    @property
    def littlefs_offset(self) -> str:
        return "0x670000" if self.esp32s3 else "0x290000"


@dataclass
class ESPPaths:
    """Paths for ESP32 binaries and tools"""

    bootloader: str
    partitions: str
    app: str
    littlefs: str
    esptool: str
    boot_app0: str

    @classmethod
    def from_bin_directory(cls, bin_dir: str = "bin_files") -> "ESPPaths":
        """Create ESPPaths by scanning the bin_files directory"""
        try:
            bootloader_files = glob.glob(os.path.join(bin_dir, "*.ino.bootloader.bin"))
            partitions_files = glob.glob(os.path.join(bin_dir, "*.ino.partitions.bin"))
            app_files = glob.glob(os.path.join(bin_dir, "*.ino.bin"))

            if not bootloader_files:
                raise FileNotFoundError("Bootloader binary not found")
            if not partitions_files:
                raise FileNotFoundError("Partitions binary not found")
            if not app_files:
                raise FileNotFoundError("Application binary not found")

            esp_depend_dir = get_frozen_path("esp_depend")
            selected_esptool = os.path.join(esp_depend_dir, "esptool.exe")

            return cls(
                bootloader=bootloader_files[0],
                partitions=partitions_files[0],
                app=app_files[0],
                littlefs=os.path.join(bin_dir, "littlefs.bin"),
                esptool=selected_esptool,
                boot_app0=os.path.join(esp_depend_dir, "boot_app0.bin"),
            )
        except IndexError as e:
            raise FileNotFoundError(
                f"Required binary files not found in {bin_dir}"
            ) from e


def _get_port_info(port) -> Tuple[str, Optional[int]]:
    """Get port name and VID (Vendor ID)"""
    port_name = port.device
    vid = None
    if hasattr(port, "vid") and port.vid is not None:
        vid = port.vid
    return port_name, vid


def _detect_serial_ports() -> List[Tuple[str, Optional[int]]]:
    """Detect available serial ports with VID, prioritizing VID 12346 and 1"""
    if serial is None:
        print("pyserial not available. Install with: pip install pyserial")
        return []

    try:
        ports = serial.tools.list_ports.comports()
        preferred_ports = []  # VID 12346 or 1
        other_ports = []  # Other VIDs

        print(
            f"Serial scan started. Total portas detectadas pelo sistema: {len(ports)}"
        )

        for port in ports:
            port_name, vid = _get_port_info(port)
            # Skip COM1 and COM2
            if port_name not in ["COM1", "COM2"]:
                if vid is None:
                    continue

                print(
                    f"Found serial port: {port_name} (VID: {vid}) - {port.description}"
                )

                # Prioritize VID 12346 or 1
                if vid in [12346, 1]:
                    preferred_ports.append((port_name, vid))
                    print(f"  → Preferred port (VID: {vid})")
                else:
                    other_ports.append((port_name, vid))
                    print(f"  → Accepted by VID filter (VID: {vid})")
            else:
                print(f"Ignoring {port_name}: porta reservada")

        # Return preferred ports first, then others
        all_ports = preferred_ports + other_ports
        if preferred_ports:
            print(
                f"\nPort priority: {len(preferred_ports)} preferred port(s) will be tried first"
            )

        print(
            f"Serial scan finished. Portas com VID valido: {len(all_ports)} "
            f"(preferidas: {len(preferred_ports)}, outras: {len(other_ports)})"
        )

        return all_ports

    except Exception as e:
        print(f"Error detecting serial ports: {e}")
        return []


def _put_device_in_download_mode(port_name: str, esptool_runner: List[str]) -> bool:
    """Put device in download mode for VID=1 ports"""
    if not _can_access_serial_port(port_name):
        return False

    print(f"Putting device on {port_name} in download mode...")
    command = [
        *esptool_runner,
        "--chip",
        "auto",
        "--port",
        port_name,
        "--before",
        "default_reset",
        "--after",
        "no_reset",
        "chip_id",
    ]
    print(f"Download mode command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=20
        )
        if result.stdout:
            print(result.stdout.strip())
        print("Device successfully put in download mode")
        return True
    except subprocess.TimeoutExpired:
        print("Timeout ao colocar dispositivo em download mode (20s)")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Failed to put device in download mode: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def _try_upload_with_port(
    port_name: str,
    vid: Optional[int],
    flash_config: FlashConfig,
    paths: ESPPaths,
    esptool_runner: List[str],
) -> bool:
    """Try upload with a specific port, handling VID=1 special case"""
    if not _can_access_serial_port(port_name):
        return False

    flash_config.port = port_name
    vid_info = f" (VID: {vid})" if vid is not None else " (VID: Unknown)"
    print(f"\n=== Trying upload with port: {port_name}{vid_info} ===")

    # Special handling for VID=1 ports
    if vid == 1:
        print("VID=1 detected - putting device in download mode first")
        if not _put_device_in_download_mode(port_name, esptool_runner):
            return False
        time.sleep(1)  # Small delay after download mode

    # Attempt upload
    success = _flash_complete_program(flash_config, paths, esptool_runner)
    if success:
        print(f"✓ Upload successful with port {port_name}")
    else:
        print(f"✗ Upload failed with port {port_name}")

    return success


def upload_program_to_esp():
    """Main function to upload program and filesystem to ESP32"""
    try:
        config = load_config("config.json")
        print(f"[STEP] Config loaded from config.json: {config}")

        flash_config = FlashConfig(
            port="",  # Will be set by port detection/selection
            esp32s3=config.get("esp32s3", True),
        )
        print(
            f"[STEP] Target chip profile: {'ESP32-S3' if flash_config.esp32s3 else 'ESP32'}"
        )

        paths = ESPPaths.from_bin_directory()
        print("[STEP] Binary/tool paths resolved successfully")

        esptool_runner = _resolve_esptool_runner(paths.esptool)
        print(f"[STEP] Esptool runner selecionado: {' '.join(esptool_runner)}")

        # Validate required files exist
        _validate_required_files(paths)
        print("[STEP] Required files validated")

        # Handle port selection and flashing
        port = config.get("com_port", "COM4")
        if port.upper() == "AUTO":
            print("Starting automatic port detection and upload...")
            attempt = 1

            while True:
                print(f"\n--- Attempt #{attempt} ---")

                # Detect ports
                ports_info = _detect_serial_ports()

                if ports_info:
                    # Try upload with each detected port
                    for port_name, vid in ports_info:
                        success = _try_upload_with_port(
                            port_name, vid, flash_config, paths, esptool_runner
                        )
                        if success:
                            print(
                                f"\n🎉 Upload completed successfully on attempt #{attempt} with port {port_name}!"
                            )
                            return True

                    print(f"All {len(ports_info)} port(s) failed on attempt #{attempt}")
                else:
                    print(f"No suitable ports found on attempt #{attempt}")

                # Wait before retry
                print("Waiting 3 seconds before next attempt...")
                time.sleep(3)
                attempt += 1
        else:
            # Manual port specified - single attempt
            print(f"Using manually specified port: {port}")
            if not _can_access_serial_port(port):
                print("Flashing aborted due to serial port permission/access issue.")
                return False
            flash_config.port = port
            if not _flash_complete_program(flash_config, paths, esptool_runner):
                print("Flashing failed with manual port.")
                return False
            else:
                print("Upload completed successfully with manual port!")

        return True

    except Exception as e:
        print(f"Upload failed: {e}")
        return False


def _validate_required_files(paths: ESPPaths):
    """Validate that all required files exist"""
    required_files = [
        (paths.bootloader, "Bootloader binary"),
        (paths.partitions, "Partitions binary"),
        (paths.app, "Application binary"),
        (paths.boot_app0, "boot_app0 binary"),
    ]

    for file_path, description in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{description} not found: {file_path}")

    # Check LittleFS file separately (optional warning)
    if not os.path.exists(paths.littlefs):
        print(f"Warning: LittleFS file not found: {paths.littlefs}")
        print("Continuing without filesystem data...")


def _flash_complete_program(
    config: FlashConfig, paths: ESPPaths, esptool_runner: List[str]
) -> bool:
    """Flash complete program including filesystem to ESP32"""
    program_parts = [
        (config.boot_location, paths.bootloader),
        ("0x8000", paths.partitions),
        ("0xe000", paths.boot_app0),
        ("0x10000", paths.app),
    ]

    # Add LittleFS only if file exists
    if os.path.exists(paths.littlefs):
        program_parts.append((config.littlefs_offset, paths.littlefs))
        print("Flashing complete program with filesystem...")
    else:
        print("Flashing program without filesystem...")

    command = _build_esptool_command(config, esptool_runner, program_parts)
    print(f"Command: {' '.join(command)}")

    return _execute_flash_command(command)


def _build_esptool_command(
    config: FlashConfig, esptool_runner: List[str], program_parts: list[tuple[str, str]]
) -> List[str]:
    """Build esptool command with given configuration and program parts"""
    base_args = [
        "--chip",
        "auto",
        "--port",
        config.port,
        "--baud",
        config.baud_rate,
        "--before",
        "default-reset",
        "--after",
        "hard-reset",
        "write-flash",
        "-z",
        "--flash-mode",
        config.flash_mode,
        "--flash-freq",
        config.flash_freq,
        "--flash-size",
        config.flash_size,
    ]

    # Add program parts (offset + file) - filter out empty tuples
    valid_parts = [
        (offset, file_path)
        for offset, file_path in program_parts
        if offset and file_path
    ]
    parts_args: List[str] = []
    for offset, file_path in valid_parts:
        parts_args.extend([offset, os.path.abspath(file_path)])

    print(f"Debug - Program parts: {valid_parts}")

    return [*esptool_runner, *base_args, *parts_args]


def _execute_flash_command(command: List[str]) -> bool:
    """Execute flash command and return success status"""
    try:
        subprocess.run(command, check=True)
        print("Flash operation completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Flash operation failed: {e}")
        return False


def generate_littlefs_bin(input_folder: str, output_folder: str) -> Optional[str]:
    """Generate LittleFS binary from input folder"""
    if not os.path.exists(input_folder):
        print(f"Input folder does not exist: {input_folder}")
        return None

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    mklittlefs_exe = get_frozen_path(os.path.join("esp_depend", "mklittlefs.exe"))
    try:
        mklittlefs_runner = _resolve_mklittlefs_runner(mklittlefs_exe)
    except FileNotFoundError as e:
        print(str(e))
        return None

    # LittleFS parameters
    page_size = 256
    block_size = 4096
    total_size = 1572864  # 1.5MB
    output_bin = os.path.join(output_folder, "littlefs.bin")

    command = [
        *mklittlefs_runner,
        "-c",
        os.path.abspath(input_folder),
        "-p",
        str(page_size),
        "-b",
        str(block_size),
        "-s",
        str(total_size),
        os.path.abspath(output_bin),
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("LittleFS binary generated successfully!")
        if result.stdout:
            print("Output:", result.stdout)
        return output_bin
    except subprocess.CalledProcessError as e:
        print("Error generating LittleFS binary:", e.stderr)
        return None


def load_config(filename: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Configuration file not found: {filename}")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        raise


def main():
    """Main entry point"""
    try:
        if _is_linux():
            platform_name = "Linux"
        elif sys.platform.startswith("win"):
            platform_name = "Windows"
        else:
            platform_name = sys.platform

        print("\n=== AUTO_UPLOAD_ESP START ===")
        print(f"Plataforma detectada: {platform_name}")
        print("Etapas planejadas:")
        if _is_linux():
            print("1) Detectar ferramentas nativas (esptool/mklittlefs) no PATH")
            print("   (usa Wine apenas quando so houver .exe em esp_depend)")
        else:
            print("1) Executar ferramentas nativamente no sistema")
        print("2) Gerar littlefs.bin a partir da pasta data/")
        print("3) Carregar configuracao do config.json")
        print("4) Validar arquivos obrigatorios de firmware/ferramentas")
        print("5) Detectar porta serial e tentar upload")
        print("=== INICIANDO PROCESSO ===\n")

        generate_littlefs_bin("data", "bin_files")
        success = upload_program_to_esp()
        if success:
            print("\n=== Upload completed successfully! ===")
        else:
            print("\n=== Upload failed! ===")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n=== Operation cancelled by user ===")
        sys.exit(1)
    except Exception as e:
        print(f"\n=== Unexpected error: {e} ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
