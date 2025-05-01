from socket import socket

import dnslib


class DNSServer:
    def __init__(self, cache):
        self.cache = cache
        self.is_exit = False
        self.socket = None
        self.upstream_socket = None

    def start(self, host, port, upstream_dns):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.socket.bind((host, port))
        self.upstream_socket.connect((upstream_dns, port))

        self.socket.settimeout(1.0)
        self.upstream_socket.settimeout(1.0)

        print(f"\nСервер запущен на {host}:{port}, используя DNS {upstream_dns}")
        print("Введите 'exit' для остановки сервера...")

        while not self.is_exit:
            try:
                query_data, addr = self.socket.recvfrom(512)
                self._process_query(query_data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Ошибка: {e}")

    def _process_query(self, query_data, addr):
        try:
            query = dnslib.DNSRecord.parse(query_data)
            qname = query.q.qname
            qtype = query.q.qtype

            cached = self.cache.get_records(qname, qtype)
            if cached:
                print(f"Данные из кэша для {qname}")
                response = query.reply()
                for record in cached:
                    response.add_answer(record)
                self.socket.sendto(response.pack(), addr)
                return

            print(f"Запрос к DNS серверу для {qname}")
            self.upstream_socket.send(query_data)
            response_data, _ = self.upstream_socket.recvfrom(512)

            self.socket.sendto(response_data, addr)

            response = dnslib.DNSRecord.parse(response_data)
            for section in [response.rr, response.auth, response.ar]:
                for record in section:
                    self.cache.add_record(record)

        except socket.timeout:
            print("Таймаут при запросе к DNS серверу")
        except Exception as e:
            print(f"Ошибка обработки запроса: {e}")

    def stop(self):
        if self.socket:
            self.socket.close()
        if self.upstream_socket:
            self.upstream_socket.close()
        self.cache.save_to_file()
        print("Кэш сохранен в файл")
