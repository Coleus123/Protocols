import socket
import struct
import json
import time
import threading
from utils import parse_dns_response, extract_records, build_dns_response

CACHE_FILE = 'cache.json'
PORT = 53
UPSTREAM_DNS = '8.8.8.8'
BUFFER_SIZE = 512

# Кэш: ключ=(rtype, name), значение=список записей с TTL и временной меткой
cache = {}
cache_lock = threading.Lock()  # Добавляем блокировку для потокобезопасного доступа к кэшу


def load_cache():
    global cache
    try:
        with open(CACHE_FILE, 'r') as f:
            raw = json.load(f)
            now = time.time()
            with cache_lock:  # Блокировка при загрузке
                for key in list(raw):
                    raw[key] = [r for r in raw[key] if now - r['timestamp'] < r['ttl']]
                    if not raw[key]:
                        del raw[key]
                cache = raw
            print(f"[INFO] Кэш загружен. Записей: {len(cache)}")
    except FileNotFoundError:
        print("[INFO] Кэш не найден. Начинаем с пустого кэша.")
        cache = {}
    except json.JSONDecodeError:
        print("[WARNING] Ошибка при загрузке кэша. Возможно, файл поврежден. Начинаем с пустого кэша.")
        cache = {} # Если кэш не загрузился, нужно его создать


def save_cache():
    with cache_lock:  # Блокировка при сохранении
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)


def cleanup_cache():
    while True:
        time.sleep(60)
        now = time.time()
        with cache_lock:  # Блокировка при очистке
            for key in list(cache):
                cache[key] = [r for r in cache[key] if now - r['timestamp'] < r['ttl']]
                if not cache[key]:
                    del cache[key]
        save_cache()
        print(f"[INFO] Кэш очищен. Активных записей: {len(cache)}")


def handle_request(data, addr, sock):
    try:
        query_name, query_type, tid = parse_dns_response(data)
        key = f"{query_type}:{query_name}"
        now = time.time()

        # Проверка кэша
        with cache_lock:  # Блокировка при доступе к кэшу
            valid_records = [r for r in cache.get(key, []) if now - r['timestamp'] < r['ttl']]
            if valid_records:
                print(f"[CACHE HIT] {query_name} (type {query_type})")
                response = build_dns_response(tid, data, valid_records, query_name, query_type)
                sock.sendto(response, addr)
                return
            else:
                if key in cache:  # Ensure key exists before deleting
                    del cache[key]

        print(f"[CACHE MISS] {query_name} (type {query_type})")

        # Запрос к вышестоящему DNS
        upstream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        upstream.settimeout(5)
        upstream.sendto(data, (UPSTREAM_DNS, 53))

        response, _ = upstream.recvfrom(BUFFER_SIZE)
        sock.sendto(response, addr)

        # Парсинг всех полезных записей
        records = extract_records(response)
        with cache_lock:  # Блокировка при обновлении кэша
            for rec in records:
                k = f"{rec['type']}:{rec['name']}"
                cache.setdefault(k, []).append({
                    'name': rec['name'],  # Добавить имя
                    'type': rec['type'],  # Добавить тип
                    'data': rec['data'],
                    'ttl': rec['ttl'],
                    'timestamp': time.time()
                })

    except Exception as e:
        print(f"[ERROR] Ошибка при обработке запроса: {e}. Данные: {data.hex()}")  # Добавлена распечатка данных
        import traceback
        traceback.print_exc()  # Добавлено отображение стека вызовов


def run_dns_server():
    load_cache()
    threading.Thread(target=cleanup_cache, daemon=True).start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', PORT))
        print(f"[STARTED] DNS-сервер запущен на порту {PORT}.")

        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            threading.Thread(target=handle_request, args=(data, addr, sock)).start()
    except PermissionError:
        print(f"[ERROR] Для работы на порту {PORT} требуются права администратора.")
    except Exception as e:
        print(f"[ERROR] Сервер остановлен: {e}")
        import traceback
        traceback.print_exc()
    finally:
        save_cache()


if __name__ == '__main__':
    run_dns_server()