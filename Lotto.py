import tkinter as tk
import time
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *
from tabBase import TabBase, HuntStopped

# Define the application class
class Lotto(TabBase):
    tabname   = 'Lotto'
    threshold = 0.05    # for image identification
    logname   = 'Loto'

    def __init__(self, nb, General, msgbox, image):

        ########################################################################
        ############################## Initialize ##############################
        ########################################################################

        super().__init__(nb, General, msgbox, image)
        # Lotto parameters
        self.img0 = img2BW(Image.open(self.picpath/'temp.bmp'))
        self.namelist = ['Bargain', 'Boost', 'Catch', 'Encounter', 'Exp Points',
                         'Friendship', 'HP Restore', 'Hatch', 'Prize Money',
                         'PP Restore', 'Stealth']
        self.imglist  = [img2BW(Image.open(self.picpath/f'{name}.bmp'))
                         for name in self.namelist]

        ########################################################################
        ################################ Objects ###############################
        ########################################################################

        self.rotobtn   = [None for i in self.namelist]        # Btn list
        self.rotovar   = [tk.IntVar() for i in self.namelist] # tk IntVar list
        self.rotovar[1].set(1)                                # Roto Boost "on"
        self.rotostate = [i.get() for i in self.rotovar]      # int list

        for i in range(len(self.namelist)):
            self.rotobtn[i]=tk.Checkbutton(self.frame, width=8, anchor='w',
                                              variable=self.rotovar[i])
            self.rotobtn[i].grid(row=int(i/3), column=i%3,
                                 padx=0, pady=2, sticky='w')
            self.rotobtn[i].config(text=self.namelist[i])
            self.rotobtn[i].config(command=self.switch)

    ############################################################################
    ################################ Functions #################################
    ############################################################################

    def switch(self):
        self.rotostate = [i.get() for i in self.rotovar]

    def findloto(self):
        # Return which one that Roto gave you
        # -1:         Roto is asking questions or other exceptions
        # other ints: the corresponding index in self.namelist
        # Ex: return 2 means the return is Roto Catch
        time.sleep(1.0)
        # Tap the screen until 'Roto' shows up on the top screen
        if not self.wait_for((144,192,170,204), self.img0, 12,
                             button=(240,60), n=100, ts=0.1):
            return -1
        # Wait until the line on the screen is completed, then
        # check which one is it (retry while the text settles)
        time.sleep(0.5)
        hit = self.wait_for((175,192,199,204), self.imglist, 12,
                            n=10, ts=0.5)
        if not hit:
            return -1
        return hit - 1

    def hunt(self):
        # Start Lotto Drawing
        while True:
            # Trigger the event
            res = self.findloto()
            # Get current time
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            # Check the draw result
            if res == -1:
                try:
                    # Test if 3DS is still alive
                    self.General.test3DS()
                except OSError:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.msgbox.MsgAppend(
                        f'Loto {self.General.start_count:04d}'
                        ' - N3DS crush?')
                    break
                else:
                    self.msgbox.MsgAppend(
                        f'Loto {self.General.start_count:04d}'
                        f' - {current_time} - Roto Asking' )
            elif self.rotostate[res]:
                self.msgbox.MsgAppend(
                    f'Loto {self.General.start_count:04d}'
                    f' - {current_time} - Done' )
                self.ir.return_control()
                self.General.CounterPlusOne()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'lime')
                self.msgbox.MsgAppend('Lotto draw completed!')
                break
            else:
                self.msgbox.MsgAppend(
                    f'Loto {self.General.start_count:04d}'
                    f' - {current_time} - Roto {self.namelist[res]}' )
            # Update the counter and plus one
            self.General.CounterPlusOne()
            # Game soft reset and re-enter
            self.restart_game()

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[i].loto = (
            [enum for enum,k in enumerate(self.rotostate) if k == 1] )

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        for k in range(len(self.namelist)):
            if k in self.General.data[i].loto:
                self.rotovar[k].set(1)
            else:
                self.rotovar[k].set(0)
        self.rotostate = [x.get() for x in self.rotovar]      # int list


