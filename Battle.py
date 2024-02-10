import tkinter as tk
import time, math
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *

# Define the application class
class Battle:
    def __init__(self, nb, General, msgbox, image):
        
        #########################################################################
        ############################## Initialize  ##############################
        #########################################################################

        self.nb          = nb
        self.tabname     = 'Battle' 
        self.frame       = nb.frame[nb.framename.index(self.tabname)] 
        self.General     = General # vars and GUI objects stored in General
        self.General.data        = General.data # Setting data structure
        self.msgbox      = msgbox  # message box
        self.image       = image   # the background updating screen
        self.ir          = None    # pre assign the input redirection object
        self.threshold   = 0.10    # for image identification
        # Battle parameters
        self.picpath = './image0/' + self.tabname + '/'
        self.ap   = img2BW(Image.open(resource_path(self.picpath+'ap.bmp')))
        self.go   = img2BW(Image.open(resource_path(self.picpath+'go.bmp')))
        self.chat = 2700           # 2700ms for normal pokemon

        #########################################################################
        ################################ Objects  ###############################
        #########################################################################

        self.movebtn   = [None,None]
        self.movevar   = tk.IntVar()
        self.movevar.set(0)

        self.movelab   = tk.Label(self.frame, width=8, anchor='w', text = 'Trigger: ')
        self.movelab.grid(row=0, column=0, padx=3, pady=8, sticky='w')

        for i in range(2):
            self.movebtn[i]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.movevar, value=i)
            self.movebtn[i].grid(row=0, column=i+1, padx=0, pady=2, sticky='w')
        self.movebtn[0].config(text='Move')
        self.movebtn[1].config(text='Talk')

        self.auralab   = tk.Label(self.frame, width=8, anchor='w', text = 'Type: ')
        self.auralab.grid(row=1, column=0, padx=3, pady=8, sticky='w')

        self.aurabtn   = [None,None]
        self.auravar   = tk.IntVar()
        self.auravar.set(0)

        for i in range(2):
            self.aurabtn[i]=tk.Radiobutton(self.frame, width=8, anchor='w',
                                             variable=self.auravar, value=i)
            self.aurabtn[i].grid(row=1, column=i+1, padx=0, pady=2, sticky='w')
            self.aurabtn[i].config(command=self.auraswitch)
        self.aurabtn[0].config(text='No aura')
        self.aurabtn[1].config(text='With aura')

    #############################################################################
    ############################### Functions ###################################
    #############################################################################

    def auraswitch(self):
        if int(self.auravar.get()) == 0:
            # 2700ms for no aura pokemon
            self.chat = 2700
        elif int(self.auravar.get()) == 1:
            # 8600ms for aura pokemon
            self.chat = 8600

    def findtime(self):
        # Return the time between 'appear' and 'Go!'
        # res:  the time between 'appear' and 'Go!'
        # img0: the screenshot when the pokemon appears
        for i in range(150):
            if int(self.movevar.get()) == 0:
                # Move around
                self.ir.press(HIDButtons.B)
                self.ir.circle_pad_set(CPAD_Commands.CPADRIGHT,
                                       math.sin(i))
                self.ir.circle_pad_set(CPAD_Commands.CPADUP,
                                       math.cos(i))
                self.ir.send(print_sent=False)
                time.sleep(0.2)
            elif int(self.movevar.get()) == 1:
                # Talk to the pokemon
                self.ir.press(HIDButtons.A)
                self.ir.send(print_sent=False)
                time.sleep(0.1)
                self.ir.unpress(HIDButtons.A)
                self.ir.send(print_sent=False)
            img0 = self.image[1]
            img1 = self.image[1].crop((35,205,235,218))
            res = matchtemplate(img2BW(img1), self.ap, 13, 200-24)
            #print(res)
            if res < self.threshold:
                t_app = time.time()
                #print("Found app!")
                for j in range(100):
                    img2 = self.image[1].crop((13,203,33,215))
                    res = matchtemplate(img2BW(img2), self.go, 12, 0)
                    if res < self.threshold:
                        t_go = time.time()
                        #print("Found go!")
                        t_use = int((t_go - t_app)*1000)
                        return t_use, img0
                    time.sleep(0.1)
        return 0.0, img0

    def main_procedure(self):
        # Start Shiny Hunting
        while True:
            # Check if it is shiny
            t_use, img0 = self.findtime()
            self.ir.clear_everything()
            self.ir.circle_pad_neutral()
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            self.msgbox.MsgAppend(
                            ('Encounter %04d' % self.General.start_count) +
                             ' - ' + current_time + ' - ' +
                            ('%i msec' % t_use) )
            # Update the counter and plus one
            self.General.CounterPlusOne()
            
            if t_use == 0.0:
                try:
                    # Test if 3DS is still alive
                    self.General.test3DS()
                except:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.msgbox.MsgAppend(
                        ('Encounter %04d' % self.General.start_count) +
                         ' - N3DS crush?' )
                    break
            if t_use > self.chat:
                img0.save(self.General.shotpath +
                          '/' + ('%04d' % self.General.start_count) +'.jpg')
                self.ir.return_control()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'yellow')
                self.msgbox.MsgAppend('Shiny hunt completed!')
                break
            # Game soft reset
            for i in range(2):
                self.ir.press(HIDButtons.L)
                self.ir.press(HIDButtons.R)
                self.ir.press(HIDButtons.SELECT)
                self.ir.send(print_sent=False)
                time.sleep(0.1)
            self.ir.clear_everything()
            # Enter the game
            for i in range(30):
                self.ir.press(HIDButtons.A)
                self.ir.send(print_sent=False)
                time.sleep(0.2)
                self.ir.unpress(HIDButtons.A)
                self.ir.send(print_sent=False)
                time.sleep(0.2)
            if str(self.General.ConnectButton['relief']) == 'raised':
                self.General.ConnectState(-1)
                self.ir.return_control()
                break

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[1][i]['move']    = int(self.movevar.get())
        self.General.data[1][i]['aura']    = int(self.auravar.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.movevar.set(int(self.General.data[1][i]['move']))
        self.auravar.set(int(self.General.data[1][i]['aura']))
        self.auraswitch()


