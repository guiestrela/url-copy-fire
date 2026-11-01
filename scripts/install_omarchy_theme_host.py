#!/usr/bin/env python3
"""Install the sibling stdlib native host for this user, without sudo or services.

Run with Python 3.11+: python3 install_omarchy_theme_host.py [--home HOME]
Use --uninstall for conservative receipt/hash-checked removal. Backups are never
restored or removed automatically. No external dependencies or network access.
The launcher pins this Python interpreter; reinstall if that interpreter moves.
Existing symlinks (including ancestors), nonregular files, hard-linked targets,
and group/world-writable user directories or files are rejected before writes.
Operations assume no concurrent process changes the target directories: this is
not a security boundary against another process running as the same user.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile

NAME = 'url_route.omarchy_theme'
EXTENSION_ID = 'url-route-omarchy-sync@local.invalid'
RECEIPT = '.install-receipt.json'
FORMAT = 'url-route-omarchy-sync-installer-v1'


def validate_target(path, home, directory=False):
    """Reject symlinks, special files and writable-by-others owned targets."""
    for item in reversed((path, *path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        leaf_file = item == path and not directory
        correct_type = stat.S_ISREG(info.st_mode) if leaf_file else stat.S_ISDIR(info.st_mode)
        if stat.S_ISLNK(info.st_mode) or not correct_type:
            raise ValueError('Unsafe target: ' + str(item))
        if item == home or home in item.parents:
            if info.st_uid != os.getuid() or info.st_mode & 0o022 or (leaf_file and info.st_nlink != 1):
                raise ValueError('Unsafe ownership, permissions or hard link: ' + str(item))


def layout(home):
    if sys.version_info < (3, 11):
        raise ValueError('Python 3.11 or newer is required')
    home = Path(os.path.abspath(home))
    if home == Path('/') or not home.is_dir():
        raise ValueError('Unsafe home: an existing per-user directory is required')
    validate_target(home, home, directory=True)
    library = home / '.local/lib/url-route-omarchy-sync'
    registration = home / '.mozilla/native-messaging-hosts' / (NAME + '.json')
    paths = [library / 'omarchy_theme_host.py', library / 'omarchy_theme_host', registration]
    receipt = library / RECEIPT
    for path in [*paths, receipt]:
        validate_target(path, home)
    return home, paths, receipt


def encoded_json(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_preserving(path, data, mode, home):
    """Skip identical files; retain different originals and replace atomically."""
    validate_target(path, home)
    previous = path.read_bytes() if path.exists() else None
    if previous == data and stat.S_IMODE(path.stat().st_mode) == mode:
        return
    for directory in reversed((path.parent, *path.parent.parents)):
        if directory == home or home in directory.parents:
            validate_target(directory, home, directory=True)
            if not directory.exists():
                directory.mkdir(mode=0o700)
    if previous is not None and previous != data:
        index = 0
        while True:
            suffix = '.bak' if index == 0 else '.bak.' + str(index)
            backup = path.with_name(path.name + suffix)
            try:
                # O_EXCL refuses even dangling symlinks at backup paths.
                fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                index += 1
                continue
            with os.fdopen(fd, 'wb') as stream:
                stream.write(previous)
            break
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), mode)
        validate_target(path, home)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def install(home):
    home, paths, receipt = layout(home)
    host, launcher, registration = paths
    source_path = Path(__file__).absolute().with_name('omarchy_theme_host.py')
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError('Missing or unsafe sibling omarchy_theme_host.py')
    source = source_path.read_bytes()
    interpreter = os.path.abspath(sys.executable)
    launch = ('#!/bin/sh\nexec ' + shlex.quote(interpreter) + ' ' +
              shlex.quote(str(host)) + ' "$@"\n').encode()
    manifest = encoded_json({'name': NAME, 'description': 'Read-only Omarchy palette stream',
                             'path': str(launcher), 'type': 'stdio',
                             'allowed_extensions': [EXTENSION_ID]})
    payloads = [source, launch, manifest]
    state = encoded_json({'format': FORMAT, 'sha256': {
        str(path.relative_to(home)): digest(data) for path, data in zip(paths, payloads)}})
    # Register last: a fresh registration never points to an incomplete install.
    for path, data, mode in [(host, source, 0o600), (launcher, launch, 0o700),
                             (receipt, state, 0o600), (registration, manifest, 0o600)]:
        write_preserving(path, data, mode, home)
    return 'Installed ' + str(registration)


def uninstall(home):
    home, paths, receipt = layout(home)
    if not receipt.exists():
        return 'Preserved: no installer receipt; nothing removed'
    try:
        state = json.loads(receipt.read_bytes())
        hashes = state['sha256']
        keys = {str(path.relative_to(home)) for path in paths}
        valid = (state['format'] == FORMAT and isinstance(hashes, dict) and set(hashes) == keys
                 and all(isinstance(value, str) and len(value) == 64
                         and all(char in '0123456789abcdef' for char in value)
                         for value in hashes.values()))
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        return 'Preserved: invalid installer receipt; nothing removed'
    registration = paths[-1]
    if not registration.exists() or digest(registration.read_bytes()) != hashes[str(registration.relative_to(home))]:
        return 'Preserved: registration does not match; nothing removed'
    # Registration goes first; a modified helper is left untouched.
    for path in reversed(paths):
        if path.exists() and digest(path.read_bytes()) == hashes[str(path.relative_to(home))]:
            path.unlink()
    receipt.unlink()
    # Deliberately retain directories, unrelated files, modified files and backups.
    return 'Uninstalled matching registration and unmodified helpers; other files preserved'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home(), help='existing user home (default: current home)')
    parser.add_argument('--uninstall', action='store_true', help='remove only receipt-matched installed files')
    args = parser.parse_args()
    try:
        print(uninstall(args.home) if args.uninstall else install(args.home))
    except (OSError, ValueError) as error:
        parser.exit(1, 'Installer refused: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
