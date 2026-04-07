#------------------------------------------------------------------------------------------
__version__ = "1.2204.00"
#===---------------------------------------------------------------------------------------
import sys
import time
import socket
import logging
import argparse
import linecache
import re



from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

#----------------------------------------------------------

def PrintException():
    """
    always print exceptions including line numbers for better debugging
    """

    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    logging.error(f'EXCEPTION IN ({filename}, LINE {lineno} "{line.strip()}"): {exc_obj}')



def init_logger(loggername, loglevel, logfilename):
    """
    initialize the logging handler
    """
    logger = logging.getLogger(loggername)
    logger.setLevel(loglevel)
    # create file handler which logs even debug messages
    fh = TimedRotatingFileHandler(logfilename, when='midnight', interval=args.logfilebackupcount)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # fh.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


def getArguments():
    """
    initialize argument parser
    """
    parser = argparse.ArgumentParser(prog=sys.argv[0], description='\
                                     copies all relevant TCEM files for a TCEM client over network ', 
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--port', help='TCP port to use.',
                        type=int,
                        required=False,
                        default=5001,
                        )
    parser.add_argument('--buffersize', help='transfer buffer size',
                        type=int,
                        required=False,
                        default=1024,
                        )

    parser.add_argument('--loglevel', help='set the log level [CRITICAL=50, ERROR=40, WARNING=30, INFO=20, DEBUG=10, NOTSET=0]',
                        type=int,
                        required=False,
                        default=30,
                        )
    parser.add_argument('--logfilebackupcount', help='After x days overwrite the log files',
                    type=int,
                    required=False,
                    default=30,
                    )



    parser.add_argument('-v', '--version',
                        action='version',
                        version="%(prog)s (" + __version__ + ")")

    """
        Server Argument Group
    """
    server = parser.add_argument_group('Server (Sender) arguments')
    server.add_argument('-s', '--src', help='Enter the TCEM src Path (this is where we watch for changed files)',
                        type=Path,
                        required=False,
                        default="d:/GESOTEC/TCEMNET2"
                        )
    server.add_argument('-t', '--sleeptime', help='time to sleep between file change recognition and reading --> sending the files',
                        type=float,
                        required=False,
                        default=0.25
                        )

    server.add_argument('--clienthost', help='Client IP-address (to which address you want to send files)',
                        type=str,
                        required=False,
                        default="127.0.0.1",
                        )
    """
    Client Argument Group
    """
    client = parser.add_argument_group('All client parameters')
    client.add_argument('--clientmode', help='put program in client mode',
                        required=False,
                        default=False,
                        action='store_true'
                        )

    client.add_argument('--listening_ip', help='host address (on which ip address (device)  we are listening to receive files)',
                        required=False,
                        default="0.0.0.0",
                        )

    client.add_argument('-d', '--destdir', help='TCEM path directory on the client machine',
                        type=Path,
                        required=False,
                        default="d:/GESOTEC/TCEMNET1",
                        )

    try:
        args = parser.parse_args()
    except Exception as e:
        logging.error(f"{PrintException()}")
    return args


def send_file(filename):
    """
    Send the file via network
    """
    SEPARATOR = "<SEPARATOR>"
    
    BUFFER_SIZE = args.buffersize  # send 4096 bytes each time step
    # the ip address or hostname of the server, the receiver
    host = args.clienthost
    # the port, let's use 5001
    port = args.port
    # the name of file we want to send, make sure it exists
    filenamefilter = Path(filename).name
    # get the file size
    filesize = Path(filename).stat().st_size

    logging.info(f"Filesize of {filename} {filesize}")
    # create the client socket
    s = socket.socket()
    logging.info(f"[+] Connecting to {host}:{port}")
    try:
        s.connect((host, port))
        logging.info("[+] Connected.")
    except:
        logging.error(f"Connect Error {PrintException()}")
    
    # send the filename and filesize
    x=f"{filenamefilter}{SEPARATOR}{filesize}".encode()
    l=str(len(x)).encode()
    logging.info(f'ultralänge {l}')
    s.send(l)
    s.send(x)
    s.close()
    s =socket.socket()
    s.connect((host, port))
    logging.info(f"Sending {filename}")

    with open(filename, 'rb') as f:
        s.sendfile(f, 0)
    s.close()
   
class SerialFileHandler(FileSystemEventHandler):
    """ 
    Serial File watch handler (we start sending the TCEM files on serial file change recognition)
    """

    def __init__(self, filetocheck):
        self.filetocheck = filetocheck
        logging.info(f"SerialFileHandler: checking {self.filetocheck} for changes....")
        self.serialfile = Path(self.filetocheck).name
        self.filter_regex = re.compile(self.serialfile, re.IGNORECASE)

    def on_modified(self, event):
        logging.info(event)
        time.sleep(args.sleeptime)
        if self.filter_regex.search(self.serialfile):
            logging.info(f"Matched file change: '{self.filetocheck}'.")
            logging.info(
                f"File to check is: {self.filetocheck}" 
            )

            try:
                send_file(Path(args.src) / "ciu1/IMAGE1.0")
            except:
                logging.error(f"Could not send: {Path(args.src) / 'ciu1/IMAGE1.0'}. Error {PrintException()}")
            try:
                send_file(Path(args.src) / "ciu1/IMAGE1.1")
            except:
                logging.error(f"Could not send: {Path(args.src) / 'ciu1/IMAGE1.1'}. Error {PrintException()}")
            
            # we are sending the serial file AFTER the image files (to make sure that the images are transferred before the clients tries to load the file)
            try:
                send_file(self.filetocheck)
            except:
                logging.error(f"Could not send: {self.filetocheck}. Error {PrintException()}")


            try:
                send_file(Path(args.src) / "ciu1/Tire/tirecr.1")
            except:
                logging.error(f"Could not send: {Path(args.src) / 'ciu1/Tire/tirecr.1'}. Error {PrintException()}")
            try:
                send_file(Path(args.src) / 'ciu1/Window/window.1')
            except:
                logging.error(f"Could not send: {Path(args.src) / 'ciu1/Window/window.1'}. Error {PrintException()}")
            try:
                send_file(Path(args.src) / 'ciu1/lining1.ini')
            except:
                logging.error(f"Could not send: {Path(args.src) / 'ciu1/lining1.ini'}. Error {PrintException()}")


def StartWatchCopy(argument):
    """
    Start filewatcher and copy files to other PC
    """
    logging.info(f"Starting directory observer on '{argument}'")
    event_handler = SerialFileHandler(argument)
    observer = Observer()
    observer.schedule(event_handler, path=str(Path(argument).parent), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def receive_files():
    
    SEPARATOR = "<SEPARATOR>"
    # logging.info(f"FILEINFO_SIZE: {FILEINFO_SIZE}")
    BUFFER_SIZE = args.buffersize
    # device's IP address
    SERVER_HOST = args.listening_ip
    SERVER_PORT = args.port
    logging.info(
        f"Buffersize: {BUFFER_SIZE}, "
        f"LISTENING ON: {SERVER_HOST}:{SERVER_PORT}"
        )
    # create the server socket
    # TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the socket to our local address
    s.bind((SERVER_HOST, SERVER_PORT))
    # enabling our server to accept connections
    # 10 here is the number of unaccepted connections that
    # the system will allow before refusing new connections
    s.listen(5)
    logging.info(80*'*')


    while 1:
        try:
            # accept connection if there is any
            client_socket, address = s.accept()
#            print (address)

            while True:
                try:

                    received = client_socket.recv(2)
                    l=len(received)

                    if l!=2:
                        #time.sleep(0.1)
                        #continue
                        logging.debug('no data pending -> close remote socket')
                        client_socket.close()
                        break
                    try:
                        i=int(received.decode())
                    except Exception as e:
                        logging.warning(e)
                        print ('i',received,i)
                        print('*'*80)
                        client_socket.close()
                        break

                    logging.debug(f'header_size: {l}, {received} [{i}]')
                    
                    received = client_socket.recv(i)
                    l=len(received)
                    logging.debug(f"size filedescriptor:{l}")
                    try:
                        received = received.decode()

                    except Exception as e:
                        logging.warning(e)
                        print (received,i,l)
                        print('*'*80)
                        client_socket.close()
                        break

 #                       raise(e)
#                    l=len(received)

                    if l!=i:
                        #time.sleep(0.1)
                        #continue
                        logging.debug('len not matching -> close remote socket')
                        client_socket.close()
                        break
                    try:
                        filename, filesize = received.split(SEPARATOR)
                    except Exception as e:
                        logging.warning(e)
                        print (received)
                        print('*'*80)
                        client_socket.close()
                        break


                    filename, filesize = received.split(SEPARATOR)
                    filename = Path(filename).name
                    logging.debug(f"Filename: {filename}, size:{filesize}")
                    if filename == "serial1.ciu":
                        filename = Path(args.destdir / "ciu1" / filename)
                        logging.debug(f"serial1.ciu will be written to {filename}")

                    if filename == "IMAGE1.0":
                        filename = Path(args.destdir / "ciu1" / filename)
                        logging.debug(f"IMAGE1.0 will be written to {filename}")

                    if filename == "IMAGE1.1":
                        filename = Path(args.destdir / "ciu1" / filename)
                        logging.debug(f"IMAGE1.1 will be written to {filename}")

                    if filename == "tirecr.1":
                        filename = Path(args.destdir / "ciu1/tire" / filename)
                        logging.debug(f"tirecr.1 will be written to {filename}")

                    if filename == "window.1":
                        filename = Path(args.destdir / "ciu1/window" / filename)
                        logging.info(f"window.1 will be written to {filename}")

                    if filename == "lining1.ini":
                        filename = Path(args.destdir / "ciu1" / filename)
                        logging.debug(f"lining1.ini will be written to {filename}")

                    with open(filename, 'wb') as f:
                        bl=0
                        fs=int(filesize)
                        rc=0
                        while True:

                            # read args.buffersize bytes from the socket (receive)
                            bytes_read = client_socket.recv((fs))
                            
                            bl=len(bytes_read)
                            if bl==0:
                                rc+=1
                                time.sleep(0.03)
                                if rc>5:
                                    e=Exception
                                    raise(e)
                            fs-=bl
                            logging.debug(f'{bl} of {filesize} bytes processed, {fs} to remaining')
                            f.write(bytes_read)
                            logging.debug(f'writing {filename}')

                            if fs<=0:
                                break

                        logging.debug(f'{filename} written')

                except Exception as e:
                    logging.warning(e)
                    raise

        except Exception as e:
            logging.error(f"{PrintException()}")
            client_socket.close()
            pass
 

if __name__ == "__main__":
    args = getArguments()

    args.clientmode = True
    

    logging = init_logger("Tcem client sync", args.loglevel, f'{Path(sys.argv[0]).name}.log' )
    
    logging.info(80*'*')
    logging.info(f'TCEM client Sync started')
    # initialize argument parser
    logging.info(f'Loglevel: {logging.getEffectiveLevel()}')

    if not args.clientmode:
        
        if not args.src:
            logging.error(f"{args.src} does not exist! Exiting....")
            sys.exit(1)
        
        StartWatchCopy(Path(args.src / "ciu1/serial1.ciu"))

    else:
        logging.info("Clientmode! Listening on TCP port, waiting for files coming from the server.")
        try:
            receive_files()
        except:
            logging.error(f"{PrintException()}")