"""Run the game inside a private virtual environment, setting it up on first launch.

main.py and main3d.py call bootstrap() before importing anything third-party, so
`python main.py` works on a fresh machine: the first run creates Source/.venv and
installs requirements.txt into it (one time, needs internet), later runs start at once.
Reinstalls only when requirements.txt changes.
"""
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / '.venv'
REQUIREMENTS = HERE / 'requirements.txt'
STAMP = VENV / 'requirements.sha256'
GUARD = 'BLOXORZ_BOOTSTRAPPED'   # set in the child process so a failed setup never loops


def _venv_python():
    if os.name == 'nt':
        return VENV / 'Scripts' / 'python.exe'
    return VENV / 'bin' / 'python'


def _in_venv():
    return Path(sys.prefix).resolve() == VENV.resolve()


def _wanted_hash():
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def _up_to_date():
    return STAMP.exists() and STAMP.read_text().strip() == _wanted_hash()


def _install(python):
    print('Bloxorz: installing libraries (first run only, about 1-3 minutes)...', flush=True)
    subprocess.check_call([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                           '-r', str(REQUIREMENTS)])
    STAMP.write_text(_wanted_hash())


def bootstrap(entry):
    """Make sure the game runs with the pinned libraries; may re-run `entry` in .venv and exit."""
    try:
        if _in_venv():
            if not _up_to_date():
                _install(sys.executable)
            return
        if os.environ.get(GUARD):
            return
        python = _venv_python()
        if not python.exists():
            print('Bloxorz: creating a private Python environment in {}'.format(VENV), flush=True)
            venv.create(VENV, with_pip=True)
        if not _up_to_date():
            _install(python)
    except (OSError, subprocess.CalledProcessError) as error:
        # no internet, no venv module, ...: fall back to whatever this Python already has
        print('Bloxorz: automatic setup failed ({}); trying the current Python.'.format(error),
              file=sys.stderr)
        return

    env = dict(os.environ, **{GUARD: '1'})
    code = subprocess.call([str(python), str(Path(entry).resolve())] + sys.argv[1:], env=env)
    sys.exit(code)
