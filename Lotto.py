import tkinter as tk
import time
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *

# Define the application class
class Lotto:
    def __init__(self, nb, General, msgbox, image):
        
        ########################################################################
        ############################## Initialize ##############################
        ########################################################################

        self.nb          = nb
        self.tabname     = 'Lotto' 
        self.frame       = nb.frame[nb.framename.index(self.tabname)] 
        self.General     = General # vars and GUI objects stored in General
        self.msgbox      = msgbox  # message box
        self.image       = image   # the background updating screen
        self.ir          = None    # pre assign the input redirection object
        self.threshold   = 0.05    # for image identification
        # Lotto parameters
        self.picpath = './image0/' + self.tabname + '/'
        self.img0 = img2BW(Image.open(resource_path(self.picpath+'temp.bmp')))
        self.mys  = img2BW(Image.open(resource_path(self.picpath+'Mys.bmp')))
        self.namelist = ['Bargain', 'Boost', 'Catch', 'Encounter', 'Exp Points',
                         'Friendship', 'HP Restore', 'Hatch', 'Prize Money',
                         'PP Restore', 'Stealth']
        self.imglist  = [None for i in self.namelist]
        for i in range(len(self.namelist)):
            self.imglist[i] = img2BW( Image.open(
                              resource_path(self.picpath +
                                            self.namelist[i] +'.bmp') ) )

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

    def cpad(self, x, y):
        d = (x**2 + y**2)**0.5
        d = d + (d == 0.0)
        x = x/d; y = y/d
        for i in range(2):
            self.ir.circle_pad_set(CPAD_Commands.CPADRIGHT,x)
            self.ir.circle_pad_set(CPAD_Commands.CPADUP,y)
            self.ir.send(print_sent=False)
        
    def click(self, button, t = 0.08):
        for i in range(3):
            self.ir.press(button)
            self.ir.send(print_sent=False)
        time.sleep(t)
        for i in range(3):
            self.ir.unpress(button)
            self.ir.send(print_sent=False)
        time.sleep(t)

    def reset(self, t = 0.1):
        for i in range(3):
            self.ir.clear_everything()
        time.sleep(t)
        
    def switch(self):
        self.rotostate = [i.get() for i in self.rotovar]

    def findloto(self):
        # Return which one that Roto gave you
        # -1:         Roto is asking questions or other exceptions
        # other ints: the corresponing index in self.namelist
        # Ex: return 2 means the return is Roto Catch
        time.sleep(1.0)
        for i in range(100):
            # Tap the screen until you find "Roto" on the top screen
            img1 = self.image[1].crop((144,192,170,204))
            res = matchtemplate(img2BW(img1), self.img0, 12, 0)
            if res > self.threshold:
                self.ir.touch(240,60)
                self.ir.send(print_sent=False)
                time.sleep(0.1)
                self.ir.clear_touch()
                self.ir.send(print_sent=False)
                time.sleep(0.1)
            else:
                # Wait 0.5 seconds until the line on the screen is completed
                # Then check which one is it
                time.sleep(0.5)
                for i in range(len(self.imglist)):
                    img1 = self.image[1].crop((175,192,199,204))
                    res = matchtemplate(img2BW(img1), self.imglist[i], 12, 0)
                    if res < self.threshold:
                        return i
        return -1

    def main_procedure(self):
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
                except:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.MsgAppend(('Loto %04d' % self.General.start_count) +
                                   ' - N3DS crush?')
                else:
                    self.msgbox.MsgAppend(
                        ('Loto %04d' % self.General.start_count ) +
                         ' - ' + current_time + ' - Roto Asking' )
            elif self.rotostate[res]:
                self.msgbox.MsgAppend(
                    ('Loto %04d' % self.General.start_count ) +
                     ' - ' + current_time + ' - Done' )
                self.ir.return_control()
                self.General.CounterPlusOne()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'lime')
                self.msgbox.MsgAppend('Lotto draw completed!')
                break
            else:
                self.msgbox.MsgAppend(
                    ('Loto %04d' % self.General.start_count ) +
                     ' - ' + current_time + ' - Roto '  +
                     self.namelist[res] )
            # Update the counter and plus one
            self.General.CounterPlusOne()
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
            if str(self.General.ConnectButton['relief']) == 'raised':
                self.General.ConnectState(-1)
                self.ir.return_control()
                break

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[1][i]['loto'] = (
            [enum for enum,k in enumerate(self.rotostate) if k == 1] )

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        for k in range(len(self.namelist)):
            if k in self.General.data[1][i]['loto']:
                self.rotovar[k].set(1)
            else:
                self.rotovar[k].set(0)
        self.rotostate = [x.get() for x in self.rotovar]      # int list


