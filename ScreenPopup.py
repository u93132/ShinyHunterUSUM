import re
import tkinter as tk
from PIL import ImageTk
from Record import N3DS_BOX
from functions import resource_path

# Win32 window-style bits: keep the title bar (so window capture and
# the taskbar see it reliably) but disable everything it can do
_GWL_STYLE     = -16
_GWL_EXSTYLE   = -20
_WS_THICKFRAME  = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_WS_EX_APPWINDOW  = 0x00040000
_WS_EX_TOOLWINDOW = 0x00000080
_SWP_FRAMECHANGED = 0x0027   # FRAMECHANGED|NOMOVE|NOSIZE|NOZORDER
# System-menu commands to grey out, so the title bar controls do nothing
_SC_SIZE = 0xF000
_SC_MOVE = 0xF010
_SC_MINIMIZE = 0xF020
_SC_MAXIMIZE = 0xF030
_SC_CLOSE    = 0xF060
_SC_RESTORE  = 0xF120
_MF_DISABLE = 0x0000 | 0x0001 | 0x0002   # BYCOMMAND|GRAYED|DISABLED

# Plain background: upper (400) over lower (320), both centred
PLAIN_POS  = {1: (0, 0), 0: (40, 240)}
PLAIN_SIZE = (400, 480)

class ScreenPopup:
    # A titled-but-locked window that mirrors the live screens and
    # follows the main window. It renders in layers on a Canvas: the console
    # picture is a static background drawn once, the two screens are
    # fixed-position items refreshed on their own loop. The app owns
    # the persistent options (pop_form / pop_scale); this class is the
    # view and writes option changes back to the app.
    def __init__(self, app):
        self.app = app
        self.alive = True             # drives the refresh loop
        self.photo = [None, None]     # PhotoImage refs, per screen
        self.item  = [None, None]     # canvas item ids, per screen
        self.id    = [None, None]     # last drawn frame id, per screen
        self.console_photo = None
        self.win = tk.Toplevel(app)
        self.win.withdraw()               # hidden while it is restyled
        self.win.resizable(False, False)
        self.win.title('Screen')
        self.win.iconbitmap(bitmap=str(resource_path('image0/star.ico')))
        # The popup is controlled only by the undock button; deny
        # taskbar / Alt+F4 closes so it can never be orphaned while
        # the app still thinks it is open
        self.win.protocol('WM_DELETE_WINDOW', self.deny_close)
        # Position tracked in geometry space (self.x, self.y): start on
        # the main window's right, then shift by the main window's own
        # moves so the relative distance is kept - even after a drag
        self.app.update_idletasks()
        self.x = self.app.winfo_x() + self.app.winfo_width() + 8
        self.y = self.app.winfo_y()
        self.win.bind('<Configure>', self.on_configure)
        # Toolbar on top: background picker on the left, size group
        # right after it; buttons within each group are flush
        self.toolbar = tk.Frame(self.win)
        self.toolbar.pack(fill='x')
        icons = ('image', 'redconsole', 'blueconsole')
        for f in range(3):
            tk.Button(self.toolbar, image=app.Record.bitmap[icons[f]],
                      command=lambda f=f: self.set_form(f)
                      ).pack(side='left', padx=0, pady=2)
        self.sizebox = tk.Frame(self.toolbar)
        self.sizebox.pack(side='left', padx=(3, 0))
        tk.Button(self.sizebox, image=app.bitmap['oneicon'],
                  command=lambda: self.set_scale(1.0)
                  ).pack(side='left', padx=0, pady=2)
        tk.Button(self.sizebox, image=app.bitmap['halficon'],
                  command=lambda: self.set_scale(0.5)
                  ).pack(side='left', padx=0, pady=2)
        self.canvas = tk.Canvas(self.win, bg='black', highlightthickness=0)
        self.canvas.pack()
        self.w = self.h = 0               # last measured window size
        self.lock_window()                # neuter the title bar first
        self.rebuild()                    # lay out, measure, pin size
        self.win.deiconify()
        self.tick()

    def lock_window(self):
        # Keep the title bar (so Discord / OBS window capture and the
        # taskbar see the window reliably) but disable everything it
        # can do: no minimize / maximize / snap / resize, and the
        # system-menu commands (Move / Size / Close / ...) greyed out.
        # The window can only be toggled by the undock button
        try:
            import ctypes
            u = ctypes.windll.user32
            self.win.update_idletasks()
            hwnd = u.GetParent(self.win.winfo_id())
            style = u.GetWindowLongW(hwnd, _GWL_STYLE)
            style &= (~_WS_THICKFRAME & ~_WS_MINIMIZEBOX
                      & ~_WS_MAXIMIZEBOX)
            u.SetWindowLongW(hwnd, _GWL_STYLE, style)
            ex = u.GetWindowLongW(hwnd, _GWL_EXSTYLE)
            ex = (ex | _WS_EX_APPWINDOW) & ~_WS_EX_TOOLWINDOW
            u.SetWindowLongW(hwnd, _GWL_EXSTYLE, ex)
            u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, _SWP_FRAMECHANGED)
            menu = u.GetSystemMenu(hwnd, False)
            if menu:
                for cmd in (_SC_SIZE, _SC_MOVE, _SC_MINIMIZE,
                            _SC_MAXIMIZE, _SC_CLOSE, _SC_RESTORE):
                    u.EnableMenuItem(menu, cmd, _MF_DISABLE)
        except Exception:
            pass   # non-Windows: a plain titled window is fine

    def set_form(self, f):
        # Switch the background; the app owns the option
        self.app.pop_form = f
        self.rebuild()

    def set_scale(self, s):
        # Full (1.0) or half (0.5) size; the app owns the option
        self.app.pop_scale = s
        self.rebuild()

    def rebuild(self):
        # Lay out the canvas for the current background and size: draw
        # the console once (if any), then create the two screen items
        # at their fixed, scaled positions on top
        c = self.canvas
        c.delete('all')
        self.item = [None, None]
        self.id   = [None, None]
        s = self.app.pop_scale
        if self.app.pop_form:
            console = self.app.Record.n3ds[self.app.pop_form - 1]
            cw, ch = console.size
            if s != 1.0:
                console = console.resize((round(cw * s), round(ch * s)))
            self.console_photo = ImageTk.PhotoImage(console)
            c.config(width=round(cw * s), height=round(ch * s))
            c.create_image(0, 0, anchor='nw', image=self.console_photo)
            pos = {0: N3DS_BOX[0], 1: N3DS_BOX[1]}
        else:
            self.console_photo = None
            c.config(width=round(PLAIN_SIZE[0] * s),
                     height=round(PLAIN_SIZE[1] * s))
            pos = PLAIN_POS
        for scr in (0, 1):
            x, y = pos[scr]
            self.item[scr] = c.create_image(round(x * s), round(y * s),
                                            anchor='nw', state='hidden')
        # Measure the size the content needs and pin the window to it
        self.win.update_idletasks()
        self.w = self.win.winfo_reqwidth()
        self.h = self.win.winfo_reqheight()
        self.apply()

    def tick(self):
        # Refresh only the screen layer (~10/s); the console stays put.
        # Guard on our own flag, not app.popup, because the very first
        # tick runs from __init__ before app.popup has been assigned
        if not self.alive:
            return
        sel = self.app.SelScreens()
        s = self.app.pop_scale
        for scr in (0, 1):
            item = self.item[scr]
            orig = self.app.image[scr]
            if scr in sel and orig is not None:
                if id(orig) != self.id[scr]:
                    draw = orig if s == 1.0 else orig.resize(
                        (round(orig.width * s), round(orig.height * s)))
                    photo = ImageTk.PhotoImage(draw)
                    self.canvas.itemconfigure(item, image=photo,
                                              state='normal')
                    self.photo[scr] = photo
                    self.id[scr] = id(orig)
                else:
                    self.canvas.itemconfigure(item, state='normal')
            else:
                self.canvas.itemconfigure(item, state='hidden')
        self.app.after(100, self.tick)

    def apply(self):
        # Pin the window to (self.x, self.y) at its measured size. An
        # explicit WxH stops a frame recalc (taskbar Move) resizing it
        self.win.geometry(f'{self.w}x{self.h}+{self.x}+{self.y}')

    def _geo(self):
        # Current window position parsed from its geometry string -
        # the same space apply() writes in, so reads and writes match
        m = re.search(r'([+-]\d+)([+-]\d+)$', self.win.geometry())
        return (int(m.group(1)), int(m.group(2))) if m else (self.x,
                                                             self.y)

    def on_configure(self, event=None):
        # The window moved: if the WM (a user drag) put it somewhere
        # other than where apply() last set it, adopt that position so
        # the popup keeps its new relative distance. Compared in
        # geometry space, so our own placements match and never drift
        if not self.alive or (event is not None and
                              event.widget is not self.win):
            return
        gx, gy = self._geo()
        if (gx, gy) != (self.x, self.y):
            self.x, self.y = gx, gy

    def follow(self, dx, dy):
        # The main window moved by (dx, dy); shift the popup the same,
        # keeping its current relative distance wherever it now sits
        self.x += dx
        self.y += dy
        self.apply()

    def deny_close(self):
        # Ignore window-manager close requests (taskbar, Alt+F4);
        # only the app's undock toggle may close the popup
        pass

    def close(self):
        self.alive = False       # stop the refresh loop first
        self.win.destroy()
