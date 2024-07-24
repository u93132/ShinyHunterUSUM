import sys, time, math, io, ctypes, _thread, socket
from tppflush import *

########################################################################
############################ Global Variable ###########################
########################################################################

# 3DS IP
serverIP = '192.168.137.50'

server = LumaInputServer(serverIP)
time.sleep(5)

server.return_control()
