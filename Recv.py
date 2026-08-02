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

    def __init__(self, nb, General, msgbox, image):

        #########################################################################
        ############################## Initialize  ##############################
        #########################################################################

        super().__init__(nb, General, msgbox, image)
        # Recv parameters
        starter = img2BW(Image.open(self.picpath/'Starter.bmp'))
        self.lab = [img2BW(Image.open(self.picpath/'Poipole.bmp')),
                    img2BW(Image.open(self.picpath/'TypeNull.bmp')),
                    starter, starter, starter]
        self.nom = [None,None]
        self.nom[0] = [136.37,  92.15, 219.39]
        self.nom[1] = [142.00, 147.00, 150.00]
        self.tar = [None,None]
        self.tar[0] = [250.00, 250.00, 250.00]
        self.tar[1] = [159.00, 154.00, 114.00]
        self.cut = [None,None]
        self.cut[0] = [196,100]
        self.cut[1] = [164, 72]

        self.ap   = img2BW(Image.open(self.picpath/'ap.bmp'))
        self.go   = img2BW(Image.open(self.picpath/'go.bmp'))
        self.do   = img2BW(Image.open(self.picpath/'do.bmp'))
        self.ro   = img2BW(Image.open(self.picpath/'ro.bmp'))
        self.yo   = img2BW(Image.open(self.picpath/'yo.bmp'))
        self.bu   = img2BW(Image.open(self.picpath/'bu.bmp'))
        self.bg   = img2BW(Image.open(self.picpath/'bg.bmp'))
        
        #########################################################################
        ################################ Objects  ###############################
        #########################################################################

        self.recvbtn   = [None,None,None,None,None]
        self.recvvar   = tk.IntVar()
        self.recvvar.set(0)

        for i in range(2):
            self.recvbtn[i]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i)
            self.recvbtn[i].grid(row=0, column=i, padx=3, pady=8, sticky='w')
        for i in range(3):
            self.recvbtn[i+2]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i+2)
            self.recvbtn[i+2].grid(row=1, column=i, padx=3, pady=8, sticky='w')
        self.recvbtn[0].config(text='Poipole')
        self.recvbtn[1].config(text='Type: Null')
        self.recvbtn[2].config(text='Rowlet')
        self.recvbtn[3].config(text='Litten')
        self.recvbtn[4].config(text='Popplio')

    #############################################################################
    ############################### Functions ###################################
    #############################################################################

    def findrecv(self, poke):
        # Input
        # 0 is Poipole
        # 1 is Type: Null
        # 2 is Rowlet
        # 3 is Litten
        # 4 is Popplio
        # Return shiny or not
        # -1: Other exceptions
        #  0: Not shiny
        #  1: Shiny            
        for i in range(3):
            if poke == 1:
                self.cpad(1.0, 0.0)
                time.sleep(0.1)
                self.cpad(0.0, 0.0)
            if poke > 1:
                self.cpad(0.0, 1.0)
                time.sleep(0.1)
                self.cpad(0.0, 0.0)

        # Talk until you find the pokemon's name on the top screen
        if not self.wait_for((105,192,165,204), self.lab[poke], 12, 60-18,
                             button=HIDButtons.A, n=1000):
            return 1.0, self.image[1]
        img0 = self.image[1]
        
        if poke < 2:
            for j in range(100):
                self.check_stop()
                # Talk until you find the pokemon's name on the top screen
                img0 = self.image[1]
                img1 = self.image[1].crop((170,192,210,204))
                res = matchtemplate(img2BW(img1), self.lab[poke], 12, 40-18)
                if res > self.threshold:
                    #print('Step 2:' + str(res))
                    self.ir.touch(240,20)
                    self.ir.send(print_sent=False)
                    time.sleep(0.1)
                    self.ir.clear_touch()
                    self.ir.send(print_sent=False)
                else:
                    #print('Step 2:' + str(res))
                    time.sleep(0.2)
                    img0 = self.image[1]
                    img1 = self.image[1].crop((self.cut[poke][0],
                                               self.cut[poke][1],
                                               self.cut[poke][0]+4,
                                               self.cut[poke][1]+4))
                    res_tar = diffnorm(img2avRGB(img1),self.tar[poke])
                    d       = diffnorm(self.nom[poke],self.tar[poke])
                    res_tar = res_tar / d
                    return  res_tar, img0
        else:
            # Press B until the starter selection menu (ro) shows up
            if not self.wait_for((297,129,321,141), self.ro, 12,
                                 button=HIDButtons.B):
                return 1.0, self.image[1]

            for i in range(poke-2):
                self.cpad(0.0, -1.0)
                time.sleep(0.05)
                self.cpad(0.0, 0.0)
                time.sleep(0.5)
                
            # Press A until the confirm dialog (yo) shows up
            if not self.wait_for((48,192,70,204), self.yo, 12,
                                 button=HIDButtons.A):
                return 1.0, self.image[1]

            # Press B until the next dialog (bu) shows up
            if not self.wait_for((271,149,290,161), self.bu, 12,
                                 button=HIDButtons.B):
                return 1.0, self.image[1]

            # Press A until the handover screen (bg) shows up
            if not self.wait_for((187,54,227,121), self.bg, 67,
                                 button=HIDButtons.A):
                return 1.0, self.image[1]
                
            self.cpad(-1.0, 1.0)
            time.sleep(2.0)
            self.cpad(0.0, 0.0)

            # Wait until 'appear' (ap) shows up on the dialog
            if not self.wait_for((35,205,235,218), self.ap, 13, 200-24):
                return 1.0, self.image[1]
            t_app = time.time()
            img0 = self.image[1]
            # Shiny check: the time between 'go' and 'do' in the dialog
            if not self.wait_for((13,203,33,215), self.go, 12):
                return 1.0, img0
            t_go = time.time()
            if not self.wait_for((47,203,65,215), self.do, 12,
                                 thr=self.threshold+0.05):
                return 1.0, img0
            t_use = int((time.time() - t_go)*1000)
            return (5920-t_use)/600, img0
                
        return  1.0, img0

    def main_procedure(self):
        # Start Recving Pokemon
        try:
            while True:
                # Trigger the event
                res, img0 = self.findrecv(int(self.recvvar.get()))
                self.ir.clear_everything()
                self.ir.circle_pad_neutral()
                # Get current time
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                # Check the result
                self.msgbox.MsgAppend(
                    f'Receive {self.General.start_count:04d}'
                    f' - {current_time} - {(1-res)*100:.2f}% Shiny')
                # Update the counter and plus one
                self.General.CounterPlusOne()
                if res == 1:
                    try:
                        # Test if 3DS is still alive
                        self.General.test3DS()
                    except:
                        self.General.ConnectState(0)
                        self.General.ConnectState(-1)
                        self.msgbox.msgbox.config(bg = 'red')
                        self.msgbox.MsgAppend(
                            f'Receive {self.General.start_count:04d}'
                            ' - N3DS crush?')
                        break
                if ((int(self.recvvar.get()) == 0 and res < self.threshold) or
                    (int(self.recvvar.get()) >= 1 and res < 0.4)):
                    img0.save(self.General.shotpath /
                              f'{self.General.start_count:04d}.jpg')
                    self.ir.return_control()
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'cyan')
                    self.msgbox.MsgAppend('Receive pokemon completed!')
                    break
                # Game soft reset and re-enter
                self.restart_game()
        except HuntStopped:
            # User pressed disconnect: finish the handover and unlock
            self.General.ConnectState(-1)
            self.ir.return_control()

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[1][i]['recv']    = int(self.recvvar.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.recvvar.set(self.General.data[1][i]['recv'])
