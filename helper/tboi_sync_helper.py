import json
import os
import sys
import time
import hashlib
import shutil
import subprocess
import re
import getpass
import urllib.request
import urllib.error
from pathlib import Path

APP_NAME = "TBOI Sync Helper"
ENDPOINT = "https://rqkatvagyyumlzatiqmp.supabase.co/functions/v1/tracker-sync"
POLL_SECONDS = 2.0


def appdata_dir():
    root = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(root) / "TBOISyncHelper"
    path.mkdir(parents=True, exist_ok=True)
    return path


CONFIG_PATH = appdata_dir() / "config.json"
STATE_PATH = appdata_dir() / "state.json"
LOG_PATH = appdata_dir() / "helper.log"


def log(message):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"

    try:
        with LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    except Exception:
        pass

    if sys.stdout is not None:
        print(line, flush=True)


def post_json(payload):
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}

    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")

        try:
            data = json.loads(raw)
            raise RuntimeError(data.get("error", f"HTTP {error.code}"))
        except json.JSONDecodeError:
            raise RuntimeError(f"HTTP {error.code}: {raw[:300]}")

    except urllib.error.URLError as error:
        raise RuntimeError(f"Network error: {error.reason}")


def read_json(path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")

    with temp.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp.replace(path)


def steam_candidates():
    """Common locations for the Repentance exporter."""
    candidates = []

    steam_roots = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
    ]

    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                steam_roots.insert(0, Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
        except OSError:
            pass
    for root in list(steam_roots):
        libraries = root / 'steamapps' / 'libraryfolders.vdf'
        if libraries.exists():
            for value in re.findall(r'"path"\s*"([^"]+)"', libraries.read_text(encoding='utf-8')):
                steam_roots.append(Path(value.replace('\\\\', '\\')))

    # Check other drive letters for common Steam library locations.
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        steam_roots.extend([
            Path(f"{letter}:\\Steam"),
            Path(f"{letter}:\\SteamLibrary"),
            Path(f"{letter}:\\Games\\Steam"),
        ])

    for steam in steam_roots:
        candidates.append(
            steam
            / "steamapps"
            / "common"
            / "The Binding of Isaac Rebirth"
            / "data"
            / "tboi_progress_exporter"
            / "save1.dat"
        )

    return candidates


def locate_export_file(config):
    configured = str(config.get("export_file", "")).strip()

    if configured:
        path = Path(
            os.path.expandvars(
                os.path.expanduser(configured)
            )
        )

        if path.exists():
            return path

    for candidate in steam_candidates():
        if candidate.exists():
            return candidate

    return None


def prompt_for_file():
    print()
    print("Could not automatically find the Isaac progression export.")
    print()
    print("In Steam:")
    print("1. Right-click The Binding of Isaac: Rebirth")
    print("2. Manage > Browse local files")
    print("3. Open data")
    print("4. Open tboi_progress_exporter")
    print("5. Find save1.dat")
    print()

    while True:
        value = input("Paste the full path to save1.dat: ")
        value = value.strip().strip('"')

        path = Path(
            os.path.expandvars(
                os.path.expanduser(value)
            )
        )

        if path.exists():
            return path

        print("File not found. Try again.")


def validate_progress(data):
    if not isinstance(data, dict):
        raise ValueError("Exporter file is not a JSON object.")

    required = [
        "achievements",
        "collectedItems",
        "completedChallenges",
        "completionMarks",
    ]

    missing = [
        key for key in required
        if key not in data
    ]

    if missing:
        raise ValueError(
            "Exporter file is missing: "
            + ", ".join(missing)
        )

    for key in ('achievements', 'collectedItems', 'completedChallenges'):
        if not isinstance(data[key], list) or not all(type(v) is int and v > 0 for v in data[key]):
            raise ValueError('Invalid export field: ' + key)
    if not isinstance(data['completionMarks'], dict):
        raise ValueError('Invalid completion marks')

    return data


def ensure_config():
    try:
        if CONFIG_PATH.exists():
            config = read_json(CONFIG_PATH)
        else:
            config = {}
    except Exception:
        config = {}

    export_file = locate_export_file(config)

    if export_file is None:
        export_file = prompt_for_file()

    config["export_file"] = str(export_file)

    if not config.get("sync_id") or not config.get("secret"):
        print()
        print(
            "Open Cloud Sync on your Dead God Tracker."
        )
        print(
            "Enter the same Sync ID and Secret below."
        )
        print()

        sync_id = input("Sync ID: ").strip().upper()
        secret = getpass.getpass("Secret (hidden while typing): ").strip()

        if not sync_id or not secret:
            raise RuntimeError(
                "Sync ID and Secret are required."
            )

        print("Checking pairing...")

        post_json({
            "action": "pull",
            "sync_id": sync_id,
            "secret": secret,
        })

        config["sync_id"] = sync_id
        config["secret"] = secret

        print("Pairing verified.")

    write_json(CONFIG_PATH, config)

    return config


def load_state():
    try:
        if STATE_PATH.exists():
            return read_json(STATE_PATH)
    except Exception:
        pass

    return {}


def run_watch():
    print()
    print(APP_NAME)
    print("=" * len(APP_NAME))
    print()

    if '--background' in sys.argv:
        config = read_json(CONFIG_PATH)
        if not all(config.get(k) for k in ('export_file', 'sync_id', 'secret')):
            raise RuntimeError('Incomplete configuration. Run Install.cmd again.')
    else:
        config = ensure_config()

    export_path = Path(config["export_file"])

    state = load_state()
    identity = hashlib.sha256((str(export_path.resolve()) + config['sync_id'] + config['secret']).encode()).hexdigest()
    last_digest = state.get("last_digest") if state.get('identity') == identity else None

    log(f"Watching: {export_path}")
    log('Background sync active.' if '--background' in sys.argv else 'Leave this window open while playing Isaac, or run Install.cmd for background startup.')

    while True:
        try:
            if not export_path.exists():
                log(
                    "Exporter file is missing. Waiting..."
                )
                time.sleep(POLL_SECONDS)
                continue

            raw = export_path.read_bytes()

            digest = hashlib.sha256(raw).hexdigest()

            if digest != last_digest:
                data = json.loads(
                    raw.decode("utf-8-sig")
                )

                progress = dict(
                    validate_progress(data)
                )

                progress["_trackerUpdated"] = int(
                    time.time() * 1000
                )
                progress['source'] = 'game'

                post_json({
                    "action": "push",
                    "sync_id": config["sync_id"],
                    "secret": config["secret"],
                    "progress": progress,
                })

                last_digest = digest

                write_json(
                    STATE_PATH,
                    {
                        "last_digest": digest,
                        "identity": identity,
                        "last_upload_unix": int(
                            time.time()
                        ),
                    },
                )

                achievements = len(
                    progress.get(
                        "achievements", []
                    )
                )

                items = len(
                    progress.get(
                        "collectedItems", []
                    )
                )

                challenges = len(
                    progress.get(
                        "completedChallenges", []
                    )
                )

                log(
                    f"Uploaded: "
                    f"{achievements} achievements, "
                    f"{items} items, "
                    f"{challenges} challenges."
                )

            time.sleep(POLL_SECONDS)

        except KeyboardInterrupt:
            return

        except Exception as error:
            log(f"Error: {error}")
            time.sleep(5)


def install():
    """Explicit one-time setup: backup exporter, install it, enable user startup."""
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('Use the packaged Windows EXE for installation.')
    print('Setup installs the continuous exporter and enables this helper at Windows sign-in.')
    print('Close Isaac and any old sync helper windows before continuing.')
    input('Press Enter when they are closed...')
    config = ensure_config()
    export = Path(config['export_file']).resolve()
    game = export.parents[2]
    if export.parent.name != 'tboi_progress_exporter' or export.parents[1].name != 'data' or not (game / 'isaac-ng.exe').exists():
        raise RuntimeError('Expected the exporter save in Isaac/data/tboi_progress_exporter. No mod files changed.')
    target = game / 'mods' / 'tboi_progress_exporter'
    target.mkdir(parents=True, exist_ok=True)
    source = Path(sys._MEIPASS) / 'exporter'
    backup = appdata_dir() / ('exporter-backup-' + time.strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    for name in ('main.lua', 'metadata.xml'):
        if (target / name).exists():
            shutil.copy2(target / name, backup / name)
        shutil.copy2(source / name, target / name)
    # Keep the user's configured save slot and pairing. Never modify Isaac's save.
    installed = appdata_dir() / 'TBOISyncHelper.exe'
    if Path(sys.executable).resolve() != installed.resolve():
        shutil.copy2(sys.executable, installed)
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        winreg.SetValueEx(key, 'TBOISyncHelper', 0, winreg.REG_SZ, '"' + str(installed) + '" --background')
    subprocess.Popen([str(installed), '--background'], creationflags=subprocess.CREATE_NO_WINDOW)
    print('Installed. The helper is running in the background and will start at sign-in.')
    print('Restart Isaac; keep TBOI Progress Exporter enabled. Start or continue a run.')
    print('Use your existing Cloud Sync code on the phone and PC website.')
    print('Logs: ' + str(LOG_PATH))
    print('Old exporter backup: ' + str(backup))
    input('Press Enter to close setup...')


def remove_startup():
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        try:
            winreg.DeleteValue(key, 'TBOISyncHelper')
        except FileNotFoundError:
            pass
    print('Automatic startup disabled. End TBOISyncHelper.exe in Task Manager to stop the current session.')
    input('Press Enter to close...')


def single_instance():
    if os.name != 'nt':
        return True
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    single_instance.handle = api.CreateMutexW(None, False, r'Local\TBOITrackerSyncHelper')
    return ctypes.get_last_error() != 183


if __name__ == "__main__":
    try:
        if '--self-test' in sys.argv:
            source = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'exporter'
            assert (source / 'main.lua').is_file()
            assert (source / 'metadata.xml').is_file()
            validate_progress({'achievements': [], 'collectedItems': [], 'completedChallenges': [], 'completionMarks': {}})
            print('PASS: packaged exporter and helper validation')
        elif '--install' in sys.argv:
            install()
        elif '--remove-startup' in sys.argv:
            remove_startup()
        elif single_instance():
            if '--background' in sys.argv and not CONFIG_PATH.exists():
                raise RuntimeError('Run Install.cmd first to pair the helper.')
            run_watch()

    except Exception as error:
        print()
        print(f"Fatal error: {error}")
        if '--background' not in sys.argv:
            input("Press Enter to close...")
        sys.exit(1)
