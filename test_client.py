import socket

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5611

    sock = socket.socket()
    sock.connect((host, port))
#
    message = 'stop'

    sock.send(message.encode())
    data = sock.recv(1024).decode()

    #print('recieved ' + data)

    sock.send('STOP'.encode())

    sock.close()
