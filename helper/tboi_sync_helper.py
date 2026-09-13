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
import tempfile
import zipfile
from pathlib import Path

APP_NAME = "TBOI Sync Helper"
ENDPOINT = "https://rqkatvagyyumlzatiqmp.supabase.co/functions/v1/tracker-sync"
POLL_SECONDS = 2.0
GITHUB_API = "https://api.github.com"
LEGACY_REPENTOGON_TAG = "1.0.12e"
LEGACY_RELEASE_API = f"{GITHUB_API}/repos/TeamREPENTOGON/REPENTOGON/releases/tags/{LEGACY_REPENTOGON_TAG}"
LAUNCHER_RELEASE_API = f"{GITHUB_API}/repos/TeamREPENTOGON/Launcher/releases/latest"


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


def request_json(url, timeout=30):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TBOI-Tracker-Sync-Helper",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(payload):
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "TBOI-Tracker-Sync-Helper"},
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


def _steam_roots():
    roots = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                roots.insert(0, Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except OSError:
            pass
    for root in list(roots):
        libraries = root / "steamapps" / "libraryfolders.vdf"
        if libraries.exists():
            try:
                text = libraries.read_text(encoding="utf-8", errors="ignore")
                for value in re.findall(r'"path"\s*"([^"]+)"', text):
                    roots.append(Path(value.replace("\\\\", "\\")))
            except OSError:
                pass
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        roots.extend([Path(f"{letter}:\\Steam"), Path(f"{letter}:\\SteamLibrary"), Path(f"{letter}:\\Games\\Steam")])
    unique = []
    seen = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def game_candidates():
    for steam in _steam_roots():
        yield steam / "steamapps" / "common" / "The Binding of Isaac Rebirth"


def steam_candidates():
    for game in game_candidates():
        yield game / "data" / "tboi_progress_exporter" / "save1.dat"


def locate_game_dir(config=None):
    config = config or {}
    configured = str(config.get("game_dir", "")).strip()
    if configured:
        candidate = Path(os.path.expandvars(os.path.expanduser(configured)))
        if (candidate / "isaac-ng.exe").is_file():
            return candidate
    configured_export = str(config.get("export_file", "")).strip()
    if configured_export:
        export = Path(os.path.expandvars(os.path.expanduser(configured_export)))
        try:
            game = export.parents[2]
            if (game / "isaac-ng.exe").is_file():
                return game
        except IndexError:
            pass
    for candidate in game_candidates():
        if (candidate / "isaac-ng.exe").is_file():
            return candidate
    return None


def prompt_for_game_dir():
    print()
    print("Could not automatically find The Binding of Isaac: Rebirth.")
    print("In Steam: right-click the game > Manage > Browse local files.")
    print("Paste that folder path below.")
    while True:
        value = input("Isaac game folder: ").strip().strip('"')
        path = Path(os.path.expandvars(os.path.expanduser(value)))
        if path.is_file() and path.name.lower() == "isaac-ng.exe":
            path = path.parent
        if (path / "isaac-ng.exe").is_file():
            return path
        print("isaac-ng.exe was not found there. Try again.")


def default_export_file(game_dir):
    return Path(game_dir) / "data" / "tboi_progress_exporter" / "save1.dat"


def locate_export_file(config):
    configured = str(config.get("export_file", "")).strip()
    if configured:
        path = Path(os.path.expandvars(os.path.expanduser(configured)))
        if path.exists():
            return path
    game = locate_game_dir(config)
    if game:
        path = default_export_file(game)
        if path.exists():
            return path
    for candidate in steam_candidates():
        if candidate.exists():
            return candidate
    return None


def prompt_for_file():
    print()
    print("Could not automatically find the Isaac progression export.")
    print("Start Isaac with TBOI Tracker enabled and start/continue a run once, then try again.")
    while True:
        value = input("Paste the full path to save1.dat: ").strip().strip('"')
        path = Path(os.path.expandvars(os.path.expanduser(value)))
        if path.exists():
            return path
        print("File not found. Try again.")


def validate_progress(data):
    if not isinstance(data, dict):
        raise ValueError("Exporter file is not a JSON object.")
    required = ["achievements", "collectedItems", "completedChallenges", "completionMarks"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("Exporter file is missing: " + ", ".join(missing))
    for key in ("achievements", "collectedItems", "completedChallenges"):
        if not isinstance(data[key], list) or not all(type(v) is int and v > 0 for v in data[key]):
            raise ValueError("Invalid export field: " + key)
    if not isinstance(data["completionMarks"], dict):
        raise ValueError("Invalid completion marks")
    return data


def game_edition(game_dir):
    game = Path(game_dir)
    return "repentance_plus" if (game / "resources-dlc3").exists() else "repentance"


def legacy_repentogon_installed(game_dir):
    game = Path(game_dir)
    return (
        (game / "dsound.dll").is_file()
        and (game / "zhlREPENTOGON.dll").is_file()
        and (game / "resources-repentogon").exists()
    )


def plus_repentogon_installed(game_dir):
    game = Path(game_dir)
    folder = game / "Repentogon"
    return folder.is_dir() and any(folder.iterdir())


def repentogon_installed(game_dir):
    return plus_repentogon_installed(game_dir) if game_edition(game_dir) == "repentance_plus" else legacy_repentogon_installed(game_dir)


def find_release_asset(release, name):
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset
    raise RuntimeError(f"Official release is missing {name}.")


def download_file(url, destination, max_bytes=100 * 1024 * 1024):
    destination = Path(destination)
    request = urllib.request.Request(url, headers={"User-Agent": "TBOI-Tracker-Sync-Helper"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise RuntimeError("Dependency download is unexpectedly large.")
            total = 0
            digest = hashlib.sha256()
            with destination.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError("Dependency download exceeded the size limit.")
                    output.write(chunk)
                    digest.update(chunk)
            return digest.hexdigest()
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not download REPENTOGON: {error.reason}")


def parse_sha256(text):
    match = re.search(r"\b([0-9a-fA-F]{64})\b", text or "")
    if not match:
        raise RuntimeError("Official release did not provide a valid SHA-256 hash.")
    return match.group(1).lower()


def _safe_zip_members(archive, destination):
    destination = Path(destination).resolve()
    members = []
    for info in archive.infolist():
        target = (destination / info.filename).resolve()
        try:
            target.relative_to(destination)
        except ValueError:
            raise RuntimeError("Dependency archive contains an unsafe path.")
        members.append((info, target))
    return members


def extract_zip_safely(zip_path, destination, backup_dir=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = _safe_zip_members(archive, destination)
        if backup_dir:
            backup_dir = Path(backup_dir)
            for info, target in members:
                if info.is_dir() or not target.is_file():
                    continue
                relative = target.relative_to(destination)
                backup = backup_dir / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
        archive.extractall(destination)


def _consent_dependency(edition):
    label = "Repentance+" if edition == "repentance_plus" else "Repentance 1.7.9b"
    print()
    print(f"REPENTOGON was not detected for {label}.")
    print("TBOI Tracker needs REPENTOGON to export progress automatically.")
    print("The helper can download it only from the official TeamREPENTOGON GitHub releases.")
    answer = input("Download/install official REPENTOGON now? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        raise RuntimeError("REPENTOGON is required. Installation cancelled.")


def install_legacy_repentogon(game_dir):
    game = Path(game_dir)
    print(f"Downloading official REPENTOGON {LEGACY_REPENTOGON_TAG} for base Repentance...")
    release = request_json(LEGACY_RELEASE_API)
    zip_asset = find_release_asset(release, "REPENTOGON.zip")
    hash_asset = find_release_asset(release, "hash.txt")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        zip_path = temp / "REPENTOGON.zip"
        hash_path = temp / "hash.txt"
        actual = download_file(zip_asset["browser_download_url"], zip_path)
        download_file(hash_asset["browser_download_url"], hash_path, max_bytes=1024 * 1024)
        expected = parse_sha256(hash_path.read_text(encoding="utf-8", errors="ignore"))
        if actual.lower() != expected:
            raise RuntimeError("REPENTOGON download failed SHA-256 verification; nothing was installed.")
        backup = appdata_dir() / ("repentogon-backup-" + time.strftime("%Y%m%d-%H%M%S"))
        backup.mkdir(parents=True, exist_ok=True)
        extract_zip_safely(zip_path, game, backup)
    if not legacy_repentogon_installed(game):
        raise RuntimeError("REPENTOGON files were downloaded but the installation could not be verified.")
    print(f"REPENTOGON {LEGACY_REPENTOGON_TAG} installed and verified.")


def install_plus_repentogon(game_dir):
    game = Path(game_dir)
    print("Downloading the official REPENTOGON Launcher for Repentance+...")
    release = request_json(LAUNCHER_RELEASE_API)
    asset = find_release_asset(release, "REPENTOGONLauncher.zip")
    digest = str(asset.get("digest") or "")
    expected = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "REPENTOGONLauncher.zip"
        actual = download_file(asset["browser_download_url"], zip_path)
        if expected and actual.lower() != expected:
            raise RuntimeError("REPENTOGON Launcher download failed SHA-256 verification; nothing was installed.")
        launcher_dir = game / "REPENTOGONLauncher"
        extract_zip_safely(zip_path, launcher_dir)
    launchers = list((game / "REPENTOGONLauncher").rglob("REPENTOGONLauncher.exe"))
    if not launchers:
        raise RuntimeError("REPENTOGON Launcher was downloaded but REPENTOGONLauncher.exe was not found.")
    launcher = launchers[0]
    print()
    print("The official REPENTOGON Launcher will open now.")
    print("Finish its first-time setup for this Isaac installation. It may manage the compatible Repentance+ version for you.")
    subprocess.Popen([str(launcher)])
    input("When REPENTOGON says it is installed, close the launcher and press Enter here...")
    if not plus_repentogon_installed(game):
        raise RuntimeError("REPENTOGON installation was not detected. Re-run Install.cmd after completing the REPENTOGON Launcher setup.")
    print("REPENTOGON installation detected.")


def ensure_repentogon(game_dir):
    game = Path(game_dir)
    edition = game_edition(game)
    if repentogon_installed(game):
        print("REPENTOGON detected; dependency setup skipped.")
        return edition
    _consent_dependency(edition)
    if edition == "repentance_plus":
        install_plus_repentogon(game)
    else:
        install_legacy_repentogon(game)
    return edition


def find_exporter_mod(game_dir):
    mods = Path(game_dir) / "mods"
    if not mods.is_dir():
        return None
    for metadata in mods.glob("*/metadata.xml"):
        try:
            text = metadata.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "<id>tboi_progress_exporter</id>" in text or "<name>TBOI Tracker</name>" in text:
            return metadata.parent
    return None


def install_bundled_exporter(game_dir):
    game = Path(game_dir)
    target = game / "mods" / "tboi_progress_exporter"
    existing = find_exporter_mod(game)
    if existing and existing.resolve() != target.resolve():
        print(f"TBOI Tracker Workshop mod detected: {existing}")
        return existing
    target.mkdir(parents=True, exist_ok=True)
    source = Path(sys._MEIPASS) / "exporter"
    backup = appdata_dir() / ("exporter-backup-" + time.strftime("%Y%m%d-%H%M%S"))
    copied_backup = False
    for name in ("main.lua", "metadata.xml"):
        if (target / name).exists():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target / name, backup / name)
            copied_backup = True
        shutil.copy2(source / name, target / name)
    print(f"Installed bundled TBOI Tracker exporter: {target}")
    if copied_backup:
        print(f"Previous local exporter backed up: {backup}")
    return target


def ensure_config(game_dir=None, allow_missing_export=False):
    try:
        config = read_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    except Exception:
        config = {}
    game = Path(game_dir) if game_dir else locate_game_dir(config)
    if game:
        config["game_dir"] = str(game)
        default = default_export_file(game)
        if allow_missing_export or default.exists():
            config["export_file"] = str(default)
    if not config.get("export_file"):
        export_file = locate_export_file(config)
        if export_file is None:
            if allow_missing_export and game:
                export_file = default_export_file(game)
            else:
                export_file = prompt_for_file()
        config["export_file"] = str(export_file)
    if not config.get("sync_id") or not config.get("secret"):
        print()
        print("Open Cloud Sync on your TBOI Tracker website.")
        print("Enter the same Sync ID and Secret below.")
        print()
        sync_id = input("Sync ID: ").strip().upper()
        secret = getpass.getpass("Secret (hidden while typing): ").strip()
        if not sync_id or not secret:
            raise RuntimeError("Sync ID and Secret are required.")
        print("Checking pairing...")
        post_json({"action": "pull", "sync_id": sync_id, "secret": secret})
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
    if "--background" in sys.argv:
        config = read_json(CONFIG_PATH)
        if not all(config.get(k) for k in ("export_file", "sync_id", "secret")):
            raise RuntimeError("Incomplete configuration. Run Install.cmd again.")
    else:
        config = ensure_config()
    export_path = Path(config["export_file"])
    state = load_state()
    identity = hashlib.sha256((str(export_path.resolve()) + config["sync_id"] + config["secret"]).encode()).hexdigest()
    last_digest = state.get("last_digest") if state.get("identity") == identity else None
    log(f"Watching: {export_path}")
    log("Background sync active." if "--background" in sys.argv else "Leave this window open while playing Isaac, or run Install.cmd for background startup.")
    while True:
        try:
            if not export_path.exists():
                log("Exporter file is missing. Start/continue a run with TBOI Tracker enabled; waiting...")
                time.sleep(POLL_SECONDS)
                continue
            raw = export_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != last_digest:
                data = json.loads(raw.decode("utf-8-sig"))
                progress = dict(validate_progress(data))
                progress["_trackerUpdated"] = int(time.time() * 1000)
                progress["source"] = "game"
                post_json({
                    "action": "push",
                    "sync_id": config["sync_id"],
                    "secret": config["secret"],
                    "progress": progress,
                })
                last_digest = digest
                write_json(STATE_PATH, {
                    "last_digest": digest,
                    "identity": identity,
                    "last_upload_unix": int(time.time()),
                })
                achievements = len(progress.get("achievements", []))
                items = len(progress.get("collectedItems", []))
                challenges = len(progress.get("completedChallenges", []))
                log(f"Uploaded: {achievements} achievements, {items} items, {challenges} challenges.")
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            return
        except Exception as error:
            log(f"Error: {error}")
            time.sleep(5)


def install():
    """One-time Windows setup, including the REPENTOGON dependency when needed."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        raise RuntimeError("Use the packaged Windows EXE for installation.")
    print("TBOI Tracker automatic sync setup")
    print("Close Isaac and any old TBOI Sync Helper windows before continuing.")
    input("Press Enter when they are closed...")
    try:
        config = read_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    except Exception:
        config = {}
    game = locate_game_dir(config)
    if game is None:
        game = prompt_for_game_dir()
    game = game.resolve()
    print(f"Isaac folder: {game}")
    edition = ensure_repentogon(game)
    install_bundled_exporter(game)
    config = ensure_config(game, allow_missing_export=True)
    config["game_edition"] = edition
    write_json(CONFIG_PATH, config)
    installed = appdata_dir() / "TBOISyncHelper.exe"
    if Path(sys.executable).resolve() != installed.resolve():
        shutil.copy2(sys.executable, installed)
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        winreg.SetValueEx(key, "TBOISyncHelper", 0, winreg.REG_SZ, '"' + str(installed) + '" --background')
    subprocess.Popen([str(installed), "--background"], creationflags=subprocess.CREATE_NO_WINDOW)
    print()
    print("Installed. The helper is running in the background and will start at Windows sign-in.")
    print("Start Isaac with TBOI Tracker enabled, then start or continue a run.")
    print("The first game export will be picked up automatically.")
    print("Use your same Cloud Sync code on the phone and PC website.")
    print("Logs: " + str(LOG_PATH))
    input("Press Enter to close setup...")


def remove_startup():
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        try:
            winreg.DeleteValue(key, "TBOISyncHelper")
        except FileNotFoundError:
            pass
    print("Automatic startup disabled. End TBOISyncHelper.exe in Task Manager to stop the current session.")
    input("Press Enter to close...")


def single_instance():
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    single_instance.handle = api.CreateMutexW(None, False, r"Local\TBOITrackerSyncHelper")
    return ctypes.get_last_error() != 183


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            source = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "exporter"
            assert (source / "main.lua").is_file()
            assert (source / "metadata.xml").is_file()
            validate_progress({"achievements": [], "collectedItems": [], "completedChallenges": [], "completionMarks": {}})
            assert parse_sha256("sha256:" + "a" * 64) == "a" * 64
            print("PASS: packaged exporter, dependency helpers and sync validation")
        elif "--install" in sys.argv:
            install()
        elif "--remove-startup" in sys.argv:
            remove_startup()
        elif single_instance():
            if "--background" in sys.argv and not CONFIG_PATH.exists():
                raise RuntimeError("Run Install.cmd first to pair the helper.")
            run_watch()
    except Exception as error:
        print()
        print(f"Fatal error: {error}")
        if "--background" not in sys.argv:
            input("Press Enter to close...")
        sys.exit(1)
