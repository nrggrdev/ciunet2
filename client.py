# echo_client.py
import pickle
import socket, sys
import time
HOST, PORT = "localhost", 50002
data = " ".join(sys.argv[1:])
print (f'data = {data}')
data='Hallo'
# create a TCP socket
socks=[]
l1=len(f"{0:2d}{0:20d}".encode())
l0=len(f"<#START>".encode())
l3=len(f"<#END>".encode())
import os
basedir=r'D:\Gesotec\TCEMNET1\ciu2'
while True:

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    socks.append(sock)
    print ('reconnect')
    try:
        while True:
            received = sock.recv(l0)
            if received=="<#START>".encode():
                d=sock.recv(l1)
                l2a,l2b = [int(i) for i in (d).split()]#len of data
                received = sock.recv(l2a)
                print(received)
                fn=received.decode()
                dfn=os.path.join(basedir,(fn))
                received = sock.recv(l2b)
                while l2b> len(received):
                    l2bb=l2b-len(received)
                    received2 = sock.recv(l2bb)
                    received+=received2

                x=pickle.loads(received)
                print(type(x))
                print(dfn)

                if type(x)==type(str()):
                    opentype='w'
                else:
                    opentype='wb'
                with open(dfn,opentype) as f:
                    data=x
                    f.write(data)
                sock.recv(l3)
    except:
        print('connection lost')
        time.sleep(1)

