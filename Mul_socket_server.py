import socket
import time
from threading import Thread

from .__stx_etx import *
from .utils import repeated_execution

__all__ = ['VisionSocketServer']


class VisionSocketServer:
    __command_format = "AFFFV{:03d}00{}"
    __message_length = 14

    def __init__(self, server_address, server_port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.s.bind((server_address, server_port))
        self.s.listen(5)
        self.client_connection, self.client_address = self.s.accept()
        print('Connected to client:', self.client_address)
        self.pending_tasks = dict()
        self.execute_pending_tasks()
        self.echo_thread = Thread(target=self.echo_loop)
        self.echo_thread.start()

    def send(self, content, flags=0):
        print(f"{time.ctime()} sent", content.decode())
        return self.client_connection.send(content, flags)

    def receive(self, buffer=1024, flags=0):
        return self.client_connection.recv(buffer, flags).decode()

    def send_command(self, agv_id, state):
        cmd = self.__command_format.format(agv_id, state)
        return self.send(STX + self.add_checksum(cmd) + ETX)

    def send_command_repeated(self, agv_id, state, n_times=1):
        self.pending_tasks.update({(agv_id, state): n_times})

    @repeated_execution(0.05)
    def execute_pending_tasks(self):
        finished_tasks = []
        for (agv_id, state), count in self.pending_tasks.items():
            self.send_command(agv_id, state)
            count -= 1
            if count == 0:
                finished_tasks.append((agv_id, state))
            else:
                self.pending_tasks[(agv_id, state)] = count
        for finished_task in finished_tasks:
            self.pending_tasks.pop(finished_task)

    def echo_loop(self):
        while True:
            ret = self.client_connection.recv(1024)
            if len(ret) != 14 or not (ret[:1] == STX and ret[-1:] == ETX): return None
            if ret[1:6] == b'FFFAH':
                msg = ret[:1] + b'AFFFH' + ret[6:]
                # print(f'Hcode: {ret.decode()} - Return: {msg.decode()}')
                self.client_connection.send(msg)

    @staticmethod
    def add_checksum(cmd):
        if not isinstance(cmd, bytes): cmd = bytes(cmd, 'utf-8')
        return cmd + bytes(hex(sum(cmd))[-1], 'utf-8')

    @staticmethod
    def check_checksum(cmd):
        if not isinstance(cmd, bytes): cmd = bytes(cmd, 'utf-8')
        return VisionSocketServer.add_checksum(cmd[:-1]) == cmd


if __name__ == "__main__":
    vision_server = VisionSocketServer('107.125.156.34', 4001)
    i = 1
    while True:
        vision_server.send_command(agv_id=700, state=i % 2)
        i += 1
        time.sleep(1)
