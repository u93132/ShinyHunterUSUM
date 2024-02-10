import tkinter.font as tkfont
import os, re, sys

# Get rid of system language issues
def FindFont():
    FontSet=tkfont.families()
    if 'Microsoft JhengHei UI' in tkfont.families():
        return 'Microsoft JhengHei UI'
    elif 'Microsoft Sans Serif' in tkfont.families():
        return 'Microsoft Sans Serif'
    else:
        return 'calibri'

# Make a regular expression
# for validating an Ip-address
regex = ('^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}' +
         '(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$')
 
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
            except:
                raise Exception("Invalid IP")

# Convert 4bytes int to a little endian string
def i2L(x):
    return ''.join([hex(x)[2:][i] for i in (2,3,0,1)])


# Image data compression to have better analyze performance
# output: 1-D list with gray scale information
def img2BW(img):
    img = img.convert('L').rotate(90, expand=True)
    pixels = list(img.getdata())
    width, height = img.size
    return [pixels[i * width + j] for i in range(height)
                                  for j in range(width)]

# Image data compression to have better analyze performance
# output: average RGB of a given block
def img2avRGB(img):
    img = img.convert('RGB').rotate(90, expand=True)
    pixels = list(img.getdata())
    width, height = img.size
    temp = [pixels[i * width + j] for i in range(height)
                                  for j in range(width)]
    R = sum([i[0] for i in temp])/width/height
    G = sum([i[1] for i in temp])/width/height
    B = sum([i[2] for i in temp])/width/height
    return [R,G,B]

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
    # Get absolute path to resource, works for dev and for PyInstaller
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
