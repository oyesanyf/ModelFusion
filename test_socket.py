import socket
s = socket.socket()
s.connect(('127.0.0.1', 5001))
s.sendall(b'POST /orchestrate HTTP/1.1\r\nHost: 127.0.0.1:5001\r\nContent-Length: 12\r\n\r\nhello world!')
print('Sent')
print(s.recv(1024))
