"""Long-lived credentials live in macOS Keychain. No plaintext fallback."""
import threading


class Vault:
    def __init__(self, installation):
        from keyring.backends.macOS import Keyring
        self.backend = Keyring()
        self.service = 'app.agentroom.desktop.' + installation
        self.lock = threading.RLock()
        self.cache = {}
        self.blocked = False

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                if self.blocked:
                    raise RuntimeError('Keychain access paused; reconnect explicitly in Settings')
                try:
                    value = self.backend.get_password(self.service, key)
                except Exception:
                    self.blocked = True
                    raise RuntimeError('Keychain access paused; reconnect explicitly in Settings') from None
                if value is not None:self.cache[key] = value
                else:self.blocked = True
                return value
            return self.cache[key]

    def set(self, key, value):
        with self.lock:
            self.backend.set_password(self.service, key, value)
            self.cache[key] = value

    def retry(self):
        with self.lock:
            self.blocked = False


class MemoryVault:
    """Explicit test-only credential store; never selected by the desktop app."""
    def __init__(self):
        self.items = {}

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value):
        self.items[key] = value
