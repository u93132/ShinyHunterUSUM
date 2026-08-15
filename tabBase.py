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
        self.bb      = img2BW(Image.open(self.picpath/'bb.bmp'))

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

    def wait_for(self, box, template, h_t, w_diff=0, v_diff=0,
                 button=None, thr=None, n=200, screen=1, ts=0.05,
                 debug=False):
        # Press button (if given) until template matches the crop
        # box of screen 1 (top, default) or 0 (bottom), polling
        # every ts seconds. template is one img2BW list or a list
        # of them; matching ANY counts. v_diff also tries the crop
        # shifted up/down by up to that many pixels.
        # True:  matched
        # False: timeout
        # (a disconnect raises HuntStopped through check_stop)
        if thr is None:
            thr = self.threshold
        # Normalize: a single template is a flat list of ints
        if not isinstance(template[0], list):
            template = [template]
        x0, y0, x1, y1 = box
        for i in range(n):
            self.check_stop()
            # one grayscale strip per vertical offset...
            bws = [img2BW(self.image[screen].crop(
                              (x0, y0 + d, x1, y1 + d)))
                   for d in range(-v_diff, v_diff + 1)]
            # ...then the best score over every offset x template pair
            res = min(matchtemplate(bw, t, h_t, w_diff)
                      for bw in bws for t in template)
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
        # Leave Mystery Gift or Live Competition
        for i in range(10): self.click(HIDButtons.B, 0.2)
        time.sleep(1.0)
        # Enter the game
        self.wait_for((160,183,190,195), self.mys, 12, 30-23, 1,
                      button=HIDButtons.START, n=30, ts=0.2)
        for i in range(2): self.click(HIDButtons.A)
        time.sleep(5.0)
            
##        for i in range(30):
##            img1 = self.image[1].crop((160,183,190,195))
##            res = matchtemplate(img2BW(img1), self.mys, 12, 30-23)
##            if res < self.threshold:
##                self.click(HIDButtons.A)
##                time.sleep(5.0)
##                break
##            else:
##                self.click(HIDButtons.START,0.2)

    def give_up(self):
        # Unrecoverable connection failure: red screen, unlock, stop
        self.General.ConnectState(0)
        self.General.ConnectState(-1)
        self.msgbox.msgbox.config(bg = 'red')
        self.msgbox.MsgAppend(
            f'{self.logname} {self.General.start_count:04d}'
            ' - 3DS connection lost')

    def main_procedure(self):
        # Drive the tab's hunt()
        try:
            self.hunt()
        except HuntStopped:
            # User pressed disconnect: finish the handover and unlock
            self.General.ConnectState(-1)
            try:
                self.ir.return_control()
            except OSError:
                pass   # dead socket: 3DS side already has control
        except OSError:
            # The input socket died (network drop / IP change):
            # stop with the red screen
            self.give_up()
        except Exception:
            # Whatever just happened, never leave the GUI locked;
            # re-raise so the traceback still shows in debug builds
            self.give_up()
            raise
