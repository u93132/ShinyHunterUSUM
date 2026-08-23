import tkinter as tk
import time, math
from PIL import Image
from datetime import datetime
from functions import *
from tppflush import *
from tabBase import TabBase, HuntStopped

# Define the application class
class Battle(TabBase):
    tabname   = 'Battle'
    threshold = 0.10    # for image identification
    logname   = 'Encounter'
    linger    = 15.0    # the battle intro runs long: keep streaming

    def __init__(self, nb, General, msgbox, image):

        #########################################################################
        ############################## Initialize  ##############################
        #########################################################################

        super().__init__(nb, General, msgbox, image)
        # Battle parameters
        self.ap   = img2BW(Image.open(self.picpath/'ap.bmp'))
        self.go   = img2BW(Image.open(self.picpath/'go.bmp'))
        self.chat = 2700           # 2700ms for normal pokemon

        self.cropbox_ap = [(35,205,235,218),(35,198,235,211)]
        self.cropbox_go = [(13,203,33,215), (11,196,31,208)]

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
            self.movebtn[i].config(command=self.auraswitch)
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

        # Hint line for the current Trigger/Type combination
        self.desclist = {
            (0, 0): 'Legendaries in Ultra wormholes/\nnormal grass encounter.',
            (0, 1): 'Stakataka and Blacephalon',
            (1, 0): 'No Pokemons belong here.',
            (1, 1): 'Ultra beasts in Ultra wormholes.',
        }
        self.desclab = tk.Label(self.frame, anchor='w', justify='left',
                                wraplength=230)
        self.desclab.grid(row=2, column=0, columnspan=3,
                          padx=3, pady=2, sticky='w')
        self.descswitch()

    #############################################################################
    ############################### Functions ###################################
    #############################################################################

    def auraswitch(self):
        if int(self.auravar.get()) == 0:
            # 2700ms for no aura pokemon
            if int(self.movevar.get()) == 0:
                self.chat = 2700
            else:
                self.chat = 2200
        elif int(self.auravar.get()) == 1:
            # 8600ms for aura pokemon
            self.chat = 8500
        self.descswitch()

    def descswitch(self):
        # Update the hint line to match the Trigger/Type combination
        self.desclab.config(
            text=self.desclist[(int(self.movevar.get()),
                                int(self.auravar.get()))])

    def findtime(self,gametype):
        # Return (result, screenshot when the pokemon appears)
        # float result: the time between 'appear' and 'Go!' in msec
        # int   result: 101 = they never appeared (error)
        if int(self.auravar.get()) == 0:
            # no aura pokemon
            n = 150
        elif int(self.auravar.get()) == 1:
            # aura pokemon
            n = 350
        for i in range(n):
            if int(self.movevar.get()) == 0:
                # Move around
                self.cpad(0, math.cos(i))
                time.sleep(0.2)
            elif int(self.movevar.get()) == 1:
                # Talk to the pokemon
                self.click(HIDButtons.A)
            img0 = self.image[1]
            img1 = img0.crop(self.cropbox_ap[gametype-1])
            res = matchtemplate(img2BW(img1), self.ap, 13, 200-24)
            #print(res)
            if res < self.threshold:
                t_app = time.time()
                #print("Found app!")
                for j in range(100):
                    img2 = self.image[1]
                    img3 = img2.crop(self.cropbox_go[gametype-1])
                    res = matchtemplate(img2BW(img3), self.go, 12, 0)
                    if res < self.threshold:
                        t_go = time.time()
                        #print("Found go!")
                        t_use = (t_go - t_app)*1000
                        return t_use, img0
                    time.sleep(0.1)
        return 101, img0

    def hunt(self, gametype=0):
        # Check Pokemon game version and update self.chat
        if gametype == 2:
            self.chat = 2200
            if not (int(self.movevar.get()) == 0 and
                    int(self.auravar.get()) == 0):
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'red')
                self.msgbox.MsgAppend(
                    f'This function is not supported for S/M')
        else:
            self.auraswitch()
        # Start Shiny Hunting
        while True:
            # Check if it is shiny
            t_use, img0 = self.findtime(gametype)
            self.ir.clear_everything()
            self.ir.circle_pad_neutral()
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            if isinstance(t_use, int):
                try:
                    # Test if 3DS is still alive
                    self.General.test3DS()
                except OSError:
                    self.General.ConnectState(0)
                    self.General.ConnectState(-1)
                    self.msgbox.msgbox.config(bg = 'red')
                    self.msgbox.MsgAppend(
                        f'Encounter {self.General.start_count:04d}'
                        ' - N3DS crush?' )
                    break
                else:
                    if self.General.debugshot:
                        combine_images(self.image).save(
                          self.General.shotpath /
                          f'Debug_Encounter_'
                          f'{self.General.lockedslot or 0}_'
                          f'{self.General.start_count:04d}_'
                          f'{t_use:03d}.jpg')
                    self.msgbox.MsgAppend(
                        f'Encounter {self.General.start_count:04d}'
                        f' - {current_time} - Error {t_use:03d}')
            else:
                # Check the result, res close to 0 means shiny
                self.msgbox.MsgAppend(
                    f'Encounter {self.General.start_count:04d}'
                    f' - {current_time} - {int(t_use)} msec' )
            if t_use > self.chat:
                img0.save(self.General.shotpath /
                          f'Encounter_{self.General.lockedslot or 0}_'
                          f'{self.General.start_count:04d}.jpg')
                # Let the shiny play on for the recorder's tail
                time.sleep(self.linger)
                self.ir.return_control()
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
                self.msgbox.msgbox.config(bg = 'yellow')
                self.msgbox.MsgAppend('Shiny hunt completed!')
                break
            # Update the counter and plus one
            self.General.CounterPlusOne()
            # Game soft reset and re-enter
            self.restart_game()

    def GUI2data(self, i):
        # For each tab, GUI to setting data struct
        self.General.data[i].move = int(self.movevar.get())
        self.General.data[i].aura = int(self.auravar.get())

    def data2GUI(self, i):
        # For each tab, setting data struct to GUI
        self.movevar.set(int(self.General.data[i].move))
        self.auravar.set(int(self.General.data[i].aura))
        self.auraswitch()


