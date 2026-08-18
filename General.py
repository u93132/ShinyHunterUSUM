import tkinter as tk
from tkinter import ttk
import time, tempfile, socket, sys, msvcrt
from dataclasses import dataclass, field
from PIL import Image
from datetime import datetime
from functions import *
from boxBase import *

@dataclass(slots=True)
class Setting:
    # One settings slot; the file keys stay unchanged ('3dsip' on
    # disk maps to the dsip attribute)
    pcip:    str = ''
    dsip:    str = ''
    count:   int = 1
    currtab: int = 0
    move:    int = 0
    aura:    int = 0
    recv:    int = 0
    loto:    list = field(default_factory=lambda: [1, 2])
    # Record tab: save folder ('' = default), shot mode, Auto
    recpath:  str = ''
    shotmode: int = 0
    recauto:  int = 0

def lock_slot(folder, num):
    # Try to lock settings slot `num`. Returns the open lock handle,
    # or None when another running instance owns that slot.
    # The handle must stay open for as long as the slot is in use;
    # Windows releases the lock automatically when the process exits,
    # so a crash can never leave a slot permanently stuck
    f = open(folder / f'USUMShinyHunter-{num}.lock', 'a')
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f
    except OSError:
        f.close()
        return None

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
        self.clientIP    = '192.168.137.50'
        self.tcp_socket  = None    # pre assign the NTR tcp object
        self.udp_socket  = None    # pre assign the NTR udp object
        self.RecordHook = None     # set by the GUI once Record exists
        self.start_count = 1
        # Load images
        self.bitmap = load_bitmaps(f'image0/{self.tabname}')
        # Setup the screenshot folder:
        # next to the exe when frozen, into ./pic in dev
        if getattr(sys, 'frozen', False):
            self.shotpath = Path(sys.executable).parent
        else:
            self.shotpath = Path('pic')
            self.shotpath.mkdir(exist_ok=True)

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
                                          '', '', [0, 18, 0])
        self.IPPC      .Label2.pack(padx=0, pady=0, side='left')
        self.IPPC      .Entry.insert(0,'192.168.137.1:8001')
        # Objects for N3DS IP
        self.frameIPDS = tk.Frame(self.frameAA)
        self.frameIPDS .grid(row=1, column=0, padx=3, pady=8)
        self.labelIPDS = tk.Label(self.frameIPDS, text = '3DS IP: ', anchor='w')
        self.labelIPDS .config(width = 5)
        self.labelIPDS .pack(padx=0, pady=0, side='left', fill='both')
        self.IPDS      = InputBox(self.frameIPDS, 0,
                                          '', '', [0, 18, 0])
        self.IPDS      .Label2.pack(padx=0, pady=0, side='left')
        self.IPDS      .Entry.insert(0,'192.168.137.50')
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
        self.ResetButton   = tk.Button(self.Counter.frame,
                                       image=self.bitmap['return'],
                                       command=self.CounterReset)
        self.ResetButton   .pack(padx=0, pady=0, side='right')
        ToolTip(self.ConnectButton, 'Connect to 3DS')
        ToolTip(self.ResetButton,   'Reset the counter')
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
        # Settings: one numbered file per Set (Set #k <-> file -k.txt).
        # Lock detection happens at startup and on Connect only; the
        # lock handle must stay referenced or GC would release it
        self.settingfolder = Path(tempfile.gettempdir())
        self.settinglist = ['Set #'+str(i+1) for i in range(12)]
        self.setting     = ttk.Combobox(self.frame, state = 'readonly')
        self.setting     .grid(row=1, column=1, padx=5, pady=8, sticky='e')
        self.setting     .config(width = 6, values = self.settinglist)

        self.MigrateSetting()
        self.data = self.LoadSetting()
        # Startup lock detection: start on Set #1 and advance to the
        # first slot no other running instance holds (#1 -> #2 -> ...)
        self.lockedslot = None
        self._settinglock = None
        for k in range(1, 13):
            self._settinglock = lock_slot(self.settingfolder, k)
            if self._settinglock is not None:
                self.lockedslot = k
                break
            self.msgbox.MsgAppend(f'Error: Setting #{k} locked by '
                                  'another instance')
        if self.lockedslot is None:
            self.msgbox.MsgAppend('Error: All settings locked, '
                                  'nothing will be saved')
        elif self.lockedslot > 1:
            self.msgbox.MsgAppend(f'Using Set #{self.lockedslot}')
            
    ############################################################################
    ################################ Functions #################################
    ############################################################################

    def settingGetInd(self):
        return self.settinglist.index(self.setting.get())

    def CounterReset(self):
        # Reset the counter to its initial value and save the setting
        self.start_count = 1
        self.Counter.Entry.delete(0,'end')
        self.Counter.Entry.insert(0,'1')
        self.GUI2data(self.settingGetInd())
        self.WriteSetting(self.data)

    def CounterPlusOne(self):
        # Update the counter and plus one; our slot is locked, so the
        # in-memory data is authoritative - no need to reload the files
        self.start_count = self.start_count + 1
        self.Counter.Entry.config(state = 'normal')
        self.Counter.Entry.delete(0,'end')
        self.Counter.Entry.insert(0,str(self.start_count))
        self.GUI2data(self.settingGetInd())
        if str(self.ConnectButton['relief']) == 'sunken':
            self.Counter.Entry.config(state = 'disabled')
        self.WriteSetting(self.data)
        

    def ConnectState(self, i):
        # i =-1: recover the connect/reset button
        # i = 0: disable the connect/reset button, every thing recovered
        # i = 1: lock down everything
        
        match i:
            case 0:
                self.ConnectButton.config(relief = 'raised')
                self.ConnectButton.config(state = 'disabled')
                self.IPDS.Entry.config(state = 'normal')
                self.IPPC.Entry.config(state = 'normal')
                self.Counter.Entry.config(state = 'normal')
                self.setting.config(state = 'readonly')
                # Write setting data struct
                currset = self.settingGetInd()
                self.GUI2data(currset)
                self.WriteSetting(self.data)
                for j in range(len(self.TabButton)):
                    self.TabButton[j].config(state = 'normal')
                    self.nb.tab(j+1, state='normal')
                # Close the UDP socket if this run ever opened one;
                # early failures (the TCP step) have nothing to close
                if self.udp_socket is not None:
                    try:
                        self.udp_socket.shutdown(socket.SHUT_RDWR)
                        self.udp_socket.close()
                    except OSError:
                        pass  # already closed by the GUI thread
                    self.udp_socket = None
                # Drop the TCP link to NTR as well: a lingering one
                # blocks the next connection attempt
                if self.tcp_socket is not None:
                    try:
                        self.tcp_socket.close()
                    except OSError:
                        pass
                    self.tcp_socket = None
            case 1:
                self.ConnectButton.config(relief = 'sunken')
                self.ConnectButton.config(state = 'disabled')
                self.ResetButton.config(state = 'disabled')
                if self.RecordHook is not None:
                    self.RecordHook(True)
                self.IPDS.Entry.config(state = 'disabled')
                self.IPPC.Entry.config(state = 'disabled')
                self.Counter.Entry.config(state = 'disabled')
                self.setting.config(state = 'disabled')
                for j in range(len(self.TabButton)):
                    self.TabButton[j].config(state = 'disabled')
                    self.nb.tab(j+1, state='disabled')
            case -1:
                self.ConnectButton.config(state = 'normal')
                self.ResetButton.config(state = 'normal')
                if self.RecordHook is not None:
                    self.RecordHook(False)

    def RecordLock(self, on):
        # While the Record stream owns the port, only tab switching
        # is locked; everything else stays as it is
        state = 'disabled' if on else 'normal'
        for j in range(len(self.TabButton) + 1):
            self.nb.tab(j, state = state)

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
        self.data[i].pcip    = self.IPPC.Entry.get()
        self.data[i].dsip    = self.IPDS.Entry.get()
        self.data[i].count   = int(self.Counter.Entry.get())
        self.data[i].currtab = int(self.Tab.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.IPPC.Entry.delete(0,'end')
        self.IPPC.Entry.insert(0,self.data[i].pcip)
        self.IPDS.Entry.delete(0,'end')
        self.IPDS.Entry.insert(0,self.data[i].dsip)
        self.Counter.Entry.delete(0,'end')
        self.Counter.Entry.insert(0,str(self.data[i].count))
        self.Tab.set(int(self.data[i].currtab))

    def DefaultData(self):
        # Fresh data struct: 12 default slots
        return [Setting() for i in range(12)]

    def ParseFields(self, lines, slot):
        # Fetch key=value lines into one Setting
        for line in lines:
            temp = line.split('=')
            if len(temp) < 2:
                continue
            match temp[0]:
                case 'pcip':
                    slot.pcip = temp[1]
                case '3dsip':
                    slot.dsip = temp[1]
                case 'loto':
                    try:
                        slot.loto = [int(k) for k in temp[1].split(',')]
                    except ValueError:
                        slot.loto = []
                case 'recpath':
                    # split only on the first '=' so a folder name
                    # containing '=' survives the round trip
                    slot.recpath = line.split('=', 1)[1]
                case ('count' | 'currtab' | 'move' | 'aura' | 'recv'
                      | 'shotmode' | 'recauto'):
                    setattr(slot, temp[0], int(temp[1]))

    def LoadSetting(self):
        # Read every slot file that exists; missing slots stay default
        data = self.DefaultData()
        for i in range(12):
            path = self.settingfolder / f'USUMShinyHunter-{i+1}.txt'
            if path.is_file():
                with open(path, 'r') as f:
                    self.ParseFields(f.read().split('\n'), data[i])
        return data

    def WriteSlotFile(self, i, d):
        # Write one Setting to its numbered file (i is 0-based)
        with open(self.settingfolder / f'USUMShinyHunter-{i+1}.txt',
                  'w') as f:
            f.write(f'pcip={d.pcip}\n')
            f.write(f'3dsip={d.dsip}\n')
            f.write(f'count={d.count}\n')
            f.write(f'currtab={d.currtab}\n')
            f.write(f'move={d.move}\n')
            f.write(f'aura={d.aura}\n')
            f.write(f'recv={d.recv}\n')
            f.write('loto=' + ','.join(str(k) for k in d.loto) + '\n')
            f.write(f'recpath={d.recpath}\n')
            f.write(f'shotmode={d.shotmode}\n')
            f.write(f'recauto={d.recauto}\n')

    def WriteSetting(self, data):
        # Write the selected slot to its own file; the other slots
        # belong to their own files and are never touched here
        i = self.settingGetInd()
        self.WriteSlotFile(i, data[i])

    def AcquireSlot(self):
        # Connect-time lock detection: own the selected slot's lock
        # before hunting starts; keep the old lock on failure
        num = self.settingGetInd() + 1
        if num == self.lockedslot:
            return True
        newlock = lock_slot(self.settingfolder, num)
        if newlock is None:
            self.msgbox.MsgAppend(f'Error: Setting #{num} locked by '
                                  'another instance')
            return False
        if self._settinglock is not None:
            self._settinglock.close()   # closing releases the old lock
        self._settinglock = newlock
        self.lockedslot = num
        return True

    def OldFormat(self, path):
        # True when the file exists and still uses the old 12-section
        # format (its first line is the numeric header)
        if not path.is_file():
            return False
        with open(path, 'r') as f:
            return f.readline().strip().isdigit()

    def MigrateSetting(self):
        # Split the old 12-section settings file into the per-slot
        # files (old Set #k -> file -k.txt), keeping counters.
        # Runs only on the first launch after the upgrade: any
        # existing per-slot file means migration already happened,
        # so a slot file deleted later comes back as defaults instead
        # of being resurrected from the old snapshot
        for i in range(12):
            path = self.settingfolder / f'USUMShinyHunter-{i+1}.txt'
            if path.is_file() and not self.OldFormat(path):
                return
        for name in ('USUMShinyHunter-1.txt', 'USUMShinyHunter.txt'):
            old = self.settingfolder / name
            if not old.is_file():
                continue
            with open(old, 'r') as f:
                lines = f.read().split('\n')
            if not (lines and lines[0].strip().isdigit()):
                continue   # already the per-slot format
            data = self.DefaultData()
            ind = -1
            for line in lines[1:]:
                if line.startswith('#'):
                    ind = ind + 1
                elif 0 <= ind < 12:
                    self.ParseFields([line], data[ind])
            # The old file is kept untouched so an old version of the
            # program can still read it; slot files are created when
            # missing, and numbered files still in the old format
            # (interim versions) are rewritten in place
            for i in range(12):
                path = self.settingfolder / f'USUMShinyHunter-{i+1}.txt'
                if not path.is_file() or self.OldFormat(path):
                    self.WriteSlotFile(i, data[i])
        
        
    
