import json
import os
import sys
import time
import hashlib
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
        secret = input("Secret: ").strip()

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

    config = ensure_config()

    export_path = Path(config["export_file"])

    state = load_state()
    last_digest = state.get("last_digest")

    log(f"Watching: {export_path}")
    log("Leave this window open while playing Isaac.")

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


if __name__ == "__main__":
    try:
        run_watch()

    except Exception as error:
        print()
        print(f"Fatal error: {error}")
        input("Press Enter to close...")
        sys.exit(1)
