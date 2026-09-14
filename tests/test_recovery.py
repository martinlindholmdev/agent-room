import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from desktop.node import Node
from desktop.secrets import MemoryVault
from desktop.recovery import backup, restore, stage_legacy, verify


class RecoveryTests(unittest.TestCase):
    def test_restore_rejects_parent_and_absolute_manifest_names(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source/bundle';source.mkdir(parents=True)
            (source/'payload').write_text('replacement')
            sibling=root/'target/bundle';sibling.mkdir(parents=True);(sibling/'payload').write_text('preserve')
            for member in ('../bundle/payload',str(source/'payload')):
                (source/'manifest.json').write_text(json.dumps({'format':1,'kind':'desktop-profile','files':{member:hashlib.sha256(b'replacement').hexdigest()}}))
                with self.assertRaises(ValueError):restore(source,root/'target/profile')
                self.assertEqual('preserve',(sibling/'payload').read_text())

    def test_consistent_backup_restore_and_stale_restore_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            vault=MemoryVault()
            node=Node(root/'source',vault)
            node.setup('Fixture')
            node.enqueue('message',{'text':'Before backup','targets':[]})
            node.sync_once()
            node.enqueue('message',{'text':'Still offline in outbox','targets':[]})
            backup(node,root/'backup')
            node.enqueue('message',{'text':'Newer than backup','targets':[]})
            with self.assertRaises(ValueError):restore(root/'backup',root/'source')
            restore(root/'backup',root/'restored')
            recovered=Node(root/'restored',vault)
            recovered.sync_once()
            self.assertEqual(2,len(recovered.snapshot()['events']))
            self.assertEqual(1,len(node.snapshot()['events']))
            self.assertNotIn(vault.get('device'), (root/'backup/manifest.json').read_text())
            for obj in (node,recovered):
                obj.db.close();obj.delivery.db.close();obj.hub.db.close()

    def test_tampered_backup_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);node=Node(root/'source',MemoryVault());node.setup('Fixture')
            backup(node,root/'backup')
            (root/'backup/device.sqlite3').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):restore(root/'backup',root/'restore')
            self.assertFalse((root/'restore').exists())
            node.db.close();node.delivery.db.close();node.hub.db.close()

    def test_legacy_staging_refuses_live_writer_and_preserves_unread_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'legacy';source.mkdir();(source/'channels').mkdir()
            state={'cursors':{'native-exact|general':17},'offered':{'native-exact|general':18},'agents':{}}
            original=json.dumps(state).encode()
            (source/'state.json').write_bytes(original)
            route={'id':'legacy-message','seq':18,'delivery_targets':[{'session':'native-exact','state':'pending','reason':''}]}
            journal=json.dumps(route)+'\n';(source/'channels/general.jsonl').write_text(journal)
            with open(source/'daemon.lock','a') as owner:
                fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(ValueError):stage_legacy(source,root/'archive')
            stage_legacy(source,root/'archive')
            self.assertEqual(original,(root/'archive/state.json').read_bytes())
            self.assertEqual(journal,(root/'archive/channels/general.jsonl').read_text())
            self.assertEqual('legacy-v2',verify(root/'archive')['kind'])
            self.assertEqual(original,(source/'state.json').read_bytes())


if __name__=='__main__':unittest.main()
