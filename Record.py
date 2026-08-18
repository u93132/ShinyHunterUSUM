import sys, io, time, socket, threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from PIL import Image
from functions import (check, i2L, load_bitmaps, combine_images,
                       resource_path, write_avi, write_gif)
from boxBase import ToolTip

# Screen hole positions inside the N3DS console template: the holes
# are exactly native resolution, so frames paste in 1:1
N3DS_BOX = {0: (139, 362), 1: (99, 50)}      # lower, upper
N3DS_SIZE = {0: (320, 240), 1: (400, 240)}
# Video length caps in seconds: a manual recording stops itself at
# VIDEO_CAP; AFK mode keeps the newest AFK_CAP of each hunt round so
# a frozen game can never grow the buffer without bound
VIDEO_CAP = 60.0
AFK_CAP   = 200.0

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
        self.runmode    = None    # None / 'burst' / 'video' / 'afk'
        self.auto_count = 0
        self._last_saved = {}
        self._nextn = {}   # cached next file number per (folder, name)
        self.recbuf  = []  # buffered (time, jpeg bytes) video frames
        self.rec_sel = []  # screens fixed for the whole run
        self.recHunter = False  # buffer fed by the hunter's stream
        self.rec_skip  = False  # armed mid-round: wait for the next
        # own frame-assembly state, separate from the app's stream
        self.bytes = [b'', b'']
        self.frame_curr = -1
        self.index_prev = -1
        # Load images
        self.bitmap = load_bitmaps('image0/Record')
        self.n3ds = tuple(
            Image.open(resource_path(
                f'image0/Record/N3DSXL{c}.png')).convert('RGBA')
            for c in ('Red', 'Blue'))
        # Shot forms: plain picture / red console / blue console
        self.shotmode = 0
        self.modeicon = ('image', 'redconsole', 'blueconsole')
        self.modetip  = ('Picture only', 'Red console frame',
                         'Blue console frame')
        # Capture modes: one shot / burst / video / one video a round
        self.capmode = 0
        self.capicon = ('camera', 'auto', 'video', 'afk')
        self.captip  = ('One screenshot',
                        'Burst: every frame to a file',
                        f'Video, {VIDEO_CAP:.0f} s max',
                        'One video per hunt round, '
                        f'last {AFK_CAP:.0f} s')
        # Video output formats: MJPEG AVI or animated GIF
        self.vidfmt  = 0
        self.fmticon = ('aviicon', 'gificon')
        self.fmttip  = ('Save videos as AVI', 'Save videos as GIF')

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
        self.ConnectButton .pack(padx=(3, 0), pady=0, side='left')
        # Shot form: each click cycles picture-only / red / blue
        self.ModeButton = tk.Button(self.frameBtn,
                                    image=self.bitmap['image'],
                                    command=self.ModeSwitch)
        self.ModeButton .pack(padx=(5, 0), pady=0, side='left')
        # Capture mode: one shot / burst / video / AFK per round
        self.CapButton = tk.Button(self.frameBtn,
                                   image=self.icon('camera'),
                                   command=self.CapSwitch)
        self.CapButton .pack(padx=0, pady=0, side='left')
        # Video format: AVI or GIF, only alive in the video modes
        self.FmtButton = tk.Button(self.frameBtn,
                                   image=self.icon('aviicon'),
                                   command=self.FmtSwitch)
        self.FmtButton .pack(padx=0, pady=0, side='left')
        # Run button: fires or stops the selected capture
        self.SaveButton = tk.Button(self.frameBtn,
                                    image=self.icon('run'),
                                    command=self.SaveShot)
        self.SaveButton .pack(padx=(5, 0), pady=0, side='left')
        self.ModeTip = ToolTip(self.ModeButton, self.modetip[0])
        self.CapTip  = ToolTip(self.CapButton, self.captip[0])
        self.FmtTip  = ToolTip(self.FmtButton, self.fmttip[0])
        self.ConnTip = ToolTip(self.ConnectButton, 'Stream is off')
        self.SaveTip = ToolTip(self.SaveButton, 'Run the capture')
        # AFK only: keep just the round that found the shiny
        self.shinyvar = tk.IntVar()
        self.shinyvar.set(1)
        self.shinybtn = tk.Checkbutton(self.frame,
                                       text='Only shiny run',
                                       variable=self.shinyvar)
        self.shinybtn .grid(row=2, column=0, padx=6, pady=0,
                            sticky='w')
        ToolTip(self.shinybtn,
                'Keep only the round that found the shiny')
        self.ShinyState()
        self.FmtState()

    ############################################################################
    ################################ Functions #################################
    ############################################################################

    def icon(self, name):
        # Fall back to the camera icon until the gif gets drawn
        return self.bitmap.get(name, self.bitmap['camera'])

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
        # when the hunter does not own the stream and no capture runs
        if self.hunterlock or self.runmode is not None:
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
        self.StopRun()
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

    def ModeShow(self):
        # Reflect the current shot mode on the button icon
        self.ModeButton.config(
            image=self.bitmap[self.modeicon[self.shotmode]])
        self.ModeTip.set_text(self.modetip[self.shotmode])

    def ModeSwitch(self):
        # Cycle the shot form: picture / red / blue console
        self.shotmode = (self.shotmode + 1) % 3
        self.ModeShow()

    def ShinyState(self):
        # The only-shiny switch matters only in AFK mode and is
        # frozen while a capture runs
        on = self.capmode == 3 and self.runmode is None
        self.shinybtn.config(state='normal' if on else 'disabled')

    def FmtState(self):
        # The format button matters only in the video modes and is
        # frozen while a capture runs
        on = self.capmode >= 2 and self.runmode is None
        self.FmtButton.config(state='normal' if on else 'disabled')

    def FmtShow(self):
        # Reflect the current video format on the button icon
        self.FmtButton.config(
            image=self.icon(self.fmticon[self.vidfmt]))
        self.FmtTip.set_text(self.fmttip[self.vidfmt])

    def FmtSwitch(self):
        # Toggle the video output format: AVI / GIF
        self.vidfmt = (self.vidfmt + 1) % 2
        self.FmtShow()

    def CapShow(self):
        # Reflect the current capture mode on the button icon
        self.CapButton.config(
            image=self.icon(self.capicon[self.capmode]))
        self.CapTip.set_text(self.captip[self.capmode])
        self.ShinyState()
        self.FmtState()

    def CapSwitch(self):
        # Cycle the capture mode: shot / burst / video / AFK
        self.capmode = (self.capmode + 1) % 4
        self.CapShow()

    def BurstLock(self, on):
        # While a capture runs, only the run button stays usable
        state = 'disabled' if on else 'normal'
        self.BrowseButton.config(state = state)
        self.PathEntry.config(state = state)
        self.ModeButton.config(state = state)
        self.CapButton.config(state = state)
        self.TVstate()
        self.ShinyState()
        self.FmtState()

    def StopRun(self):
        # End whatever capture is running; a video saves its frames
        mode, self.runmode = self.runmode, None
        self.SaveButton.config(relief='raised')
        match mode:
            case 'burst':
                self.msgbox.MsgAppend('Auto capture stopped '
                                      f'({self.auto_count} saved)')
            case 'video':
                self.SaveVideo(self.recbuf, 'Video')
                self.recbuf = []
            case 'afk':
                self.recbuf = []
                self.msgbox.MsgAppend('AFK recording disarmed')
        self.BurstLock(False)

    def StreamOn(self):
        # A stream is running: ours or the hunter's
        if not self.stop.is_set():
            return True
        return str(self.General.ConnectButton['relief']) == 'sunken'

    def SelScreens(self):
        # Every ticked screen: up to [0, 1], empty when none
        sel = []
        if int(self.app.lowerVal.get()) == 1:
            sel.append(0)
        if int(self.app.upperVal.get()) == 1:
            sel.append(1)
        return sel

    def SaveShot(self):
        # The run button: fire the capture, or stop the running one.
        # AFK mode may arm before any stream exists - it waits for
        # the hunter to start streaming
        if self.runmode is not None:
            self.StopRun()
            return
        if self.capmode != 3 and not self.StreamOn():
            self.msgbox.MsgAppend('Error: No active stream')
            return
        if self.capmode == 0:
            self.SaveOne()
        else:
            self.StartRun(('burst', 'video', 'afk')[self.capmode - 1])

    def StartRun(self, mode):
        # Begin a continuous capture; the screen pick is frozen for
        # the whole run so every video frame keeps the same size
        sel = self.SelScreens()
        if not sel:
            self.msgbox.MsgAppend('Error: No screen is selected')
            return
        self.runmode = mode
        self.rec_sel = sel
        self.auto_count  = 0
        self._last_saved = {}
        self.recbuf = []
        self.rec_t0 = None
        self.recHunter = False
        # Arming while the hunter is already mid-round: that round
        # is only half captured, so recording counts from the next
        self.rec_skip = mode == 'afk' and self.hunterlock
        self.SaveButton.config(relief='sunken')
        self.BurstLock(True)
        match mode:
            case 'burst':
                self.msgbox.MsgAppend('Auto capture started')
            case 'video':
                self.msgbox.MsgAppend('Recording '
                                      f'({VIDEO_CAP:.0f} s max)...')
            case 'afk':
                self.msgbox.MsgAppend('AFK recording armed')
        self.run_tick()

    def FreshFrame(self):
        # True once per new frame (or pair) of the running screens
        if any(self.image[s] is None for s in self.rec_sel):
            return False
        key = tuple(id(self.image[s]) for s in self.rec_sel)
        if key == self._last_saved.get('key'):
            return False
        self._last_saved['key'] = key
        return True

    def run_tick(self):
        # One heartbeat of a continuous capture (~10/s max)
        if self.runmode is None:
            return
        if not self.StreamOn():
            if self.runmode != 'afk':
                self.StopRun()
                return
            # AFK: the hunter's stream ending means the hunt is
            # over. Its last round - the shiny - never got a
            # RoundHook, so flush it, then pop the run button in
            # step with the hunter's Connect. An arm that has not
            # seen the hunter yet just keeps waiting for it
            if self.recHunter:
                if self.recbuf:
                    self.RoundFlush(self.General.start_count)
                self.StopRun()
                return
            self.recbuf = []
        elif self.FreshFrame():
            match self.runmode:
                case 'burst':
                    shot = self.ComposeShot(self.rec_sel)
                    if shot is not None:
                        self.SaveImage(*shot, quiet=True)
                case 'video' | 'afk':
                    if self.BufferFrame() and self.runmode == 'video':
                        t0, t1 = self.recbuf[0][0], self.recbuf[-1][0]
                        if t1 - t0 >= VIDEO_CAP:
                            self.StopRun()   # assembles and saves
                            return
        self.frame.after(100, self.run_tick)

    def BufferFrame(self):
        # Compose the current frame and buffer it as JPEG bytes;
        # AFK mode keeps only the newest AFK_CAP seconds
        shot = self.ComposeShot(self.rec_sel)
        if shot is None:
            return False
        img = shot[0]
        if img.mode != 'RGB':
            # JPEG frames carry no alpha: flatten onto white
            base = Image.new('RGB', img.size, 'white')
            base.paste(img, mask=img.getchannel('A'))
            img = base
        buf = io.BytesIO()
        img.save(buf, 'JPEG')
        t = time.time()
        self.recbuf.append((t, buf.getvalue()))
        self.recHunter = self.hunterlock
        if self.runmode == 'afk':
            while t - self.recbuf[0][0] > AFK_CAP:
                self.recbuf.pop(0)
        return True

    def SaveOne(self, quiet=False):
        # Save the composed shot of the ticked screens
        sel = self.SelScreens()
        if not sel:
            self.msgbox.MsgAppend('Error: No screen is selected')
            return
        shot = self.ComposeShot(sel)
        if shot is not None:
            self.SaveImage(*shot, quiet=quiet)

    def ComposeShot(self, sel):
        # Build one picture from the selected screens in the current
        # shot form. Returns (image, name, extension), or None when
        # no frame has arrived yet. Console forms paste the ticked
        # screens into the template and black out the other hole
        for s in sel:
            if self.image[s] is None:
                self.msgbox.MsgAppend('Error: No frame received yet')
                return None
        if self.shotmode:
            console = self.n3ds[self.shotmode - 1]
            canvas = Image.new('RGBA', console.size, (0, 0, 0, 0))
            for s in (0, 1):
                if s in sel:
                    canvas.paste(self.image[s].convert('RGBA'),
                                 N3DS_BOX[s])
                else:
                    canvas.paste(Image.new('RGBA', N3DS_SIZE[s],
                                           (0, 0, 0, 255)),
                                 N3DS_BOX[s])
            return (Image.alpha_composite(canvas, console),
                    ('N3DSRed', 'N3DSBlue')[self.shotmode - 1], 'png')
        if len(sel) == 2:
            return (combine_images(self.image), 'Combined', 'jpg')
        return (self.image[sel[0]], ('Lower', 'Upper')[sel[0]], 'jpg')

    def NextFile(self, name, ext):
        # Reserve the next numbered path in the save folder. The
        # instance's Set number keeps parallel instances from
        # overwriting each other's files (0 = no slot acquired)
        folder = Path(self.PathEntry.get())
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.msgbox.MsgAppend('Error: Cannot use the save folder')
            return None
        name = f'{name}_{self.General.lockedslot or 0}'
        key = (str(folder), name, ext)
        n = self._nextn.get(key, 1)
        while (folder / f'{name}_{n:04d}.{ext}').is_file():
            n = n + 1
        self._nextn[key] = n + 1
        return folder / f'{name}_{n:04d}.{ext}'

    def SaveImage(self, img, name, ext='jpg', quiet=False):
        # Write an image to the save folder with a running number
        path = self.NextFile(name, ext)
        if path is None:
            self.StopRun()
            return
        img.save(path)
        self.auto_count = self.auto_count + 1
        if not quiet:
            self.msgbox.MsgAppend(f'Saved {path.name} '
                                  f'({img.size[0]}x{img.size[1]})')

    def SaveVideo(self, buf, name, path=None):
        # Assemble buffered JPEG frames into one video, AVI or GIF
        # by the format button. Frame timing comes from the run's
        # real timestamps so playback matches wall-clock time
        if len(buf) < 2:
            self.msgbox.MsgAppend('Error: Nothing recorded')
            return
        dur = buf[-1][0] - buf[0][0]
        if path is None:
            path = self.NextFile(name, ('avi', 'gif')[self.vidfmt])
            if path is None:
                return
        frames = [f for t, f in buf]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if self.vidfmt:
                ts = [t for t, f in buf]
                durs = [round((b - a) * 1000)
                        for a, b in zip(ts, ts[1:])]
                durs.append(round(sum(durs) / len(durs)))
                write_gif(path, frames, durs)
            else:
                fps = (len(buf) - 1) / dur if dur > 0 else 10.0
                size = Image.open(io.BytesIO(frames[0])).size
                write_avi(path, frames, size, fps)
        except OSError:
            self.msgbox.MsgAppend('Error: Cannot write the video')
            return
        self.msgbox.MsgAppend(f'Saved {path.name} '
                              f'({len(buf)} frames, {dur:.1f} s)')

    def RoundEnd(self, count):
        # Hunter thread: one hunt round just finished. An ordinary
        # round is only worth keeping when the user wants every
        # round; the shiny run never reaches here (the hunt stops
        # without counting) and is flushed by run_tick instead
        if self.runmode != 'afk' or not self.recbuf:
            return
        if self.rec_skip:
            # the half-captured round armed into: drop it, the next
            # round is the first complete one
            self.rec_skip = False
            self.recbuf = []
            return
        if int(self.shinyvar.get()) == 1:
            self.recbuf = []
            return
        self.RoundFlush(count)

    def RoundFlush(self, count):
        # Hand the buffer to a writer thread so neither the hunt
        # nor the GUI waits on video assembly; the file carries the
        # round number, matching the hunter's screenshots
        buf, self.recbuf = self.recbuf, []
        path = (Path(self.PathEntry.get()) /
                f'AFK_{self.General.lockedslot or 0}_{count:04d}.'
                f'{("avi", "gif")[self.vidfmt]}')
        threading.Thread(target=self.SaveVideo, name='afk-writer',
                         args=(buf, 'AFK', path), daemon=True).start()

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[i].recpath   = self.PathEntry.get()
        self.General.data[i].shotmode  = self.shotmode
        self.General.data[i].capmode   = self.capmode
        self.General.data[i].onlyshiny = int(self.shinyvar.get())
        self.General.data[i].vidfmt    = self.vidfmt

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI; an empty saved
        # path keeps the default folder chosen at startup. Loading a
        # Set ends any running capture first
        self.StopRun()
        d = self.General.data[i]
        if d.recpath:
            self.PathEntry.delete(0, 'end')
            self.PathEntry.insert(0, d.recpath)
        self.shotmode = d.shotmode if d.shotmode in (0, 1, 2) else 0
        self.ModeShow()
        self.capmode = d.capmode if d.capmode in (0, 1, 2, 3) else 0
        self.shinyvar.set(1 if d.onlyshiny else 0)
        self.vidfmt = d.vidfmt if d.vidfmt in (0, 1) else 0
        self.FmtShow()
        self.CapShow()
