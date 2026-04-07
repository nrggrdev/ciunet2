import socket
import websockets
import time
import threading
import asyncio
class  webThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.loop=asyncio.get_event_loop()
        start_server = websockets.serve(self.register, "0.0.0.0", 6789)
        self.loop.run_until_complete(start_server)
        self.webClients=set()

        self.clientSockets=set()
        self.data={}

    async def register(self,websocket,path):
        print (' new connection')
        cs=webClient(websocket)
        self.webClients.add(cs)
        self.clientSockets.add(websocket)
        await websocket.send('greeting')
        await self.notify_scanners()
        async for message in websocket:
            data = json.loads(message)
            print ('*'*80)
            print(data)
            print ('*'*80)

        while True:
            await asyncio.sleep(1)