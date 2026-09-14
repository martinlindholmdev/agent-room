"""Consistent backup, empty-destination restore and non-destructive v2 staging."""
import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path, PurePosixPath
from desktop.protocol import require


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root, kind):
    result = {'format': 1, 'kind': kind, 'created': time.time(), 'credentials': 'Excluded; macOS Keychain remains authoritative',
              'files': {str(p.relative_to(root)): checksum(p) for p in root.rglob('*') if p.is_file() and p.name != 'manifest.json'}}
    (root/'manifest.json').write_text(json.dumps(result, indent=2))
    return result


def sqlite_copy(source, dest):
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
        require(target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'backup failed integrity check')
    finally:
        target.close()


def backup(node, destination):
    destination = Path(destination).resolve()
    require(not destination.exists(), 'backup destination already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.agent-room-backup-', dir=destination.parent))
    try:
        with contextlib.ExitStack() as locks:
            locks.enter_context(node.lock)
            if node.hub:locks.enter_context(node.hub.lock)
            locks.enter_context(node.delivery.lock)
            sqlite_copy(node.db, temporary/'device.sqlite3')
            sqlite_copy(node.delivery.db, temporary/'delivery.sqlite3')
            if node.hub:sqlite_copy(node.hub.db, temporary/'hub.sqlite3')
            if (node.root/'listener.json').exists():shutil.copy2(node.root/'listener.json',temporary/'listener.json')
            if (node.root/'legacy-archive').exists():
                shutil.copytree(node.root/'legacy-archive', temporary/'legacy-archive')
            manifest(temporary, 'desktop-profile')
        os.replace(temporary, destination)
        return {'backup': str(destination)}
    except Exception:
        shutil.rmtree(temporary)
        raise


def verify(source):
    source=Path(source).resolve()
    data=json.loads((source/'manifest.json').read_text())
    require(data.get('format')==1, 'unsupported backup format')
    require(data.get('kind') in ('desktop-profile','legacy-v2'), 'unsupported backup type')
    for filename, expected in data['files'].items():
        require(isinstance(filename,str) and '\\' not in filename and '\x00' not in filename, 'invalid backup member')
        relative=PurePosixPath(filename)
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==filename and filename not in ('','.','manifest.json'), 'noncanonical backup member')
        path=source/filename
        require(path.resolve().is_relative_to(source) and not path.is_symlink(), 'invalid backup path')
        require(checksum(path)==expected, 'backup checksum mismatch')
        if filename.endswith('.sqlite3'):
            db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
            try:require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok', 'backup database invalid')
            finally:db.close()
    return data


def restore(source, destination):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    data=verify(source)
    require(data['kind']=='desktop-profile', 'not a desktop profile backup')
    require(not destination.exists(), 'restore only to an absent directory; never overwrite newer messages')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.agent-room-restore-',dir=destination.parent))
    try:
        for filename in data['files']:
            target=temporary/filename
            require(target.resolve().is_relative_to(temporary.resolve()), 'restore member escapes destination')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/filename,target)
        # A backup cannot prove that a native prompt was not executed after it
        # was taken. Never auto-dispatch pre-backup pending work after restore.
        delivery=temporary/'delivery.sqlite3'
        if delivery.exists():
            db=sqlite3.connect(delivery)
            try:
                db.execute("UPDATE deliveries SET state='uncertain',reason='Restored backup; native outcome must be reconciled' WHERE state IN ('pending','sending','relaying','unavailable')")
                db.commit()
            finally:db.close()
        os.replace(temporary,destination)
    except Exception:
        shutil.rmtree(temporary)
        raise
    return {'restored':str(destination),'credentials':'Restore the original profile path to retain its Keychain identity. Another Mac must pair as a new device.'}


def stage_legacy(source, destination):
    """Stage all unread/history/routes without converting or guessing delivery.

    A live v2 singleton lock prevents mixed journal/state/database snapshots.
    Original files and cursors remain byte-preserved in this archive. The
    bundled --legacy-service can run a restored copy as v2 for rollback.
    """
    source,destination=Path(source).resolve(),Path(destination).resolve()
    require(source.is_dir() and not destination.exists(), 'legacy source must exist and destination must be new')
    with open(source/'daemon.lock','a') as owner:
        try:fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('legacy daemon is running; stop competing writers before staging') from None
        destination.mkdir(parents=True,mode=0o700)
        try:
            for name in ('state.json','channels'):
                path=source/name
                if path.is_dir():shutil.copytree(path,destination/name)
                elif path.is_file():shutil.copy2(path,destination/name)
            path=source/'delivery.sqlite3'
            if path.exists():
                db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
                try:sqlite_copy(db,destination/'delivery.sqlite3')
                finally:db.close()
            manifest(destination,'legacy-v2')
            verify(destination)
        except Exception:
            shutil.rmtree(destination)
            raise
    return {'staged':str(destination),'delivery':'Original pending and uncertain sends retained. No routes dispatched or rewritten.'}
