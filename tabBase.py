import time
from PIL import Image
from functions import *
from tppflush import *

class HuntStopped(Exception):
    # Raised from the input helpers when the user pressed disconnect;
    # unwinds any depth of hunting loops back to main_procedure
    pass

# Shared base class for the feature tabs (Battle / Recv / Lotto):
# common init plumbing, input helpers, and the soft reset sequence
class TabBase:
    tabname   = ''     # subclass sets: which notebook tab this is
    threshold = 0.10   # subclass sets: image identification threshold
    logname   = ''     # subclass sets: message box line prefix

    def __init__(self, nb, General, msgbox, image):
        self.nb      = nb
        self.frame   = nb.frame[nb.framename.index(self.tabname)]
        self.General = General # vars and GUI objects stored in General
        self.msgbox  = msgbox  # message box
        self.image   = image   # the background updating screen
        self.ir      = None    # pre assign the input redirection object
        self.picpath = resource_path(f'image0/{self.tabname}')
        self.mys     = img2BW(Image.open(self.picpath/'Mys.bmp'))

    ############################################################################
    ############################### Functions ##################################
    ############################################################################

    def check_stop(self):
        # The Connect button pops back up ('raised') on disconnect;
        # abort the hunt before sending any further input
        if str(self.General.ConnectButton['relief']) == 'raised':
            raise HuntStopped

    def cpad(self, x, y):
        self.check_stop()
        d = (x**2 + y**2)**0.5
        d = d + (d == 0.0)
        x = x/d; y = y/d
        for i in range(2):
            self.ir.circle_pad_set(CPAD_Commands.CPADRIGHT,x)
            self.ir.circle_pad_set(CPAD_Commands.CPADUP,y)
            self.ir.send(print_sent=False)

    def click(self, button, t = 0.08):
        self.check_stop()
        for i in range(3):
            self.ir.press(button)
            self.ir.send(print_sent=False)
        time.sleep(t)
        for i in range(3):
            self.ir.unpress(button)
            self.ir.send(print_sent=False)
        time.sleep(t)

    def wait_for(self, box, template, h_t, w_diff=0,
                 button=None, thr=None, n=200, screen=1, ts=0.05, debug=False):
        # Press `button` (if given) until `template` matches the crop
        # `box` of screen 1 (top, default) or 0 (bottom), polling
        # every `ts` seconds.
        # True:  matched
        # False: timeout
        # (a disconnect raises HuntStopped through check_stop)
        if thr is None:
            thr = self.threshold
        for i in range(n):
            self.check_stop()
            img1 = self.image[screen].crop(box)
            res = matchtemplate(img2BW(img1), template, h_t, w_diff)
            if res < thr:
                return True
            if button is not None:
                self.click(button)
            time.sleep(ts)
            if debug:
                print(res)
        return False

    def restart_game(self):
        self.check_stop()
        # Game soft reset
        for i in range(2):
            self.ir.press(HIDButtons.L)
            self.ir.press(HIDButtons.R)
            self.ir.press(HIDButtons.SELECT)
            self.ir.send(print_sent=False)
            time.sleep(0.1)
        for i in range(2):
            self.ir.unpress(HIDButtons.L)
            self.ir.unpress(HIDButtons.R)
            self.ir.unpress(HIDButtons.SELECT)
            self.ir.send(print_sent=False)
            time.sleep(0.1)
        time.sleep(5.0)
        # Enter the game
        for i in range(30):
            img1 = self.image[1].crop((160,183,190,195))
            res = matchtemplate(img2BW(img1), self.mys, 12, 30-23)
            if res < self.threshold:
                self.click(HIDButtons.A)
                time.sleep(5.0)
                break
            else:
                self.click(HIDButtons.START,0.2)

    def main_procedure(self):
        # Drive the tab's hunt() and recover from a died input socket
        # (network drop / IP change): rebuild the socket and continue;
        # three failures in a row without progress means the
        # connection is really gone
        deaths = 0
        last_count = -1
        while True:
            try:
                self.hunt()
                return
            except HuntStopped:
                # User pressed disconnect: finish the handover, unlock
                self.General.ConnectState(-1)
                try:
                    self.ir.return_control()
                except OSError:
                    pass   # dead socket: 3DS side already has control
                return
            except OSError:
                if self.General.start_count != last_count:
                    deaths = 0     # progress made since the last death
                last_count = self.General.start_count
                deaths += 1
                if deaths > 3:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.msgbox.MsgAppend(
                        f'{self.logname} {self.General.start_count:04d}'
                        ' - 3DS connection lost')
                    return
                self.msgbox.MsgAppend('Error: Input socket died, '
                                      f'rebuilding ({deaths}/3)...')
                self.ir = LumaInputServer(self.General.clientIP)
