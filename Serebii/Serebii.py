import sys, time, math, io, ctypes, _thread, socket
from datetime import datetime

from PIL import Image

from tppflush import *

def img2BW(img):
    img = img.convert('L').rotate(90, expand=True)
    pixels = list(img.getdata())
    width, height = img.size
    return [pixels[i * width + j] for i in range(height)
                                  for j in range(width)]

########################################################################
############################ Global Variable ###########################
########################################################################

# 3DS IP
serverIP = '192.168.137.50' # 3DS
clientIP = '192.168.137.1'  # PC or router
# Streaming
bytes_upper = b''
bytes_lower = b''
frame_curr = -1
index_prev = -1
# Convert the "appears!" and "Go!" to a list
temp_ap = img2BW(Image.open('app.bmp'))
temp_go = img2BW(Image.open('go.bmp'))
threshold = 0.1
# How many millisecond to find a shiny Poke
chat = 15300
# Initialize the counter
start_count = 1

########################################################################
############################### Functions ##############################
########################################################################

def matchtemplate(img_r, img_t, h_t, w_diff):
    res   = 10.0
    left  = 0
    right = len(img_t)
    for i in range(w_diff + 1):
        res_iter = [abs(a-b) for a, b in zip(img_r[left:right], img_t)]
        res_iter = sum(res_iter)/len(img_t)/255.0
        left  = left  +h_t
        right = right +h_t
        res = min(res, res_iter)
    return res

def PressButton(key, sec):
    for i in range(2):
        server.press(key)
        server.send(print_sent=False)
    time.sleep(sec)
    for i in range(2):
        server.unpress(key)
        server.send(print_sent=False)
    time.sleep(sec)
    return 'OK'

def findtime(temp_app, temp_go, threshold):
    global image_upper
    for i in range(100):
        img1 = image_upper.crop((182,77,192,93))
        res = matchtemplate(img2BW(img1), temp_go, 16, 0)
        if res < threshold:
            t_app = time.time()
            time.sleep(8.0)
            for i in range(100):
                img1 = image_upper.crop((82,216,119,228))
                res = matchtemplate(img2BW(img1), temp_app, 12, 0)
                if res < threshold:
                    t_go = time.time()
                    t_use = int((t_go - t_app)*1000)
                    return t_use
                time.sleep(0.1)
        else:
            PressButton(HIDButtons.A, 0.2)
        time.sleep(0.1)
    return 0.0

def listening_thread():
    global bytes_upper
    global image_upper
    global bytes_lower
    global image_lower
    global frame_curr
    global index_prev
    while True:
        # Receive from client:
        msg, addr = s.recvfrom(2048)
        msg = bytearray(msg)
        # Parse the data header
        frame  = msg[0]
        lastlu = msg[1]
        index  = msg[3]
        # Analyze the packets
        if index == 0:
            frame_curr = frame
            index_prev = 0
            if lastlu == 0:
                bytes_lower = msg[4:]
            elif lastlu == 1:
                bytes_upper = msg[4:]
        else:
            if (frame == frame_curr) and (index == index_prev + 1):
                index_prev = index
                if lastlu == 0:
                    bytes_lower = bytes_lower + msg[4:]
                elif lastlu == 1:
                    bytes_upper = bytes_upper + msg[4:]
                elif lastlu == 16:
                    bytes_lower = bytes_lower + msg[4:]
                elif lastlu == 17:
                    bytes_upper = bytes_upper + msg[4:]
                    image_upper = Image.open(io.BytesIO(bytes_upper)).\
                                        rotate(90, expand=True)
                
########################################################################
############################# Main Program #############################
########################################################################

# Create a TCP/IP connection to the N3DS
tcp_socket = socket.create_connection((serverIP, 8000))
print('Step 1: Build TCP/IP connecton...')
print('Local IP:   %s' % tcp_socket.getsockname()[0])
print('Local port: %s' % tcp_socket.getsockname()[1])
print('N3DS IP:    %s' % tcp_socket.getpeername()[0])
print('N3DS port:  %s' % tcp_socket.getpeername()[1])
print('Step 2: Send packets to set up to streaming...')
tcp_socket.sendall(
    bytearray.fromhex('78563412e8030000000000008503\
                       0000050100005000000000001800\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000'))
tcp_socket.sendall(
    bytearray.fromhex('78563412d0070000000000000500\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000'))
tcp_socket.sendall(
    bytearray.fromhex('78563412b80b0000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000\
                       0000000000000000000000000000'))
# Receive data from UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((clientIP, 8001))
print('Step 3: Start to listen NTR Packets on port 8001...')
try:
   _thread.start_new_thread(listening_thread, ())
except:
    print ("Error: unable to start thread")
    quit()
# Create a Input Redirection connection
print('Step 4: Build inour redirection server on PC...')
server = LumaInputServer(serverIP)
time.sleep(5)

# Start Shiny Hunting
print('Step 5: Start shiny hunting...')
for count in range(start_count,10000):
    # Check if it is shiny
    t_use = findtime(temp_ap, temp_go, threshold)
    server.clear_everything()
    server.circle_pad_neutral()
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print( ('Encounter %04d' % count) +
            ' - [' + current_time + '] - ' +
           ('%i msec' % t_use) )
    if t_use > chat:
        image_upper.save('./pic/'+ ('%04d' % count) +'.jpg')
        server.return_control()
        break
    #else: image_upper.save('./pic/'+ ('%04d' % count) +'.jpg')
    # Reset
    server.touch(160,120)
    server.send(print_sent=False)
    time.sleep(0.5)
    server.return_control()
    time.sleep(0.5)
    server.touch(160,180)
    server.send(print_sent=False)
    time.sleep(0.5)
    server.return_control()
    time.sleep(0.5)
    for i in range(2):
        PressButton(HIDButtons.A, 0.2)
        time.sleep(0.5)
        server.return_control()
        time.sleep(0.5)
    # Enter the game
    server.clear_everything()
    for i in range(10):
        PressButton(HIDButtons.A, 0.2)
