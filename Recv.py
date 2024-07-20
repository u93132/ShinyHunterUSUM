import tkinter as tk
import time
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *

# Define the application class
class Recv:
    def __init__(self, nb, General, msgbox, image):
        
        #########################################################################
        ############################## Initialize  ##############################
        #########################################################################

        self.nb          = nb
        self.tabname     = 'Recv'
        self.frame       = nb.frame[nb.framename.index(self.tabname)] 
        self.General     = General # vars and GUI objects stored in General
        self.msgbox      = msgbox  # message box
        self.image       = image   # the background updating screen
        self.ir          = None    # pre assign the input redirection object
        self.threshold   = 0.15    # for image identification
        # Recv parameters
        self.picpath = './image0/' + self.tabname + '/'
        self.mys  = img2BW(Image.open(resource_path(self.picpath+'Mys.bmp')))
        self.lab = [None,None]
        self.lab[0] = img2BW(Image.open(
                             resource_path(self.picpath + '/Poipole.bmp') ))
        self.lab[1] = img2BW(Image.open(
                             resource_path(self.picpath + '/TypeNull.bmp') ))
        self.nom = [None,None]
        self.nom[0] = [136.37,  92.15, 219.39]
        self.nom[1] = [142.00, 147.00, 150.00]
        self.tar = [None,None]
        self.tar[0] = [250.00, 250.00, 250.00]
        self.tar[1] = [159.00, 154.00, 114.00]
        self.cut = [None,None]
        self.cut[0] = [196,100]
        self.cut[1] = [164, 72]
        
        #########################################################################
        ################################ Objects  ###############################
        #########################################################################

        self.recvbtn   = [None,None]
        self.recvvar   = tk.IntVar()
        self.recvvar.set(0)

        for i in range(2):
            self.recvbtn[i]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.recvvar, value=i)
            self.recvbtn[i].grid(row=0, column=i, padx=3, pady=8, sticky='w')
        self.recvbtn[0].config(text='Poipole')
        self.recvbtn[1].config(text='Type: Null')

    #############################################################################
    ############################### Functions ###################################
    #############################################################################

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
        
    def findrecv(self, poke):
        # Input
        # 0 is Poipole
        # 1 is Type: Null
        # Return shiny or not
        # -1: Other exceptions
        #  0: Not shiny
        #  1: Shiny            
        if poke == 1:
            for i in range(3):
                self.cpad(1.0, 0.0)
                time.sleep(0.1)
        for i in range(200):
            # Talk until you find the pokemon's name on the top screen
            img0 = self.image[1]
            img1 = self.image[1].crop((105,192,165,204))
            res = matchtemplate(img2BW(img1), self.lab[poke], 12, 60-18)
            if res > self.threshold:
                #print('Step 1:' + str(res))
                self.click(HIDButtons.A)
            else:
                #print('Step 1:' + str(res))
                for i in range(100):
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
        return  1.0, img0

    def main_procedure(self):
        # Start Recving Pokemon
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
                        ('Receive %04d' % self.General.start_count ) +
                         ' - ' + current_time + ' - %.2f' % ((1-res)*100) +
                         '% Shiny')
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
                        ('Receive %04d' % self.General.start_count) +
                         ' - N3DS crush?')
                    break
            if ((int(self.recvvar.get()) == 0 and res < self.threshold) or
                (int(self.recvvar.get()) == 1 and res < 0.4)):
                img0.save(self.General.shotpath +
                          '/' + ('%04d' % self.General.start_count) +'.jpg')
                self.ir.return_control()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'cyan')
                self.msgbox.MsgAppend('Receive pokemon completed!')
                break
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
        self.General.data[1][i]['recv']    = int(self.recvvar.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.recvvar.set(self.General.data[1][i]['recv'])
