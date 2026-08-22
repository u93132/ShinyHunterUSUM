import tkinter as tk
import time
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *
from tabBase import TabBase, HuntStopped

# Define the application class
class Recv(TabBase):
    tabname   = 'Recv'
    threshold = 0.15    # for image identification
    logname   = 'Receive'

    def __init__(self, nb, General, msgbox, image):

        #########################################################################
        ############################## Initialize  ##############################
        #########################################################################

        super().__init__(nb, General, msgbox, image)
        # Recv parameters
        poipole  = img2BW(Image.open(self.picpath/'Poipole.bmp'))
        typenull = img2BW(Image.open(self.picpath/'TypeNull.bmp'))
        starter  = img2BW(Image.open(self.picpath/'Starter.bmp'))
        pikachu  = img2BW(Image.open(self.picpath/'Pikachu.bmp'))
        # Dialogue name templates (Aether shares the Type: Null one)
        self.lab = [poipole, typenull, typenull,
                    starter, starter, starter,
                    pikachu]
        # Summary page name templates
        self.nam = [poipole, typenull, typenull,
                    img2BW(Image.open(self.picpath/'Rowlet.bmp')),
                    img2BW(Image.open(self.picpath/'Litten.bmp')),
                    img2BW(Image.open(self.picpath/'Popplio.bmp')),
                    pikachu]

        self.naminv = [invertBW(x) for x in self.nam]

        # Shiny star check on the summary page: every target reads the
        # same spot, so all six share one normal/shiny color pair
        self.nom = [128.86, 242.03, 73.97]
        self.tar = [174.08, 126.38, 40.03]

        # Boost mode: the original in-scene check spots and colors
        # (Poipole / Type: Null; Aether shares the Poni values)
        tn_cut = [177, 129]
        tn_nom = [143.22, 146.74, 151.71]
        tn_tar = [158.10, 145.65, 119.19]
        self.cut  = [[196, 100], tn_cut, tn_cut,
                     [210, 124],
                     [192, 106],
                     [204, 127],
                     None]
        self.nomb = [[136.37,  92.15, 219.39], tn_nom, tn_nom,
                     [233.61, 190.17, 147.13],
                     [ 79.44,  95.04, 106.47],
                     [189.81, 240.05, 244.52],
                     None]
        self.tarb = [[250.00, 250.00, 250.00], tn_tar, tn_tar,
                     [132.46, 193.54, 165.05],
                     [227.95, 220.50, 215.24],
                     [184.07, 167.99, 172.58],
                     None]
        
        self.ty   = img2BW(Image.open(self.picpath/'ty.bmp'))
        self.to   = img2BW(Image.open(self.picpath/'to.bmp'))
        self.mo   = img2BW(Image.open(self.picpath/'mo.bmp'))
        self.no   = img2BW(Image.open(self.picpath/'no.bmp'))
        #self.po   = img2BW(Image.open(self.picpath/'po.bmp'))
        self.be   = img2BW(Image.open(self.picpath/'be.bmp'))
        self.be2  = img2BW(Image.open(self.picpath/'be2.bmp'))
        self.ap   = img2BW(Image.open(self.picpath/'ap.bmp'))
        self.go   = img2BW(Image.open(self.picpath/'go.bmp'))
        self.do   = img2BW(Image.open(self.picpath/'do.bmp'))
        self.ro   = img2BW(Image.open(self.picpath/'ro.bmp'))
        self.yo   = img2BW(Image.open(self.picpath/'yo.bmp'))
        self.bu   = img2BW(Image.open(self.picpath/'bu.bmp'))
        self.bg   = img2BW(Image.open(self.picpath/'bg.bmp'))
        self.Lv   = img2BW(Image.open(self.picpath/'Lv.bmp'))
        
        #########################################################################
        ################################ Objects  ###############################
        #########################################################################

        self.recvbtn   = [None,None,None,None,None,None,None]
        self.recvvar   = tk.IntVar()
        self.recvvar.set(0)

        for i in range(3):
            self.recvbtn[i]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i)
            self.recvbtn[i].grid(row=0, column=i, padx=3, pady=8, sticky='w')
        for i in range(3):
            self.recvbtn[i+3]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i+3)
            self.recvbtn[i+3].grid(row=1, column=i, padx=3, pady=2, sticky='w')
        for i in range(1):
            self.recvbtn[i+6]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i+6)
            self.recvbtn[i+6].grid(row=2, column=i, padx=3, pady=8, sticky='w')
        self.recvbtn[0].config(text='Poipole')
        self.recvbtn[1].config(text='TN-Poni')
        self.recvbtn[2].config(text='TN-Aether')
        self.recvbtn[3].config(text='Rowlet')
        self.recvbtn[4].config(text='Litten')
        self.recvbtn[5].config(text='Popplio')
        self.recvbtn[6].config(text='Pikachu')
        # Boost mode: use the original in-scene shiny check
        self.boostvar = tk.IntVar()
        self.boostbtn = tk.Checkbutton(self.frame, width=8, anchor='w',
                                       variable=self.boostvar,
                                       text='Boost',
                                       command=self.boostswitch)
        self.boostbtn.grid(row=2, column=2, padx=3, pady=2, sticky='w')

    #############################################################################
    ############################### Functions ###################################
    #############################################################################

    def boostswitch(self):
        # Boost mode only supports the first-row targets: lock the
        # other rows out and pull the selection back if needed
        if int(self.boostvar.get()) == 1:
            if int(self.recvvar.get()) > 5:
                self.recvvar.set(0)
            for btn in self.recvbtn[6:]:
                btn.config(state = 'disabled')
        else:
            for btn in self.recvbtn[6:]:
                btn.config(state = 'normal')

    def findrecv(self, poke):
        # Input
        # 0 is Poipole
        # 1 is Type: Null (Poni)
        # 2 is Type: Null (Aether)
        # 3 is Rowlet
        # 4 is Litten
        # 5 is Popplio
        # 6 is Pikachu
        # +100: Boost mode - the original in-scene shiny check
        # Return (result, screenshot)
        # float result: shiny score, close to 0 means shiny
        # int result:   error code, hundreds digit = stage
        #   101      dialogue name never showed up
        #   2TS      nav_dialogue, T = target, S = step
        #     201      Poipole - 'ty' (added to party)
        #     211      Poni    - 'be' (end of dialogue)
        #     221/222  Aether  - 'ty' / 'be,be2'
        #     261      Pikachu - 'no' (end of dialogue)
        #   301/302  starter select: 'ro' menu / 'yo' confirm
        #   311/312  starter dialogs: 'bu' / 'bg'
        #   501-503  summary check: menu / 'Lv' / party name
        #   601-603  Boost: 'ro' / 'yo' / in-scene name
        boost = poke >= 100
        poke  = poke % 100
        for i in range(3):
            if poke == 1:
                self.cpad(1.0, 0.0)
                time.sleep(0.1)
                self.cpad(0.0, 0.0)
            if 2 < poke < 6:
                self.cpad(-1.0, 0.0)
                time.sleep(0.1)
                self.cpad(0.0, 0.0)

        # Talk until you find the pokemon's name on the top screen
        if not self.wait_for((105,192,165,204), self.lab[poke], 12, 60-18,
                             button=HIDButtons.A, n=1000):
            return 101, self.image[1]

        if boost:
            if 2 < poke < 6:
                err = self.select_starter(poke, 601)
                if err is not None:
                    return err, self.image[1]
            return self.check_inscene(poke)

        err = self.nav_dialogue(poke)
        if err is not None:
            return err, self.image[1]
        return self.check_summary(poke)

    def select_starter(self, poke, err):
        # ro menu -> move down to the chosen starter -> confirm (yo)
        # Returns `err` / `err+1` on timeout, None when done
        if not self.wait_for((297,129,321,141), self.ro, 12,
                             button=HIDButtons.B):
            return err
        # Switch between the starters
        for i in range(poke-3):
            self.click(HIDButtons.DPADDOWN)
            time.sleep(0.5)
        # Press A until the confirm dialog (yo) shows up
        if not self.wait_for((48,192,70,204), self.yo, 12,
                             button=HIDButtons.A):
            return err + 1
        return None

    def check_inscene(self, poke):
        # Boost mode: tap through the dialogue until the name shows
        # up, then read the calibrated color patch in the scene
        if not self.wait_for((170,192,210,204), self.nam[poke], 12, 40-18,
                             button=(240,20), n=100, screen=1, ts=0.1):
            return 603, self.image[1]
        time.sleep(0.2)
        img0 = self.image[1]
        img1 = img0.crop((self.cut[poke][0],
                          self.cut[poke][1],
                          self.cut[poke][0]+3,
                          self.cut[poke][1]+3))
        res_tar = diffnorm(img2avRGB(img1), self.tarb[poke])
        d       = diffnorm(self.nomb[poke], self.tarb[poke])
        return res_tar / d, img0

    def nav_dialogue(self, poke):
        # Walk the per-target dialogue after the name showed up
        # Returns an error code, None once the pokemon is received
        if poke == 0:
            # Press B until the added to your party (ty) shows up
            if not self.wait_for((262,193,302,207), self.ty, 14, 40-11,
                             button=HIDButtons.B, n=200):
                return 201

        elif poke == 1:
            # Press B until the end of the dialogue
            if not self.wait_for((227,212,241,224), self.be, 12,
                             button=HIDButtons.B, n=200):
                return 211

        elif poke == 2:
            # Press B until the added to your party (ty) shows up
            if not self.wait_for((262,193,302,207), self.ty, 14, 40-11, 1,
                             button=HIDButtons.B, n=200):
                return 221

            # Press A until the dialogue over
            if not self.wait_for((101,192,115,204), [self.be,self.be2], 12,
                             button=HIDButtons.A, n=200):
                return 222
            for i in range(2): self.click(HIDButtons.B)
            time.sleep(2.0)

        elif poke == 6:
            # Press B until the end of the dialogue
            if not self.wait_for((55,212,73,224), self.no, 12,
                             button=HIDButtons.B, n=200):
                return 261
            for i in range(2): self.click(HIDButtons.B)
            time.sleep(2.0)

        else:
            err = self.select_starter(poke, 301)
            if err is not None:
                return err

            # Press B until the next dialog (bu) shows up
            if not self.wait_for((271,149,290,161), self.bu, 12,
                                 button=HIDButtons.B):
                return 311

            # Press A until the handover screen (bg) shows up
            if not self.wait_for((187,54,227,121), self.bg, 67,
                                 button=HIDButtons.A):
                return 312
        return None

    def check_summary(self, poke):
        # Open the menu, walk to the received pokemon, and read the
        # shiny star on its summary page
        # Make sure clean up all the dialogue
        for i in range(10):
            self.click(HIDButtons.B)
            time.sleep(0.05)
            
        # Wait until menu shows up, remember place the pokemon label at first
        if not self.wait_for((27,211,38,222), self.bb, 11,
                                button=HIDButtons.X, screen=0, ts=0.5):
            return 501, self.image[0]

        # Wait until 'Lv' shows up on the lower screen
        if not self.wait_for((46,56,63,66), self.Lv, 10, 17-13, 1,
                             button=HIDButtons.A, ts=0.5, screen=0):
            return 502, self.image[0]

        # Switch to the last pokemon in your team
        time.sleep(0.2)
        n = 3
        for i in range(n):
            if self.wait_for((227,222,238,233), self.to, 11, screen=0, ts=0.1, n=1):
                self.click(HIDButtons.B)
                time.sleep(0.2)
            if self.wait_for((221,224,237,233), self.mo, 16, screen=0, ts=0.1, n=1):
                self.click(HIDButtons.B)
                time.sleep(0.2)
            if not self.wait_for((46,35,68,47),
                                 [self.nam[poke], self.naminv[poke]], 12, 22-18, 1,
                                 button=HIDButtons.DPADUP, screen=0, ts=0.3, n=10):
                if i == n-1:  return 503, self.image[0]
            else:
                break

        # Check the star on the summary page
        time.sleep(0.3)
        img0 = self.image[0]
        img1 = img0.crop((59,184,67,192))
        img2 = img0.crop((45,186,53,194))
        d       = diffnorm(self.nom,self.tar)
        res_tar1= diffnorm(img2avRGB(img1),self.tar)
        res_tar2= diffnorm(img2avRGB(img2),self.tar) # for Pokemon SM
        res_tar = min(res_tar1,res_tar2) / d
        return res_tar, self.image[0]

    def hunt(self, gametype=0):
        # Check Pokemon game version
        if gametype == 2 and int(self.recvvar.get()) != 2:
            self.General.ConnectState(0)
            self.General.ConnectState(-1)
            self.msgbox.msgbox.config(bg = 'red')
            self.msgbox.MsgAppend(
                f'This function is not supported for S/M')
        # Start Recving Pokemon
        while True:
            # Trigger the event; Boost mode is encoded as +100
            base  = int(self.recvvar.get())
            boost = int(self.boostvar.get())
            res, img0 = self.findrecv(base + 100*boost)
            self.ir.clear_everything()
            self.ir.circle_pad_neutral()
            # Get current time
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            if isinstance(res, int):
                try:
                    # Test if 3DS is still alive
                    self.General.test3DS()
                except OSError:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.msgbox.MsgAppend(
                        f'Receive {self.General.start_count:04d}'
                        ' - N3DS crush?')
                    break
                else:
                    combine_images(self.image).save(self.General.shotpath /
                          f'Debug_Recv_'
                          f'{self.General.lockedslot or 0}_'
                          f'{self.General.start_count:04d}_'
                          f'{res:03d}.jpg')
                    self.msgbox.MsgAppend(
                        f'Receive {self.General.start_count:04d}'
                        f' - {current_time} - Error {res:03d}')
            else:
                # Check the result, res close to 0 means shiny
                self.msgbox.MsgAppend(
                    f'Receive {self.General.start_count:04d}'
                    f' - {current_time} - {(1-res)*100:.2f}% Shiny')

            # Boost mode uses one unified shiny threshold
            limit = 0.4 if boost else self.threshold
            if res < limit:
                img0.save(self.General.shotpath /
                          f'Recv_{self.General.lockedslot or 0}_'
                          f'{self.General.start_count:04d}.jpg')
                # Let the shiny play on for the recorder's tail
                time.sleep(self.linger)
                self.ir.return_control()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'cyan')
                self.msgbox.MsgAppend('Receive pokemon completed!')
                break
            # Update the counter and plus one
            self.General.CounterPlusOne()
            # Game soft reset and re-enter
            self.restart_game()

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        # (Boost mode is encoded as +100 on top of the target index)
        self.General.data[i].recv = (int(self.recvvar.get())
                                     + 100*int(self.boostvar.get()))

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        v = int(self.General.data[i].recv)
        self.recvvar.set(v % 100)
        self.boostvar.set(v // 100)
        self.boostswitch()
