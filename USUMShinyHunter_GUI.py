import sys, os, time, math, io, ctypes, threading, socket, signal
from datetime import datetime

from PIL import Image, ImageTk
from tppflush import *

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from functions import *
import boxBase

from General import *
from Battle  import *
from Recv    import *
from Lotto   import *

# Define the application class
class ShinyHunterUSUM(tk.Tk):
    def __init__(self, *args, **kwargs):
        
        ########################################################################
        ############################## Initialize ##############################
        ########################################################################
        
        # Initialize tk
        tk.Tk.__init__(self, *args, **kwargs)
        self.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.title('Shiny Hunter USUM')
        # Fonts from Windows OS
        myFont = tkfont.Font(family=FindFont(), size=9)
        self.option_add( '*font', myFont )
        # Load Icons
        self.iconbitmap(bitmap=str(resource_path('image0/star.ico')))
        # Locate to the middle
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        # Dimension of the GUI
        w=290
        h=450
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        self.resizable(width=False, height=False)
        # Load images in ./image0
        self.bitmap = load_bitmaps('image0')
        # Parameters
        self.bytes = [b'', b'']
        self.image = [None,None]
        self.frame_curr = -1
        self.index_prev = -1
        
        ########################################################################
        ########################## GUI objects : Row 0 #########################
        ########################################################################
      
        # Frame Row 0
        self.frame0 = tk.LabelFrame(self, text = 'Screen')
        self.frame0.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
        # Frame and objects for upper screen
        self.upperVal   = tk.IntVar()
        self.upperframe = tk.Frame(self.frame0)
        self.upperframe .grid(row=0, column=0, padx=0, pady=0, sticky='w')
        self.upperlabel = tk.Label(self.upperframe, image=self.bitmap['Upper'])
        self.upperlabel .config(height=72, width=120)
        self.upperlabel .grid(row=0, column=0, padx=12, pady=5, sticky='w')
        self.upperbtn   = tk.Checkbutton(self.upperframe, variable=self.upperVal,
                                         command=self.screenSwitch)
        self.upperbtn   .grid(row=1, column=0, padx=10, pady=0)
        # Frame and objects for lower screen
        self.lowerVal   =tk.IntVar()
        self.lowerframe = tk.Frame(self.frame0)
        self.lowerframe .grid(row=0, column=1, padx=0, pady=0, sticky='e')
        self.lowerlabel = tk.Label(self.lowerframe, image=self.bitmap['Lower'])
        self.lowerlabel .config(height=72, width=96)
        self.lowerlabel .grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.lowerbtn   = tk.Checkbutton(self.lowerframe, variable=self.lowerVal,
                                         command=self.screenSwitch)
        self.lowerbtn   .grid(row=1, column=0, padx=5, pady=0)

        ########################################################################
        ########################## GUI objects : Row 1 #########################
        ########################################################################

        # Notebook for settings and additional features
        self.nb = ttk.Notebook(self)
        self.nb .grid(row=1, column=0, padx=10, pady=0, sticky='ew')
        # Notebook format
        style   = ttk.Style()
        style.theme_create( 'MyStyle', parent='alt', settings={
                'TNotebook': {'configure': {'tabmargins': [2, 2, 2, 0]}},
                'TNotebook.Tab': {'configure': {'padding': [5, 0]}},
                'TCombobox': {'configure': {'padding': 2, 'arrowsize': 15}}
                })
        style.theme_use('MyStyle')
        # Notebook tags, additional features are controlled here
        self.nb.framename = ['General', 'Battle', 'Recv', 'Lotto']
        self.nb.frame = [None for i in self.nb.framename]
        for i in range(len(self.nb.framename)):
            self.nb.frame[i]=tk.Frame(self.nb)
            self.nb.frame[i].config(height=105, width=250)
            self.nb.frame[i].pack()
            self.nb.add(self.nb.frame[i], text=self.nb.framename[i])
    
        ########################################################################
        ############################## Message Box #############################
        ########################################################################
            
        # Message Box
        self.message = ['']
        self.frame2 = tk.Frame(self)
        self.frame2.grid(row=2, column=0, padx=10, pady=0, sticky='ew')
        self.msgbox = msgBox(self.frame2, 35, 10)

        ########################################################################
        ################################ Notebook ##############################
        ########################################################################

        # Connect Notebook object with base class functions
        self.General = General(self.nb, self.msgbox)
        self.General .ConnectButton.config(command=self.Connect3DS)
        self.General .ReturnButton .config(command=self.ReturnControl)
        self.General .setting.bind('<<ComboboxSelected>>', self.settingswitch)

        self.Lotto  = Lotto (self.nb, self.General, self.msgbox, self.image)
        self.Recv   = Recv  (self.nb, self.General, self.msgbox, self.image)
        self.Battle = Battle(self.nb, self.General, self.msgbox, self.image)

        currset = self.General.data[0]
        self.General.setting.set(self.General.settinglist[currset])
        self.data2GUI(currset)

    ############################################################################
    ############################## Class Functions #############################
    ############################################################################

    def on_closing(self):
        # Return control to physical buttons when closing application
        try:
            self.ir.return_control()
        except Exception:
            self.destroy()
            return
        # The packed exe needs a hard exit, plain destroy() in dev
        if getattr(sys, 'frozen', False):
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            self.destroy()

    def screenSwitch(self):
        # To have better performance, only one screen is updating
        if int(self.upperVal.get()) == 1:
            self.lowerVal.set(0)
            self.lowerbtn.config(state = 'disabled')
        else:
            self.upperlabel.config(image = self.bitmap['Upper'])
            self.lowerbtn.config(state = 'normal')
        if int(self.lowerVal.get()) == 1:
            self.upperVal.set(0)
            self.upperbtn.config(state = 'disabled')
        else:
            self.lowerlabel.config(image = self.bitmap['Lower'])
            self.upperbtn.config(state = 'normal')

    def background_thread(self):
        # Fetch data from the UDP socket 
        while True:
            if str(self.General.ConnectButton['relief']) == 'raised':
                self.upperlabel.config(image = self.bitmap['Upper'])
                self.lowerlabel.config(image = self.bitmap['Lower'])
                try:
                    self.udp_socket.shutdown(socket.SHUT_RDWR)
                    self.udp_socket.close()
                except OSError:
                    pass  # already closed by ConnectState(0)
                break
            # Receive from client:
            try:
                msg, addr = self.udp_socket.recvfrom(2048)
                msg = bytearray(msg)
            except OSError:
                # Closing the socket on purpose also lands here; only
                # report when we are still supposed to be connected
                if str(self.General.ConnectButton['relief']) == 'sunken':
                    self.msgbox.MsgAppend('Error: Packet receive error')
                continue
            # Skip malformed packets (header needs at least 4 bytes)
            if len(msg) < 4:
                continue
            # Parse the data header
            frame  = msg[0]
            lastlu = msg[1]
            index  = msg[3]
            # Analyze the packets
            try:
                if index == 0:
                    self.frame_curr = frame
                    self.index_prev = 0
                    if lastlu == 0:
                        self.bytes[0] = msg[4:]
                    elif lastlu == 1:
                        self.bytes[1] = msg[4:]
                else:
                    if ( (frame == self.frame_curr) and
                         (index == self.index_prev + 1) ):
                        self.index_prev = index
                        if lastlu == 0:
                            # Lower frame not last packet
                            self.bytes[0] = self.bytes[0] + msg[4:]
                        elif lastlu == 1:
                            # Upper frame not last packet
                            self.bytes[1] = self.bytes[1] + msg[4:]
                        elif lastlu == 16:
                            # Lower frame last packet
                            self.bytes[0] = self.bytes[0] + msg[4:]
                            self.image[0] = ( Image.open(
                                                 io.BytesIO(self.bytes[0])).\
                                                 rotate(90, expand=True) )
                            if int(self.lowerVal.get()) == 1:
                                img = ImageTk.PhotoImage(
                                          self.image[0].resize((96,72)) )
                                self.lowerlabel.config(image = img)
                                self.lowerlabel.image = img  # keep a reference, or Tk loses the image
                                self.upperlabel.config(image = self.bitmap['Upper'])
                            else:
                                self.lowerlabel.config(image = self.bitmap['Lower'])
                        elif lastlu == 17:
                            # Upper frame last packet
                            self.bytes[1] = self.bytes[1] + msg[4:]
                            self.image[1] = ( Image.open(
                                                 io.BytesIO(self.bytes[1])).\
                                                 rotate(90, expand=True) )
                            if int(self.upperVal.get()) == 1:
                                img = ImageTk.PhotoImage(
                                          self.image[1].resize((120,72)) )
                                self.upperlabel.config(image = img)
                                self.upperlabel.image = img  # keep a reference, or Tk loses the image
                                self.lowerlabel.config(image = self.bitmap['Lower'])
                            else:
                                self.upperlabel.config(image = self.bitmap['Upper'])
            except:
                self.msgbox.MsgAppend('Error: Packet analyze error')

    def Connect3DS(self):
        if str(self.General.ConnectButton['relief']) == 'raised':
            self.TID = threading.Thread(target=self.main_procedure,
                                        name='main-procedure', daemon=True)
            self.TID.start()
        else:
            self.ir.return_control()
            self.General.ConnectState(0)
            self.msgbox.MsgAppend('Please wait till this run complete')

    def main_procedure(self):
            # Drop frames left from a previous run, so the wait below
            # really waits for this run's first frame
            self.image[0] = None
            self.image[1] = None
            # Valid the string in entries
            try:
                check(self.General.IPDS.Entry.get())
            except:
                self.msgbox.MsgAppend('Error: Invalid 3DS IP')
                raise Exception('Invalid IP')
            try:
                check(self.General.IPPC.Entry.get())
            except:
                self.msgbox.MsgAppend('Error: Invalid PC IP')
                raise Exception('Invalid IP')
            try:
                int(self.General.Counter.Entry.get())
            except:
                self.msgbox.MsgAppend('Error: Not a number for the counter!')
                raise Exception('Not a number!')
            # Lock down GUI
            self.General.ConnectState(1)
            self.General.ConnectButton.config(state = 'disabled')
            self.msgbox.msgbox.config(bg = 'white')
            # Get IP address and port number
            IPstr = self.General.IPPC.Entry.get()
            self.General.serverIP = IPstr.split(':')[0]
            self.General.serverport = int(IPstr.split(':')[1])
            IPstr = self.General.IPDS.Entry.get()
            self.General.clientIP = IPstr.split(':')[0]
            self.General.start_count = int(self.General.Counter.Entry.get())
            # TCP/IP connection to NTR
            self.msgbox.MsgAppend('Step 1: Build TCP/IP connecton...')
            try:
                self.tcp_socket = socket.create_connection(
                                    (self.General.clientIP, 8000) )
                self.General.tcp_socket = self.tcp_socket
            except:
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.MsgAppend('Cannot build connection')
                raise Exception('Error: Cannot build connection')
            pcip, pcport = self.tcp_socket.getsockname()
            dsip, dsport = self.tcp_socket.getpeername()
            self.msgbox.MsgAppend(f'PC IP:      {pcip}')
            self.msgbox.MsgAppend(f'PC port:    {pcport}')
            self.msgbox.MsgAppend(f'N3DS IP:    {dsip}')
            self.msgbox.MsgAppend(f'N3DS port:  {dsport}')
            # Setup streaming by sending packets
            self.msgbox.MsgAppend('Step 2: Set up streaming...')
            for i in range(2):
                self.tcp_socket.sendall(
                    bytearray.fromhex('7856341200000000000000000000\
                                       0000050100000000000000000000\
                                       0000000000000000000000000000\
                                       0000000000000000000000000000\
                                       0000000000000000000000000000\
                                       0000000000000000000000000000') )
                self.tcp_socket.sendall(
                    bytearray.fromhex('7856341200010000000000008503\
                                       0000050100005000000000001800\
                                       dce5af53411f0000000000000000\
                                       0000000000000000000000000000\
                                       0000000000000000000000000000\
                                       0000000000000000000000000000'
                                       .replace('411f',i2L(self.General.serverport))) )
                time.sleep(0.1)
            # Set up UDP socket on PC
            self.msgbox.MsgAppend( 'Step 3: Listen NTR Packets on port '
                                   f'{self.General.serverport}...' )
            try:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.bind((self.General.serverIP, self.General.serverport))
                self.General.udp_socket = self.udp_socket
            except:
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.MsgAppend('Error: Cannot build connection')
                raise Exception('Cannot build connection')
            self.TIDb = threading.Thread(target=self.background_thread,
                                         name='stream', daemon=True)
            self.TIDb.start()
            # Create a Input Redirection connection
            self.msgbox.MsgAppend('Step 4: Build input redirection server...')
            self.ir = LumaInputServer(self.General.clientIP)
            # Wait until the first complete upper frame arrives (max 30 s);
            # the tab threads crop self.image[1] right away
            for i in range(300):
                if self.image[1] is not None:
                    break
                time.sleep(0.1)
            if self.image[1] is None:
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.MsgAppend('Error: No stream from 3DS')
                raise Exception('No stream from 3DS')
            # Write setting data struct
            currset = self.General.settingGetInd()
            self.General.data[0] = currset
            self.GUI2data(currset)
            self.General.WriteSetting(self.General.data)            
            # Start main procedure
            if int(self.General.Tab.get()) == 0:
                self.msgbox.MsgAppend('Step 5: Start shiny hunting...')
                self.Battle.ir = self.ir
                self.TIDm = threading.Thread(
                            target=self.Battle.main_procedure,
                            name='battle', daemon=True)
            elif int(self.General.Tab.get()) == 1:
                self.msgbox.MsgAppend('Step 5: Start receiving pokemon...')
                self.Recv.ir = self.ir
                self.TIDm = threading.Thread(
                            target=self.Recv.main_procedure,
                            name='recv', daemon=True)
            elif int(self.General.Tab.get()) == 2:
                self.msgbox.MsgAppend('Step 5: Start lottery draw...')
                self.Lotto.ir = self.ir
                self.TIDm = threading.Thread(
                            target=self.Lotto.main_procedure,
                            name='lotto', daemon=True)
            self.TIDm.start()
            self.General.ConnectButton.config(state = 'normal')

    def settingswitch(self, event=None):
        currset = self.General.settingGetInd()
        self.General.setting.selection_clear()
        self.General.data = self.General.LoadSetting()
        self.data2GUI(currset)

    def GUI2data(self,i):
        self.General.GUI2data(i)
        self.Battle.GUI2data(i)
        self.Recv.GUI2data(i)
        self.Lotto.GUI2data(i)

    def data2GUI(self,i):
        self.General.data2GUI(i)
        self.Battle.data2GUI(i)
        self.Recv.data2GUI(i)
        self.Lotto.data2GUI(i)

    def ReturnControl(self):
        # Return control to physical buttons
        try:
            self.ir.return_control()
        except:
            self.msgbox.MsgAppend('Error: Input redirection not setup')

app = ShinyHunterUSUM()
app.mainloop()
