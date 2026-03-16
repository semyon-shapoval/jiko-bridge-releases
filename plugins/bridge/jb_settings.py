import os
import platform
import json
from typing import Optional

# default port mirrors the value used by the Electron application and the
# test suite.  Keeping it here makes it easy to change without digging through
# other code.
DEFAULT_API_PORT = 5174


def settings_path() -> Optional[str]:
    """Return the location of the JSON settings file created by the Electron
    app.

    The path logic duplicates the behaviour of the JS side (we don't have
    access to `app.getPath` from C4D), covering Windows, macOS, and
    Linux/XDG.
    """
    system = platform.system()
    if system == 'Windows':
        appdata = os.getenv('APPDATA')
        if not appdata:
            return None
        return os.path.join(appdata, 'jiko-bridge', 'settings.json')
    elif system == 'Darwin':
        return os.path.join(
            os.path.expanduser('~'),
            'Library',
            'Application Support',
            'jiko-bridge',
            'settings.json',
        )
    else:
        base = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(base, 'jiko-bridge', 'settings.json')


def port_from_settings(default: int = DEFAULT_API_PORT) -> int:
    """Read ``apiPort`` from the settings file, falling back to `default`.

    Any failure (missing file, parse error, wrong type) returns ``default``.
    """
    path = settings_path()
    if not path:
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        port = data.get('apiPort')
        if isinstance(port, int):
            return port
    except Exception:
        pass
    return default
