import threading


from dns.DNSCache import DNSCache
from dns.DNSServer import DNSServer


def check_exit(server):
    while not server.is_exit:
        try:
            inp = input()
            if inp == 'exit':
                server.is_exit = True
        except (EOFError, KeyboardInterrupt):
            server.is_exit = True


def main():
    print("\nDNS кэширующий сервер")
    host = input("Укажите IP-адрес хоста: ").strip()
    upstream = input("Укажите IP DNS сервера: ").strip()

    cache = DNSCache()
    cache_loaded = cache.load_from_file()

    if not cache_loaded:
        print("Кеш пуст")

    server = DNSServer(cache)
    exit_thread = threading.Thread(target=check_exit, args=(server,))
    exit_thread.start()

    try:
        server.start(host, 53, upstream)
    except OSError as e:
        print(f"Ошибка запуска сервера: {e}")
    except KeyboardInterrupt:
        print("\nПолучен сигнал прерывания")
    finally:
        server.stop()
        exit_thread.join()
        print("Сервер остановлен")


if __name__ == '__main__':
    main()
