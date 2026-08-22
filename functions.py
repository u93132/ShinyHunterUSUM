import tkinter as tk
import tkinter.font as tkfont
import io, re, sys, struct
from pathlib import Path
from PIL import Image, ImageStat, ImageTk

# Get rid of system language issues
def FindFont():
    families = tkfont.families()
    for name in ('Microsoft JhengHei UI', 'Microsoft Sans Serif'):
        if name in families:
            return name
    return 'calibri'

# Make a regular expression
# for validating an Ip-address
regex = (r'^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}'
         r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$')
 
# Define a function for
# validate an Ip address with or without port number
def check(Ip): 
    # pass the regular expression
    # and the string in search() method
    Ip = Ip.split(':')
    if not (re.search(regex, Ip[0])):
        raise Exception("Invalid IP")
    else:
        if len(Ip) > 1:
            try:
                int(Ip[1])
            except ValueError:
                raise Exception("Invalid IP")

# Convert a 16-bit int (e.g. port number) to a little-endian hex string
def i2L(x):
    return x.to_bytes(2, 'little').hex()


# Image data compression to have better analyze performance
# output: 1-D list with gray scale information
def img2BW(img):
    # getdata() already yields pixels row by row
    return list(img.convert('L').rotate(90, expand=True).getdata())

# Invert a grayscale template (img2BW output): white-on-black
# becomes black-on-white, for matching inverted dialog styles
def invertBW(bw):
    return [255 - v for v in bw]

# Image data compression to have better analyze performance
# output: average RGB of a given block
def img2avRGB(img):
    return ImageStat.Stat(img.convert('RGB')).mean

def diffnorm(a,b):
    return sum([(i-j)**2 for i, j in zip(a, b)])**0.5

# Find if one image appears in a larger image
# (the height has to be the same)
# output: a normalized number, smaller number means highly match
def matchtemplate(img_r, img_t, h_t, w_diff):
    res   = 10.0
    left  = 0
    right = len(img_t)
    for i in range(w_diff + 1):
        res_iter = [abs(a-b) for a, b in zip(img_r[left:right], img_t)]
        res_iter = sum(res_iter)/len(img_t)/255.0
        left  = left  +h_t
        right = right +h_t
        res = min(res, res_iter)
    return res


# For check whether script is in IDLE or Pyinstaller
def resource_path(relative_path):
    # PyInstaller unpacks bundled data files under sys._MEIPASS
    return Path(getattr(sys, '_MEIPASS', '.')) / relative_path

# Load every image in a folder into tk-compatible objects
# gif -> tk.PhotoImage (animation-capable)
# ico -> skipped (window icon, loaded separately)
def load_bitmaps(folder):
    bitmap = {}
    for p in resource_path(folder).iterdir():
        if not p.is_file() or p.suffix.lower() == '.ico':
            continue
        if p.suffix.lower() == '.gif':
            bitmap[p.stem] = tk.PhotoImage(file=str(p))
        else:
            bitmap[p.stem] = ImageTk.PhotoImage(Image.open(p))
    return bitmap

# One RIFF chunk: fourcc + size + data, padded to an even length
def _chunk(fourcc, data):
    if len(data) % 2:
        data += b'\x00'
    return fourcc + struct.pack('<I', len(data)) + data

def _list(fourcc, data):
    return _chunk(b'LIST', fourcc + data)

# Write an MJPEG AVI video: the stream's JPEG frames go into the
# container unchanged, so the picture quality is exactly the stream's
# and no codec library is needed. All frames must share `size`.
def write_avi(path, frames, size, fps):
    w, h  = size
    rate  = max(1, round(fps * 1000))   # frame rate = rate / scale
    scale = 1000
    n      = len(frames)
    maxbuf = max(len(f) for f in frames)
    avih = struct.pack('<14I',
        round(1e6 * scale / rate),      # microseconds per frame
        maxbuf * rate // scale,         # max bytes per second
        0, 0x10,                        # padding; flags: has index
        n, 0, 1, maxbuf, w, h,          # frames, streams, buffer, size
        0, 0, 0, 0)
    strh = struct.pack('<4s4sIHHIIIIIIII4h',
        b'vids', b'MJPG', 0, 0, 0, 0,
        scale, rate, 0, n, maxbuf,
        0xFFFFFFFF, 0,                  # default quality
        0, 0, w, h)
    strf = struct.pack('<IiiHH4sIiiII',
        40, w, h, 1, 24, b'MJPG', w * h * 3, 0, 0, 0, 0)
    hdrl = _list(b'hdrl', _chunk(b'avih', avih) +
                 _list(b'strl', _chunk(b'strh', strh) +
                                _chunk(b'strf', strf)))
    movi, idx1 = [], []
    offset = 4                          # from the 'movi' fourcc
    for f in frames:
        ck = _chunk(b'00dc', f)
        movi.append(ck)
        idx1.append(struct.pack('<4sIII', b'00dc', 0x10,
                                offset, len(ck) - 8))
        offset += len(ck)
    body = (hdrl + _list(b'movi', b''.join(movi)) +
            _chunk(b'idx1', b''.join(idx1)))
    with open(path, 'wb') as f:
        f.write(_chunk(b'RIFF', b'AVI ' + body))

# Re-iterable frame sequence: PIL's PNG writer walks append_images
# twice (a mode scan, then the frame write), which would exhaust a
# plain generator after the first pass. Each pass builds one frame
# at a time through `make`, so memory stays flat
class _Frames:
    def __init__(self, items, make):
        self.items = items
        self.make  = make

    def __iter__(self):
        return (self.make(x) for x in self.items)

# Write an animated GIF or APNG (fmt 'GIF' / 'PNG'): make(item)
# turns each buffered item into a PIL image; durations are per
# frame in milliseconds. RGBA frames keep their alpha in APNG
def write_anim(path, items, make, durations, fmt):
    first = make(items[0])
    first.save(path, fmt, save_all=True,
               append_images=_Frames(items[1:], make),
               duration=durations, loop=0)

# JPEG and GIF carry no alpha: flatten an RGBA frame onto white
def flatten(img):
    if img.mode == 'RGB':
        return img
    base = Image.new('RGB', img.size, 'white')
    base.paste(img, mask=img.getchannel('A'))
    return base

# Combine images horizontally
def combine_images(image_list):
    # 1. Calculate the dimensions of the final canvas
    total_width = sum(img.width for img in image_list)
    max_height = max(img.height for img in image_list)
    
    # 2. Create a blank canvas (matching the mode of the first image)
    combined_image = Image.new(image_list[0].mode, (total_width, max_height))
    
    # 3. Paste each image sequentially
    current_x = 0
    for img in image_list:
        combined_image.paste(img, (current_x, 0))
        current_x += img.width  # Shift right for the next image
        
    return combined_image
