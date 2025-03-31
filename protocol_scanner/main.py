import threading
from socket import *


def check_port(host, port_num, protocol_type):
    connection = socket(AF_INET, SOCK_STREAM)
    connection.settimeout(0.1)
    try:
        if protocol_type == "TCP":
            status = connection.connect_ex((host, port_num))
            if status == 0:
                print(f"\nПорт {port_num}: Доступен (TCP)")
            else:
                print(f"\nПорт {port_num}: Недоступен (TCP)")
        elif protocol_type == "UDP":
            connection.connect_ex((host, port_num))
            try:
                connection.sendto(b'\x11', (host, port_num))
                print(f"\nПорт {port_num}: Доступен (UDP)")
            except:
                print(f"\nПорт {port_num}: Недоступен (UDP)")
    finally:
        connection.close()


def parallel_port_check(host, first_port, last_port, protocol_type):
    for current_port in range(first_port, last_port + 1):
        thread = threading.Thread(target=check_port, args=(host, current_port, protocol_type))
        thread.start()


def main():
    target_host = input("Укажите IP адрес для проверки: ")
    port_range = input("Укажите диапазон портов: ").split()
    selected_protocol = input("Выберите тип проверки (TCP/UDP): ").upper()

    parallel_port_check(
        target_host,
        int(port_range[0]),
        int(port_range[1]),
        selected_protocol
    )

if __name__ == "__main__":
    main()