import sys
from pathlib import Path

import tboi_sync_helper as core


def _legacy_repentogon_installed(game_dir):
    """Recognize valid legacy REPENTOGON installs without requiring one exact layout."""
    game = Path(game_dir)

    # Strong REPENTOGON-specific markers used by official legacy builds.
    zhl = (game / "zhlREPENTOGON.dll").is_file()
    resources = (game / "resources-repentogon").is_dir()

    # Different legacy packages/loaders have used different proxy DLLs.
    loader = any(
        (game / name).is_file()
        for name in (
            "dsound.dll",
            "winhttp.dll",
            "version.dll",
            "dinput8.dll",
            "launcher.dll",
        )
    )

    # A REPENTOGON-specific DLL plus either its resources or a loader is enough.
    # The resources directory plus a known loader is also a strong signal.
    if zhl and (resources or loader):
        return True
    if resources and loader:
        return True

    # Some installs keep the loader files in a REPENTOGON-named subfolder.
    for folder_name in ("REPENTOGON", "Repentogon", "repentogon"):
        folder = game / folder_name
        if folder.is_dir():
            try:
                names = {p.name.lower() for p in folder.iterdir()}
            except OSError:
                continue
            if any("repentogon" in name for name in names):
                return True

    return False


core.legacy_repentogon_installed = _legacy_repentogon_installed


def main():
    try:
        if "--self-test" in sys.argv:
            source = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "exporter"
            assert (source / "main.lua").is_file()
            assert (source / "metadata.xml").is_file()
            core.validate_progress({"achievements": [], "collectedItems": [], "completedChallenges": [], "completionMarks": {}})
            assert core.parse_sha256("sha256:" + "a" * 64) == "a" * 64
            print("PASS: packaged exporter, flexible REPENTOGON detection and sync validation")
        elif "--install" in sys.argv:
            core.install()
        elif "--remove-startup" in sys.argv:
            core.remove_startup()
        elif core.single_instance():
            if "--background" in sys.argv and not core.CONFIG_PATH.exists():
                raise RuntimeError("Run Install.cmd first to pair the helper.")
            core.run_watch()
    except Exception as error:
        print()
        print(f"Fatal error: {error}")
        if "--background" not in sys.argv:
            input("Press Enter to close...")
        sys.exit(1)


if __name__ == "__main__":
    main()
