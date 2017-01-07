import datetime
import logging
import select
import socket
import threading
import time
import traceback
import queue
import win32com.client

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Change the formatting
ch = logging.StreamHandler()
fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)

running = True


def list_to_string(l):
    return ','.join(map(str, l))


class LabViewApp():
    """ Represents a LabView application """

    def __init__(self, application, vi):
        self.app = win32com.client.Dispatch(application)
        self.vi = self.app.GetViReference(vi)

    def get_data(self, name):
        return self.vi.GetControlValue(name)

    def set_data(self, control_name, control_data, Async=False):
        if type(control_data) in (tuple, list):
            self.vi.SetControlValue('SetControl',
                                    (control_name, '', control_data))
        else:
            self.vi.SetControlValue('SetControl',
                                    (control_name, control_data, [[], []]))

        if not Async:
            while self.vi.GetControlValue('SetControl')[0] != '':
                time.sleep(0.1)


class QueueThread(threading.Thread):
    """ Processes commands in the queue. """

    def __init__(self, name, work_queue, lock):
        threading.Thread.__init__(self, name=name)

        self.work_queue = work_queue
        self.lock = lock

    def run(self):
        global running

        logger.info('Starting main queue thread')

        # We have to call CoInitialize to get the COM working with threads
        win32com.client.pythoncom.CoInitialize()

        # Connect to the fridge software
        self.tc = LabViewApp('DRTempControl.Application',
                             'DR TempControl.exe\TC.vi')

        self.fp = LabViewApp('DRFrontPanel.Application',
                             'DR FrontPanel.exe\FP.vi')

        while running:
            self.lock.acquire()

            if not self.work_queue.empty():
                sock, data = self.work_queue.get()
                self.lock.release()

                self.handle_command(sock, data)
            else:
                self.lock.release()
                time.sleep(0.1)

        logger.info('Exiting queue thread, socket thread will exit within 60s')

    def handle_command(self, sock, command):
        """ Parses an incoming command and sends the response back. """
        response = ''

        try:
            if command.startswith('all_temperatures'):
                response = list_to_string(self.tc.get_data('T'))
            elif command.startswith('all_currents'):
                response = list_to_string(self.tc.get_data('I'))
            elif command.startswith('all_resistances'):
                response = list_to_string(self.tc.get_data('R'))
            elif command.startswith('temperature'):
                response = str(self.tc.get_data('T')[int(command[-1])])
            elif command.startswith('current'):
                response = str(self.tc.get_data('I')[int(command[-1])])
            elif command.startswith('resistance'):
                response = str(self.tc.get_data('R')[int(command[-1])])
            elif command.startswith('pressure'):
                response = str(self.fp.get_data('P{}'.format(command[-1])))
            else:
                logger.error('Command ' + command + ' not recognized')

                response = 'command not recognized'
        except (win32com.client.pythoncom.com_error, Exception) as e:
            logger.error(traceback.format_exc())
            logger.error(e)

            response = 'error executing command, see server log'

        addr = sock.getpeername()

        try:
            logger.info(str(addr) + ': Sending: ' + response)
            sock.send(response.encode())
        except Exception as e:
            logger.error(str(addr) + ': Error sending response:')
            logger.error(str(e))
        finally:
            logger.info(str(addr) + ': Closing connection')
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()


class SocketThread(threading.Thread):
    """ Accepts connections and puts commands into the queue. """

    def __init__(self, name, work_queue, lock):
        threading.Thread.__init__(self, name=name)

        self.work_queue = work_queue
        self.lock = lock

    def run(self):
        global running

        logger.info('Starting socket thread')

        start_time = datetime.datetime.now()

        recv_buffer = 4096
        addr = '0.0.0.0'
        port = 5611
        connections = []

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((addr, port))
        server_socket.listen(5)

        logger.info('Listening at ' + str((addr, port)))

        connections.append(server_socket)

        while running:
            read_socks, write_socks, error_socks = select.select(connections,
                                                                 [], [], 60)

            for sock in read_socks:
                if sock == server_socket:
                    # Accept a new incoming connection
                    new_socket, addr = server_socket.accept()
                    connections.append(new_socket)

                    logger.info(str(addr) + ': Accepted connection request')
                else:
                    try:
                        # Recieve a command and append it to the work queue
                        data = sock.recv(recv_buffer).decode().rstrip().lower()

                        if data:
                            addr = sock.getpeername()
                            logger.info(str(addr) + ': Recieved: ' + data)

                            if data == 'stop':
                                running = False
                            elif data == 'server_status':
                                uptime = str(datetime.datetime.now() - start_time)
                                response = 'Uptime: {}, connections: {}'.format(
                                    uptime, len(connections) - 1)

                                sock.send(response.encode())
                                sock.shutdown(socket.SHUT_RDWR)
                            else:
                                with self.lock:
                                    self.work_queue.put((sock, data))

                        connections.remove(sock)
                    except Exception as e:
                        logger.info(str(e))
                        sock.close()
                        connections.remove(sock)

        logger.info('Closing server socket and exiting thread')
        server_socket.close()


if __name__ == '__main__':
    lock = threading.Lock()
    work_queue = queue.Queue(100)

    queue_thread = QueueThread('queue_thread', work_queue, lock)
    queue_thread.start()

    socket_thread = SocketThread('socket_thread', work_queue, lock)
    socket_thread.start()

    queue_thread.join()
    socket_thread.join()
