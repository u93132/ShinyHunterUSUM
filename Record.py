import sys, io, time, socket, threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from PIL import Image
from functions import check, i2L, load_bitmaps, combine_images
from boxBase import ToolTip

# Define the application class
class Record:
    def __init__(self, frame, app):

        ########################################################################
        ############################## Initialize ##############################
        ########################################################################

        self.frame   = frame
        self.app     = app         # reads app.General's IPs, shares
        self.General = app.General # the stream images and the display
        self.msgbox  = app.msgbox
        self.image   = app.image
        self.stop = threading.Event()
        self.stop.set()
        self.tcp_socket = None
        self.hunterlock = False   # True from ConnectState(1) to (-1)
        self.auto_running = False
        self.auto_count   = 0
        self._last_saved  = {}
        self._nextn = {}   # cached next file number per (folder, name)
        # own frame-assembly state, separate from the app's stream
        self.bytes = [b'', b'']
        self.frame_curr = -1
        self.index_prev = -1
        # Load images
        self.bitmap = load_bitmaps('image0/Record')

        ########################################################################
        ################################ Objects ###############################
        ########################################################################

        # Save folder, next to the exe by default
        if getattr(sys, 'frozen', False):
            savedir = Path(sys.executable).parent
        else:
            savedir = Path('.').resolve()
        self.framePath = tk.Frame(self.frame)
        self.framePath .grid(row=0, column=0, padx=3, pady=8, sticky='w')
        self.PathLabel = tk.Label(self.framePath, text='Save to: ',
                                  width=7, anchor='w')
        self.PathLabel .pack(padx=0, pady=0, side='left')
        self.PathEntry = tk.Entry(self.framePath, width=20)
        self.PathEntry .pack(padx=0, pady=0, side='left')
        self.PathEntry .insert(0, str(savedir))
        self.BrowseButton = tk.Button(self.framePath, text='...',
                                      command=self.Browse)
        self.BrowseButton .pack(padx=3, pady=0, side='left')
        # Own stream connection plus one-shot / continuous capture
        self.frameBtn = tk.Frame(self.frame)
        self.frameBtn .grid(row=1, column=0, padx=3, pady=4, sticky='w')
        self.ConnectButton = tk.Button(self.frameBtn,
                                       image=self.bitmap['TVoff'],
                                       command=self.Connect)
        self.ConnectButton .pack(padx=3, pady=0, side='left')
        self.SaveButton = tk.Button(self.frameBtn,
                                    image=self.bitmap['camera'],
                                    command=self.SaveShot)
        self.SaveButton .pack(padx=6, pady=0, side='left')
        self.autovar = tk.IntVar()
        self.autobtn = tk.Checkbutton(self.frameBtn, text='Auto',
                                      variable=self.autovar,
                                      command=self.autoswitch)
        self.autobtn .pack(padx=3, pady=0, side='left')
        self.ConnTip = ToolTip(self.ConnectButton, 'Stream is off')
        self.SaveTip = ToolTip(self.SaveButton, 'Save a screenshot')

    ############################################################################
    ################################ Functions #################################
    ############################################################################

    def Browse(self):
        folder = filedialog.askdirectory(
                     initialdir=self.PathEntry.get())
        if folder:
            self.PathEntry.delete(0, 'end')
            self.PathEntry.insert(0, folder)

    def Connect(self):
        if self.stop.is_set():
            if str(self.General.ConnectButton['relief']) == 'sunken':
                self.msgbox.MsgAppend('Error: Disconnect the hunter '
                                      'before recording')
                return
            self.TID = threading.Thread(target=self.connect_procedure,
                                        name='record', daemon=True)
            self.TID.start()
        else:
            self.stop.set()
            self.Disconnected()
            self.msgbox.MsgAppend('Record stopped')

    def TVstate(self):
        # Single authority over the TV button: it is enabled only
        # when the hunter does not own the stream and no burst runs
        if self.hunterlock or self.auto_running:
            self.ConnectButton.config(state='disabled')
        else:
            self.ConnectButton.config(state='normal')

    def HunterState(self, on):
        # The hunter owns the stream: the TV icon mirrors it, locked
        self.hunterlock = on
        if on:
            self.ConnectButton.config(image=self.bitmap['TVon'],
                                      relief='sunken')
            self.ConnTip.set_text('Stream is on')
        else:
            self.ConnectButton.config(image=self.bitmap['TVoff'],
                                      relief='raised')
            self.ConnTip.set_text('Stream is off')
        self.TVstate()

    def Disconnected(self):
        self.StopAuto()
        # Drop the TCP link to NTR as well: a lingering one blocks
        # the next connection attempt (ours or the hunter's)
        if self.tcp_socket is not None:
            try:
                self.tcp_socket.close()
            except OSError:
                pass
            self.tcp_socket = None
        self.ConnectButton.config(image=self.bitmap['TVoff'],
                                  relief='raised')
        self.ConnTip.set_text('Stream is off')
        self.General.RecordLock(False)

    def connect_procedure(self):
        # Read the IPs straight from the General tab - no duplicates
        try:
            IPstr = self.General.IPPC.Entry.get()
            check(IPstr)
            serverIP   = IPstr.split(':')[0]
            serverport = int(IPstr.split(':')[1])
            clientIP   = self.General.IPDS.Entry.get().split(':')[0]
            check(clientIP)
        except (Exception, IndexError):
            self.msgbox.MsgAppend('Error: Invalid IP on the General tab')
            return
        self.stop.clear()
        self.ConnectButton.config(image=self.bitmap['TVon'],
                                  relief='sunken')
        self.ConnTip.set_text('Stream is on')
        self.msgbox.msgbox.config(bg = 'white')
        # The stream owns the UDP port now: lock the hunting UI
        self.General.RecordLock(True)
        # Drop frames left from a previous run
        self.image[0] = None
        self.image[1] = None
        # TCP/IP connection to NTR
        self.msgbox.MsgAppend('Record: Build TCP/IP connection...')
        try:
            self.tcp_socket = socket.create_connection((clientIP, 8000))
        except OSError:
            self.msgbox.MsgAppend('Error: Cannot build connection')
            self.stop.set()
            self.Disconnected()
            return
        # Setup streaming by sending packets
        self.msgbox.MsgAppend('Record: Set up streaming...')
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
                                   .replace('411f', i2L(serverport))) )
            time.sleep(0.1)
        # Set up UDP socket on PC
        self.msgbox.MsgAppend(f'Record: Listen on port {serverport}...')
        try:
            self.udp_socket = socket.socket(socket.AF_INET,
                                            socket.SOCK_DGRAM)
            self.udp_socket.bind((serverIP, serverport))
        except OSError:
            self.msgbox.MsgAppend('Error: Cannot bind the UDP port')
            self.stop.set()
            self.Disconnected()
            return
        self.TIDb = threading.Thread(target=self.stream_thread,
                                     name='record-stream', daemon=True)
        self.TIDb.start()
        self.msgbox.MsgAppend('Record: Streaming, press Save')

    def stream_thread(self):
        # Fetch data from the UDP socket, share the app's image slots
        # and display so the screen previews stay live
        while True:
            if self.stop.is_set():
                # restore the placeholder previews, same behavior as
                # the hunter's stream on disconnect
                self.app.upperlabel.config(image=self.app.bitmap['Upper'])
                self.app.lowerlabel.config(image=self.app.bitmap['Lower'])
                try:
                    self.udp_socket.close()
                except OSError:
                    pass
                break
            try:
                msg, addr = self.udp_socket.recvfrom(2048)
                msg = bytearray(msg)
            except OSError:
                continue
            if len(msg) < 4:
                continue
            frame  = msg[0]
            lastlu = msg[1]
            index  = msg[3]
            try:
                if index == 0:
                    self.frame_curr = frame
                    self.index_prev = 0
                    match lastlu:
                        case 0 | 1:
                            self.bytes[lastlu] = msg[4:]
                else:
                    if ( (frame == self.frame_curr) and
                         (index == self.index_prev + 1) ):
                        self.index_prev = index
                        match lastlu:
                            case 0 | 1:
                                self.bytes[lastlu] += msg[4:]
                            case 16 | 17:
                                s = lastlu - 16
                                self.bytes[s] += msg[4:]
                                self.image[s] = (Image.open(
                                    io.BytesIO(self.bytes[s]))
                                    .rotate(90, expand=True))
                                self.app.show_frame(s)
            except Exception:
                self.msgbox.MsgAppend('Error: Packet analyze error')

    def autoswitch(self):
        # Toggle between one-shot and continuous capture
        self.StopAuto()
        if int(self.autovar.get()) == 1:
            self.SaveButton.config(image=self.bitmap['video'])
            self.SaveTip.set_text('Record the stream')
        else:
            self.SaveButton.config(image=self.bitmap['camera'])
            self.SaveTip.set_text('Save a screenshot')

    def BurstLock(self, on):
        # While the burst runs, only the camera button stays usable
        state = 'disabled' if on else 'normal'
        self.BrowseButton.config(state = state)
        self.PathEntry.config(state = state)
        self.autobtn.config(state = state)
        self.TVstate()

    def StopAuto(self):
        self.SaveButton.config(relief='raised')
        if self.auto_running:
            self.auto_running = False
            self.msgbox.MsgAppend('Auto capture stopped '
                                  f'({self.auto_count} saved)')
        self.BurstLock(False)

    def SelScreens(self):
        # Every ticked screen: up to [0, 1], empty when none
        sel = []
        if int(self.app.lowerVal.get()) == 1:
            sel.append(0)
        if int(self.app.upperVal.get()) == 1:
            sel.append(1)
        return sel

    def SaveShot(self):
        if int(self.autovar.get()) == 0:
            self.SaveOne()
            return
        # Continuous mode: the same button starts and stops the run;
        # a sunken camera means the burst is running
        if self.auto_running:
            self.StopAuto()
        elif not self.SelScreens():
            self.msgbox.MsgAppend('Error: No screen is selected')
        else:
            self.auto_running = True
            self.auto_count   = 0
            self._last_saved  = {}
            self.SaveButton.config(relief='sunken')
            self.BurstLock(True)
            self.msgbox.MsgAppend('Auto capture started')
            self.auto_tick()

    def auto_tick(self):
        # Save every fresh frame of the selected screen (~10/s max)
        if not self.auto_running:
            return
        hunter_on = str(self.General.ConnectButton['relief']) == 'sunken'
        if self.stop.is_set() and not hunter_on:
            # no stream from either side, stop capturing
            self.StopAuto()
            return
        sel = self.SelScreens()
        if not sel:
            self.msgbox.MsgAppend('Error: No screen is selected')
            self.StopAuto()
            return
        if len(sel) == 2:
            # combined mode: a fresh frame on either screen makes a
            # new pair worth saving
            pair = (id(self.image[0]), id(self.image[1]))
            if (self.image[0] is not None and
                    self.image[1] is not None and
                    pair != self._last_saved.get('pair')):
                self._last_saved['pair'] = pair
                self.SaveCombined(quiet=True)
        else:
            s = sel[0]
            img = self.image[s]
            if img is not None and id(img) != self._last_saved.get(s):
                self._last_saved[s] = id(img)
                self.SaveScreen(s, quiet=True)
        self.frame.after(100, self.auto_tick)

    def SaveOne(self, quiet=False):
        # Save the ticked screen at full resolution; with both
        # screens ticked the two frames merge into one picture
        sel = self.SelScreens()
        if not sel:
            self.msgbox.MsgAppend('Error: No screen is selected')
            return
        if len(sel) == 2:
            self.SaveCombined(quiet)
        else:
            self.SaveScreen(sel[0], quiet)

    def SaveScreen(self, s, quiet=False):
        # Save one screen's latest frame
        img = self.image[s]
        if img is None:
            self.msgbox.MsgAppend('Error: No frame received yet')
            return
        self.SaveImage(img, ('Lower', 'Upper')[s], quiet)

    def SaveCombined(self, quiet=False):
        # Save both screens merged side by side
        if self.image[0] is None or self.image[1] is None:
            self.msgbox.MsgAppend('Error: No frame received yet')
            return
        self.SaveImage(combine_images(self.image), 'Combined', quiet)

    def SaveImage(self, img, name, quiet=False):
        # Write an image to the save folder with a running number
        folder = Path(self.PathEntry.get())
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.msgbox.MsgAppend('Error: Cannot use the save folder')
            self.StopAuto()
            return
        key = (str(folder), name)
        n = self._nextn.get(key, 1)
        while (folder / f'{name}_{n:04d}.jpg').is_file():
            n = n + 1
        img.save(folder / f'{name}_{n:04d}.jpg')
        self._nextn[key] = n + 1
        self.auto_count = self.auto_count + 1
        if not quiet:
            self.msgbox.MsgAppend(f'Saved {name}_{n:04d}.jpg '
                                  f'({img.size[0]}x{img.size[1]})')
