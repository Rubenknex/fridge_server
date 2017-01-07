from instrument import Instrument
import types
import socket
import errno


class Leiden_fridge(Instrument):
    def __init__(self, name, address, port):
        Instrument.__init__(self, name)

        self._socket = None
        self._address = address
        self._port = port

        self._ensure_connection = EnsureConnection(self)

        self._channels = range(10)
        self._pressures = range(1, 8)
        self._currents = range(3)

        self.add_parameter('pressure',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._pressures,
                           units='')

        self.add_parameter('current',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._currents,
                           units='A')

        self.add_parameter('resistance',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._channels,
                           units='Ohm')

        self.add_parameter('temperature',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._channels,
                           units='K')

        self.reset()

    def _connect(self):
        if self._socket is not None:
            self._disconnect()

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self._address, self._port))
        except socket.error as serr:
            print(serr)
            self._socket.close()
            self._socket = None

    def _disconnect(self):
        if self._socket is None:
            return

        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self._socket = None

    def _send(self, data):
        self._socket.send(data)

    def _recv(self, buffer_size=1400):
        return self._socket.recv(buffer_size)

    def ask(self, cmd):
        with self._ensure_connection:
            self._send(cmd)
            return self._recv()

    def reset(self):
        pass

    def do_get_pressure(self, channel):
        return self.ask('pressure{}'.format(channel))

    def do_get_current(self, channel):
        return self.ask('temperature{}'.format(channel))

    def do_get_resistance(self, channel):
        return self.ask('temperature{}'.format(channel))

    def do_get_temperature(self, channel):
        return self.ask('temperature{}'.format(channel))

    def get_server_status(self):
        return self.ask('server_status')

    def get_all():
        pass


class EnsureConnection:
    def __init__(self, instrument):
        self.instrument = instrument

    def __enter__(self):
        """Make sure we connect when entering the context."""
        if self.instrument._socket is None:
            self.instrument._connect()

    def __exit__(self, type, value, tb):
        """Possibly disconnect on exiting the context."""
        self.instrument._disconnect()
