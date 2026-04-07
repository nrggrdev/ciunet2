import socket
import threading
import time
import numpy
import pickle
import sys
import os
import logging
import json
import asyncio
import websockets
def is_socket_closed(sock: socket.socket) -> bool:
    try:
        # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        # data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        data = sock.recv(16, socket.MSG_DONTWAIT)
        if len(data) == 0:
            return True
    except BlockingIOError:
        print('Block')

        return False  # socket is open and reading from it would block
    except ConnectionResetError:
        print('connection reset')
        return True  # socket was closed for some other reason
    except Exception as e:
        print(e)
        raise
    print('ok')
    print(data)
    #        return False
    return False

class webClient:
    def __init__(self, sock):#
        self.connectTime=time.time()
        self.lastUpdateTime=0
        self.updates=0
        self.socket=sock
        ip,port=sock.remote_address
        self.ip=ip
        self.port=port
    def getStats(self):
        data={}
        data['connect']=self.connectTime
        data['ip']=self.ip
        data['updates']=self.updates
        data['lastUpdate']=self.lastUpdateTime
        data['port']=self.port
        id=f"{self.ip}:{self.port}"
        return {'id':id}, data

    def update(self):
        self.lastUpdateTime=time.time()
        self.updates+=1

class  webThread(threading.Thread):
    def __init__(self,loop):
        print ('HAAAAAAAAAAAAAAAAAAAAALLLLLLLLLLLLLLLLOOOOOOOOOOOOOOOOOOOO')
        threading.Thread.__init__(self)
        self.daemon=True

        self.loop=loop
        print ('websocket.....')

        start_server = websockets.serve(self.register, "0.0.0.0", 6788)
        self.loop.run_until_complete(start_server)
        self.webClients=set()
        self.clientSockets=set()
        self.data={}


    def setData(self,data):
        self.data=data
        try:
            asyncio.run(self.notify_scanners())
        except Exception as e:
            print(e)
    async def register(self,websocket,path):
        print (' new connection')
        cs=webClient(websocket)
        self.webClients.add(cs)
        self.clientSockets.add(websocket)
        await websocket.send('greeting')
        # await self.notify_scanners()
        # async for message in websocket:
        #     data = json.loads(message)
        #     print ('*'*80)
        #     print(data)
        #     print ('*'*80)

        while True:
            await asyncio.sleep(1)
    def getClientstat(self):
        data=[]
        for wc in self.webClients:
            data.append(wc.getStats())
        return str(json.dumps({'clients':data}))
    async def notify_scanners(self ):
        if self.clientSockets:  # asyncio.wait doesn't accept an empty list
            message = self.data
            print (type(message))
            old_socks=[]
#            await asyncio.wait([clientSocket.send(message) for clientSocket in self.clientSockets])
            for ws in self.webClients:
                ws.update()
                clientSocket=ws.socket
                print (clientSocket)
#            for clientSocket in self.clientSockets:
                print (clientSocket.remote_address)
                try:
                    await clientSocket.send(message)
                except Exception as e:
                    print(e)
                    print('POP')
                    old_socks.append(ws)
#                self.loop.create_task(clientSocket.send(message))
            for s in old_socks:
                self.webClients.remove(s)
    def run(self):

        self.loop.run_forever()

class tcemServer(threading.Thread):
    def __init__(self,config):
        threading.Thread.__init__(self,daemon=True)
        self.logger = logging.getLogger("TCEMServer")
        self.clients = set()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        config={"port":55551}|config
        print (config)
        print("_"*80)
        port=int(config["port"])
        server.bind(("", port))

        #        server.setblocking(False)
        server.listen(5)
        self.server = server

    def serve(self):
        while True:
            a, b = self.server.accept()
            self.clients.add(a)
            print(a)
            print('*'*80)

    def run(self):
        self.serve()

    def checkAkiveClients(self):
        remvers = []
        for c in self.clients:
            print(c, is_socket_closed(c))
            if is_socket_closed(c):
                remvers.append(c)
        for c in remvers:
            print(f'client{c} closed connection')
            self.clients.remove(c)

    def broadCastData(self, data, targetfile):
        data = pickle.dumps(data)
        self.removers=[]
        for c in self.clients:
            print (f'{c}')
            try:
                d2 = f"<#START>{len(targetfile):2d}{len(data):20d}{targetfile}".encode() + data + "<#END>".encode()
                c.sendall(d2)
            except Exception as e:
                print(c, e)
                self.removers.append(c)
#                self.checkAkiveClients()
        for c in self.removers:
            c.close()
            self.clients.remove(c)


#    def __del__(self):
#        self.server.close()


if __name__ == '__main__':
    s = tcemServer()
    s.start()

    try:
        data = f'{time.time()}: new Data...\n'

        data = numpy.asarray(list(range(20000000)))

        while True:
            time.sleep(0.01)
            print(time.time())
            print(s.clients)
            remvers = []
            fn = os.path.abspath(os.curdir)
            s.broadCastData(data, fn)
    finally:
        s.server.close()
        s.join()