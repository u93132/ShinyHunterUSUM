import tkinter as tk
from tkinter import ttk
import time, tempfile, os, socket
from PIL import Image
from datetime import datetime
from functions import *
from boxBase import *

import win32con
import win32.win32gui as win32gui
import win32.win32process as win32process
import win32.win32api as win32api

# Define the application class
class General:
    def __init__(self, nb, msgbox):
        
        ########################################################################
        ############################## Initialize ##############################
        ########################################################################

        self.nb          = nb
        self.tabname     = 'General' 
        self.frame       = nb.frame[nb.framename.index(self.tabname)] 
        self.framename   = nb.framename
        self.msgbox      = msgbox  # message box
        self.serverIP    = '192.168.137.1'
        self.serverport  = 8001
        self.clientIP    = '192.168.137.60'
        self.tcp_socket  = None    # pre assign the NTR tcp object
        self.udp_socket  = None    # pre assign the NTR udp object
        self.start_count = 1
        # Load images
        self.picpath = './image0/' + self.tabname + '/'
        self.bitmap = {}
        for i in os.listdir(resource_path(self.picpath)):
            temp = i.split('.')
            if len(temp) > 1:
                if not temp[1] == 'ico':
                    if temp[1] == 'gif':
                        self.bitmap[temp[0]] = tk.PhotoImage(
                                file=(resource_path(self.picpath+ i)) )
                    else:
                        self.bitmap[temp[0]] = ImageTk.PhotoImage(
                            Image.open(resource_path(self.picpath+ i)) )
        # Get EXE folder
        hwnd = win32gui.FindWindowEx(0,None,None,'Shiny Hunter USUM')
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        hndl = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION |
                                    win32con.PROCESS_VM_READ, 0, pid)
        self.path = win32process.GetModuleFileNameEx(hndl, 0)
        self.shotpath, self.filename = os.path.split(self.path)
        # Setup the screenshot folder
        if self.filename == 'pythonw.exe':
            self.shotpath = './pic'

        ########################################################################
        ################################ Objects ###############################
        ########################################################################

        self.frameAA = tk.Frame(self.frame)
        self.frameAA .grid(row=0, column=0, padx=0, pady=0, sticky='nsw')
        # Objects for Computer IP
        self.frameIPPC = tk.Frame(self.frameAA)
        self.frameIPPC .grid(row=0, column=0, padx=3, pady=8)
        self.labelIPPC = tk.Label(self.frameIPPC, text = 'PC IP: ', anchor='w')
        self.labelIPPC .config(width = 5)
        self.labelIPPC .pack(padx=0, pady=0, side='left', fill='both')
        self.IPPC      = InputBox(self.frameIPPC, 0,
                                          '192.168.', '', [7, 11, 0])
        self.IPPC      .Label2.pack(padx=0, pady=0, side='left')
        #self.IPPC      .Entry.insert(0,'137.1:8001')
        # Objects for N3DS IP
        self.frameIPDS = tk.Frame(self.frameAA)
        self.frameIPDS .grid(row=1, column=0, padx=3, pady=8)
        self.labelIPDS = tk.Label(self.frameIPDS, text = '3DS IP: ', anchor='w')
        self.labelIPDS .config(width = 5)
        self.labelIPDS .pack(padx=0, pady=0, side='left', fill='both')
        self.IPDS      = InputBox(self.frameIPDS, 0,
                                          '192.168.', '', [7, 11, 0])
        self.IPDS      .Label2.pack(padx=0, pady=0, side='left')
        #self.IPDS      .Entry.insert(0,'137.60')
        # Objects for Counter
        self.frameCounter = tk.Frame(self.frame)
        self.frameCounter .grid(row=1, column=0, padx=3, pady=8, sticky='ew')
        self.Counter      = InputBox(self.frameCounter, 0,
                                             'Counter: ', '', [8, 5, 0])
        self.Counter      .Label2.pack(padx=0, pady=0, side='left')
        self.Counter      .Entry.insert(0,'1')
        # Objects for Connect and return control button
        self.ConnectButton = tk.Button(self.Counter.frame,
                                       image=self.bitmap['connect'])
        self.ConnectButton .pack(padx=0, pady=0, side='right')
        self.ReturnButton  = tk.Button(self.Counter.frame,
                                       image=self.bitmap['return'])
        #self.ReturnButton .pack(padx=0, pady=0, side='right')
        # Objects for Tab Control
        self.frameTabCon = tk.Frame(self.frame)
        self.frameTabCon .grid(row=0, column=1, padx=5, pady=0, sticky='nse')
        self.TabButton   = [None for i in range(len(self.framename)-1)]

        self.Tab = tk.IntVar()
        if len(self.TabButton) == 1:
            self.Tab.set(-1)
        else:
            self.Tab.set(0)
            
        for i in range(len(self.TabButton)):
            self.TabButton[i]=tk.Radiobutton(self.frameTabCon,
                                             variable=self.Tab, value=i)
            self.TabButton[i].config(width=5, anchor='w')
            self.TabButton[i].grid(row=i, column=0, padx=0, pady=0, sticky='w')
            self.TabButton[i].config(text=self.framename[i+1])
        # Settings
        self.settingpath = tempfile.gettempdir() + '/USUMShinyHunter.txt'
        self.settinglist = ['Set #'+str(i+1) for i in range(12)]
        self.setting     = ttk.Combobox(self.frame, state = 'readonly')
        self.setting     .grid(row=1, column=1, padx=5, pady=8, sticky='e')
        self.setting     .config(width = 6, values = self.settinglist)

        if not os.path.isfile(self.settingpath):
            self.CreateSetting()
        self.data = self.LoadSetting()
            
    ############################################################################
    ################################ Functions #################################
    ############################################################################

    def settingGetInd(self):
        return self.settinglist.index(self.setting.get())

    def CounterPlusOne(self):
        # Update the counter and plus one
        self.data = self.LoadSetting()
        self.start_count = self.start_count + 1
        self.Counter.Entry.config(state = 'normal')
        self.Counter.Entry.delete(0,'end')
        self.Counter.Entry.insert(0,str(self.start_count))
        self.GUI2data(self.settingGetInd())
        if str(self.ConnectButton['relief']) == 'sunken':
            self.Counter.Entry.config(state = 'disable')
        self.WriteSetting(self.data)
        

    def ConnectState(self, i):
        # i =-1: recover the recover/return button
        # i = 0: disable the connect/return button, every thing recovered
        # i = 1: lock down everything
        
        if i == 0:
            self.ConnectButton.config(relief = 'raised')
            self.ConnectButton.config(state = 'disable')
            self.IPDS.Entry.config(state = 'normal')
            self.IPPC.Entry.config(state = 'normal')
            self.Counter.Entry.config(state = 'normal')
            self.setting.config(state = 'readonly')
            # Write setting data struct
            currset = self.settingGetInd()
            self.data[0] = currset
            self.GUI2data(currset)
            self.WriteSetting(self.data) 
            for j in range(len(self.TabButton)):
                self.TabButton[j].config(state = 'normal')
                self.nb.tab(j+1, state='normal')
            try:
                self.udp_socket.shutdown(socket.SHUT_RDWR)
                self.udp_socket.close()
            except:
                self.msgbox.MsgAppend('Error: Cannot close the socket')
        elif i == 1:
            self.ConnectButton.config(relief = 'sunken')
            self.ConnectButton.config(state = 'disable')
            self.ReturnButton.config(state = 'disable')
            self.IPDS.Entry.config(state = 'disable')
            self.IPPC.Entry.config(state = 'disable')
            self.Counter.Entry.config(state = 'disable')
            self.setting.config(state = 'disable')
            for j in range(len(self.TabButton)):
                self.TabButton[j].config(state = 'disable')
                self.nb.tab(j+1, state='disable')
        elif i == -1:
            self.ConnectButton.config(state = 'normal')
            self.ReturnButton.config(state = 'normal')

    def test3DS(self):
        # Test if 3DS is still alive
        self.tcp_socket.send(
            bytearray.fromhex('7856341200000000000000000000\
                               0000050100000000000000000000\
                               0000000000000000000000000000\
                               0000000000000000000000000000\
                               0000000000000000000000000000\
                               0000000000000000000000000000'))

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.data[1][i]['pcip']    = self.IPPC.Entry.get()
        self.data[1][i]['3dsip']   = self.IPDS.Entry.get()
        self.data[1][i]['count']   = int(self.Counter.Entry.get())
        self.data[1][i]['currtab'] = int(self.Tab.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.IPPC.Entry.delete(0,'end')
        self.IPPC.Entry.insert(0,self.data[1][i]['pcip'])
        self.IPDS.Entry.delete(0,'end')
        self.IPDS.Entry.insert(0,self.data[1][i]['3dsip'])
        self.Counter.Entry.delete(0,'end')
        self.Counter.Entry.insert(0,str(self.data[1][i]['count']))
        self.Tab.set(int(self.data[1][i]['currtab']))

    def CreateSetting(self):
        # Create a new setting file to temp folder
        with open(self.settingpath, 'w') as f:
            f.write('0\n')
            for i in range(12):
                f.write('#' + str(i+1)+'\n')
                f.write('pcip=\n')
                f.write('3dsip=\n')
                f.write('count=1\n')
                f.write('currtab=0\n')
                f.write('move=0\n')
                f.write('aura=0\n')
                f.write('recv=0\n')
                f.write('loto=1,2\n')

    def LoadSetting(self):
        # Initialize data struct in Python
        data = [0, []]
        for i in range(12):
            x = {'pcip':'', '3dsip':'', 'count':1, 'currtab':0, 'move':0, 'aura':0,
                 'recv':0, 'loto':[1,2]}
            data[1].append(x)
        # Read the setting file
        with open(self.settingpath, 'r') as f:
            lines = f.read().split('\n')
        # Fetch data to the struct
        data[0] = int(lines[0]) # Latest saved setting file
        ind = -1                # current read setting file
        for i in range(1,len(lines)):
            temp = lines[i].split('=')
            if len(temp) == 1:
                ind = ind + 1
            else:
                if temp[0] == 'loto':
                    try:
                        data[1][ind]['loto'] = [int(k) for k in temp[1].split(',')]
                    except:
                        data[1][ind]['loto'] = []
                elif (temp[0] == 'pcip') or (temp[0] == '3dsip'):
                    data[1][ind][temp[0]] = temp[1]
                else:
                    data[1][ind][temp[0]] = int(temp[1])
        return data

    def WriteSetting(self,data):
        # Write data struct to setting file
        with open(self.settingpath, 'w') as f:
            f.write(str(data[0])+'\n')
            for i in range(12):
                f.write('#' + str(i+1)+'\n')
                f.write('pcip='   + data[1][i]['pcip']                +'\n')
                f.write('3dsip='  + data[1][i]['3dsip']               +'\n')
                f.write('count='  + str(data[1][i]['count'])          +'\n')
                f.write('currtab='+ str(data[1][i]['currtab'])        +'\n')
                f.write('move='   + str(data[1][i]['move'])           +'\n')
                f.write('aura='   + str(data[1][i]['aura'])           +'\n')
                f.write('recv='   + str(data[1][i]['recv'])           +'\n')
                s = ''.join([str(i)+',' for i in data[1][i]['loto']])[:-1]
                f.write('loto='   + s +'\n')
        
        
    
