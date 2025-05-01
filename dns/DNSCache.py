import pickle
import threading
from collections import defaultdict
from datetime import timedelta, datetime


class DNSCache:
    def __init__(self):
        self.cache = defaultdict(dict)
        self.lock = threading.Lock()

    def add_record(self, record):
        with self.lock:
            name = str(record.rname).lower()
            rtype = record.rtype

            if rtype not in self.cache[name]:
                self.cache[name][rtype] = []

            existing = next((r for r in self.cache[name][rtype]
                             if str(r.rdata) == str(record.rdata)), None)
            if existing:
                existing.ttl = record.ttl
                existing.timestamp = datetime.now()
            else:
                record.timestamp = datetime.now()
                self.cache[name][rtype].append(record)

    def get_records(self, name, rtype):
        name = str(name).lower()
        with self.lock:
            self._clean_expired()
            if name in self.cache and rtype in self.cache[name]:
                return self.cache[name][rtype].copy()
            return []

    def _clean_expired(self):
        now = datetime.now()
        expired = []

        for name in self.cache:
            for rtype in self.cache[name]:
                self.cache[name][rtype] = [
                    r for r in self.cache[name][rtype]
                    if now - r.timestamp < timedelta(seconds=r.ttl)
                ]
                if not self.cache[name][rtype]:
                    expired.append((name, rtype))

        for name, rtype in expired:
            del self.cache[name][rtype]
            if not self.cache[name]:
                del self.cache[name]

    def save_to_file(self, filename='dns_cache.pkl'):
        with self.lock:
            self._clean_expired()
            with open(filename, 'wb') as f:
                pickle.dump(dict(self.cache), f)

    def load_from_file(self, filename='dns_cache.pkl'):
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                with self.lock:
                    self.cache = defaultdict(dict, data)
                self._clean_expired()
                print("Кэш успешно загружен из файла")
                return True
        except FileNotFoundError:
            print("Файл кэша не найден, будет создан новый")
            return False
        except pickle.PickleError:
            print("Ошибка чтения файла кэша, будет создан новый")
            return False
