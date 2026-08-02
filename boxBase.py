import tkinter as tk

class ToolTip:
    # Hover hint for a widget: shows after a short delay, hides on
    # leave or click
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text   = text
        self.delay  = delay
        self.tip    = None
        self.after_id = None
        widget.bind('<Enter>', self.schedule)
        widget.bind('<Leave>', self.hide)
        widget.bind('<ButtonPress>', self.hide)

    def schedule(self, event=None):
        self.after_id = self.widget.after(self.delay, self.show)

    def show(self):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)   # no window frame
        self.tip.wm_geometry(f'+{x}+{y}')
        tk.Label(self.tip, text=self.text, bg='lightyellow',
                 relief='solid', borderwidth=1, padx=4).pack()

    def hide(self, event=None):
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None

class InputBox:
    def __init__(self, frame, mode, Text1, Text2, WidthList):
        self.frame=frame
        self.Text1=Text1
        self.Text2=Text2
        self.WidthList=WidthList

        self.Label1=tk.Label(self.frame, text=self.Text1)
        self.Entry=tk.Entry(self.frame)
        
        self.Label1.config(width=self.WidthList[0], anchor='w')
        self.Entry.config(width=self.WidthList[1])

        self.Label1.pack(padx=0, pady=0, side='left', fill='both')
        self.Entry.pack(padx=0, pady=0, side='left')

        self.Label2=tk.Label(self.frame, text=self.Text2)
        self.Label2.config(width=self.WidthList[2])
        self.Label2.pack(padx=5, pady=0, side='left')

class msgBox:
    def __init__(self, frame, w, h):
        self.message = ['']
        self.scroll = tk.Scrollbar(frame, orient='vertical')
        self.msgbox = tk.Text(frame, width = w, height = h,
                              yscrollcommand=self.scroll.set)
        self.scroll.config(command=self.msgbox.yview)
        self.msgbox.pack(padx=0, pady=10, side='left')
        self.scroll.pack(pady=10, side='left', fill='y')
    
    def MsgDisplay(self):
        string = ''
        self.msgbox.delete(1.0 , tk.END)
        if self.message != ['']:
            for i in range(len(self.message)):
                string = string+self.message[i]+'\n'
            self.msgbox.insert(tk.END,string)
        self.msgbox.see('end')

    def MsgAppend(self,s):
        if self.message[0] == '':
            self.message[0] = s
        else:
            self.message.append(s)
        # Keep only 500 lines in the message box 
        if len(self.message) > 500:
            self.message.pop(0)
        self.MsgDisplay()
