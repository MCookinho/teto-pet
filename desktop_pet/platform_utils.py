import os
import sys
import subprocess


def is_windows():
    return sys.platform == "win32"


def font_name():
    if is_windows():
        return "Segoe UI"
    return "sans-serif"


def kill_process(pattern_or_name):
    if is_windows():
        subprocess.run(
            ["taskkill", "/F", "/IM", pattern_or_name],
            capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", pattern_or_name], capture_output=True)


def check_command(cmd):
    if is_windows():
        return subprocess.run(
            ["where", cmd], capture_output=True
        ).returncode == 0
    else:
        return subprocess.run(
            ["which", cmd], capture_output=True
        ).returncode == 0


def open_url(url):
    if is_windows():
        os.startfile(url)
    else:
        subprocess.run(["xdg-open", url])


def get_cache_dir():
    from desktop_pet import config
    d = config.CACHE_DIR
    os.makedirs(d, exist_ok=True)
    return d


def get_config_dir():
    from desktop_pet import config
    d = config.CONFIG_DIR
    os.makedirs(d, exist_ok=True)
    return d


def get_config_dir():
    from desktop_pet import config
    d = config.CONFIG_DIR
    os.makedirs(d, exist_ok=True)
    return d
