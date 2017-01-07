from qcodes import IPInstrument


class LeidenFridge(IPInstrument):
    """
    Driver that talks to the Leiden fridge software via an intermediate
    server script.
    """

    def __init__(self, name, address, port, timeout=20, **kwargs):
        super().__init__(name, address=address, port=port, timeout=timeout,
                         persistent=False)

        for i in range(10):
            self.add_parameter(name='temperature{}'.format(i),
                               get_cmd='temperature{}'.format(i),
                               get_parser=float)

        for i in range(3):
            self.add_parameter(name='current{}'.format(i),
                               get_cmd='current{}'.format(i),
                               get_parser=float)

        for i in range(10):
            self.add_parameter(name='resistance{}'.format(i),
                               get_cmd='resistance{}'.format(i),
                               get_parser=float)

        self.add_parameter(name='server_status',
                           get_cmd='server_status')

        self.connect_message()

    def connect_message(self):
        pass

    def get_idn(self):
        pass
