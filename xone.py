#!/usr/bin/python3
import time
time.sleep(3)
import traceback
import mido
import sys
from math import ceil
import msvcrt
from copy import deepcopy

virtualPorts = mido.Backend('mido.backends.tevirtualmidi')
#rbox = virtualPorts.open_ioport("PIONEER DDJ-SX", virtual=True)
#virt = virtualPorts.open_ioport("DDJ-400", virtual=True)

rtmidi = mido.Backend("mido.backends.rtmidi")
last_xone = time.time()
layer=0
fxchan=0

# 0 = never, 1 = when not in hotcue, 2 = always
VU_ON=1

DBG=True
PITCHBEND=False

# layer numbers
HOTCUE=1
BEATJUMP=0
BEATLOOP=2  # not used

VU_NEVER=0
VU_BEATJUMP=1
VU_ALWAYS=2

def prn(*args):
    if DBG:
        print(*args)

def prn2(*args):
    if DBG == 2:
        print(*args)

# find a midi device by name
def find_port(name, out=True):
    prn("Enumerating names")
    if out:
        names = rtmidi.get_output_names()
    else:
        names = rtmidi.get_input_names()
    prn(names)
    
    for n in names:
        if name in n:
            prn("Found %s (out=%s)"%(n,out))
            if out:
                return rtmidi.open_output(n)
            else:
                return rtmidi.open_input(n)
            
    raise Exception("Couldn't find %s (out=%s)" % (name,out))

def find_port_safe(name, out=True):
    while True:
        try:
            return find_port(name, out)
        except Exception as e:
            print(e)
            time.sleep(1)

xone_in = find_port_safe("XONE", False)    
xone = find_port_safe("XONE", True)    
rbox_in = find_port_safe("Internal", False)
rbox = find_port_safe("Internal", True)

DBG=False


# [shift][layer] = channel
layer2chan = {False: {0: 14, 1:12}, True: {0: 13, 1:11}}
# [channel] = (shift, layer)
chan2layer = {11:(True, 1), 12:(False, 1), 13:(True, 0), 14:(False, 0)}

#red + yell + green
# + 24 + 24
# Buttons to always be a certain color
yellows = [45,46]
greens = [41,42]
class Deck:
    def __init__(self, n):
        self._n = n
        self._loaded = False
        self._onair = False
        self._warn = False
        self._vu = 0
        self._pos = 0
        self._lastpos = 0
        self._lastplay = 0
        self._vu_pads = [0,0,0,0]
    def loaded(self, val):
        self._loaded = val
        self.update_loaded()
    def onair(self, val):
        self._onair = val
        self.update_loaded()
    def update_loaded(self):
        n=0x35+self._n
        v=0
        t="note_on"
        if self._loaded:
            v=127
            n+=72
        elif self._onair:
            v=127
        else:
            t="note_off"
        xone.send(mido.Message(type=t, channel=14, note=n, velocity=v))
    def warn(self, val):
        self._warn = val
        xone.send(mido.Message(type="note_on", channel=14, note=0x34+self._n*3, velocity=val))
    #25 29 33 37
    def vu(self, val):
        self._vu = val
        if VU_ON == VU_NEVER or (VU_ON == VU_BEATJUMP and layer == BEATJUMP): return
        p = vu_mapping_1[val]
        if p>0: p += 1
        m = vu_mapping_2[p]
        prn(val," > ",p," > ",m)
        for i in range(0,4):
            note = m[i]
            velocity=127
            t = "note_on"
            if note<0 and self._vu_pads[i]:
                self._vu_pads[i] = 0
                velocity=0
                note = note * -1
                note += self._n
                t = "note_off"
                msg=mido.Message(type=t, channel=14, note=note, velocity=velocity)
                prn(msg)
                xone.send(msg)
            elif note>0:
                self._vu_pads[i] = 1
                note += self._n
                msg=mido.Message(type=t, channel=14, note=note, velocity=velocity)
                prn(msg)
                xone.send(msg)

    def pos(self, val):
        self._pos = val
        self._lastpos = time.time()
    def play(self, val):
        if not val:
            self._lastplay = time.time()
    def playing(self):
        if time.time() - self._lastplay < 1.1:
            return False
        else:
            return True




# maps data sent from hotcue note to 3 colors on xone
#0,1,2=red,yel,grn
pad_mapping = {
        49:1, 56:1, 60:1, 62:1, 
        1:1, 5:1, 9:1, 14:1, 
        18:1, 22:2, 26:0, 30:0, 
        34:0, 39:0, 42:0, 45:0, 
        37:0, # loop
        }
# maps the 11 values sent for channel level
# to the 12 possible values for LEDs
vu_mapping_1 = \
{
0: 0,
43: 1,
50: 2,
65: 3,
72: 4,
80: 5,
87: 7,
94: 8,
101: 9,
108: 10,
119: 11,
127: 12,
}

# maps out 12 possible VU states
# negative sends a note_off command
# the pads fill up with green, then orange, then red 
#0=red, +36=orange, +72=green
# C#1 C#4 C#7
# 25 61 97
# C#1 F1 A1 C#2
# 25 29 33 37
R=0
Y=36
G=72
vu_mapping_2 = [
        [-25-R, -29-R, -33-R, -37-R],
        [25+G, -29-R, -33-R, -37-R],
        [25+Y, -29-R, -33-R, -37-R],
        [25+R, -29-R, -33-R, -37-R],
        [25+R, 29+G, -33-R, -37-R],
        [25+R, 29+Y, -33-R, -37-R],
        [25+R, 29+R, -33-R, -37-R],
        [25+R, 29+R, 33+G, -37-R],
        [25+R, 29+R, 33+Y, -37-R],
        [25+R, 29+R, 33+R, -37-R],
        [25+R, 29+R, 33+R, 37+G],
        [25+R, 29+R, 33+R, 37+Y],
        [25+R, 29+R, 33+R, 37+R],
        ]

# alternative mapping, not used
vu_mapping_2b = [
        [-25-G, -29-G, -33-G, -37-G],
        [25+G, -29-G, -33-G, -37-G],
        [25+G, 29+G, -33-G, -37-G],
        [25+G, 29+G, 33+G, -37-G],
        [25+G, 29+G, 33+G, 37+G],
        [25+Y, 29+G, 33+G, 37+G],
        [25+Y, 29+Y, 33+G, 37+G],
        [25+Y, 29+Y, 33+Y, 37+G],
        [25+Y, 29+Y, 33+Y, 37+Y],
        [25+R, 29+Y, 33+Y, 37+Y],
        [25+R, 29+R, 33+Y, 37+Y],
        [25+R, 29+R, 33+R, 37+Y],
        [25+R, 29+R, 33+R, 37+R],
]
decks = [Deck(0),Deck(1)]
def handle_rbox(msg):
    if msg.type == "sysex":
        return
    prn2("RB",msg," = ",msg.hex())
    if msg.type == "control_change":
        if msg.channel == 0:
            if msg.control == 2:
                decks[0].vu(msg.value)
        if msg.channel == 1:
            if msg.control == 2:
                decks[1].vu(msg.value)
        if msg.channel == 11: 
            if msg.control == 0:
                decks[0].pos(msg.value)
            if msg.control == 1:
                decks[1].pos(msg.value)
            if msg.control == 4:
                decks[0].onair(msg.value)
            if msg.control == 5:
                decks[1].onair(msg.value)
    if msg.type == "note_on":
        # Ignore FX assign button, as we handle the color of that internally
        if msg.note == 47:
            return
        
        # Keep track of deck playing
        if msg.note == 41:
            decks[0].play(msg.velocity == 127)
        if  msg.note == 42:
            decks[1].play(msg.velocity == 127)

        # ignore layer change
        if msg.note == 15:
            return

        # keep track of load/warning status
        if msg.channel == 11:
            if msg.note == 0:
                decks[0].loaded(msg.velocity)
            if msg.note == 1:
                decks[1].loaded(msg.velocity)
            if msg.note == 4:
                decks[0].warn(msg.velocity)
            if msg.note == 5:
                decks[1].warn(msg.velocity)

        # Buttons that should always be a certain color
        if msg.note in yellows:
            msg.note += 36
        if msg.note in greens:
            msg.note += 72

        # handle the bottom button grid
        if ((msg.note >= 24 and msg.note <= 39)) and msg.channel in ledcache.keys():
            # cache their color, so we can display it later if we're on a diff layer
            ledcache[msg.channel][msg.note] = msg.velocity

            if msg.channel in chan2layer:
                s2, l2 = chan2layer[msg.channel]
                if l2 == layer:
                    msg.channel = 14
                    if l2 == BEATJUMP: #backwards
                        # Convert from many hotcue colors to the 3 xone colors (diff note per color)
                        print("Cue",msg.note,msg.velocity)
                        if msg.velocity in pad_mapping:
                            msg.note += 36 * pad_mapping[msg.velocity]
                            msg.velocity = 127
                        else: 
                            # default color is yellow
                            print("color not found: %d"%msg.velocity)
                            msg.note += 36
                    elif l2 == HOTCUE: #backwards
                        # beatjump always green btns
                        msg.note += 72
                else:
                    return
                prn2(s2, l2, layer)

    prn2(" "*20+"<<",msg," = ",msg.hex())
    try:
        xone.send(msg)
    except:
        prn("XONE exception sending")
        recon()

ledcache = {}
for c in 11,12,13,14:
    ledcache[c] = {}
    for n in range(24,40):
        ledcache[c][n] = 0


# Whenever we change layers, update all the button lights to their cached state
def update_layer_color():
    if layer == HOTCUE:
        xone.send(mido.Message(type="note_on", channel=14, note=0x0f))
    elif layer == BEATLOOP:
        xone.send(mido.Message(type="note_on", channel=14, note=0x13))
    elif layer == BEATJUMP:
        xone.send(mido.Message(type="note_on", channel=14, note=0x17))

    # if VU overrides hotcue, dont update
    if VU_ON == VU_ALWAYS: return

    chan = layer2chan[False][layer]
    for n,v in ledcache[chan].items():
        if v > 0:
            if layer == BEATJUMP:#backwards
                if v in pad_mapping:
                    n += 36 * pad_mapping[v]
                else:
                    n += 36
            if layer == HOTCUE:#backwards
                n += 72
            v = 127
            xone.send(mido.Message(type="note_on", channel=14, note=n, velocity=v))
        else:
            xone.send(mido.Message(type="note_off", channel=14, note=n, velocity=0))


# chan=14
# rotary = cc
# 0,1,2,3 top row
# 0 and 3
# left = 127, right = 1
shift = False
def handle_xone(msg):
    global last_xone,shift,layer,fxchan,PITCHBEND
    last_xone = time.time()
    skipshift=False
    dup=False
    prn("K2",msg," = ",msg.hex())
    # Handle Shift key internally
    if msg.type in ["note_on","note_off"] and msg.channel == 14 and msg.note == 12:
        shift = msg.velocity == 127
        xone.send(msg)
        return

    # Handle encoders, convert them to quick button presses
    # with a diff button for clock vs anti-clockwise turns
    if msg.type == 'control_change' and msg.channel == 14 and msg.control in [0,3]:
        # different control if shifting OR if the deck associated with the control is not playing
        # (so that we can beatjump while unshifted when deck is stopped)
        shifted=False
        cc = cc0 = msg.control
        if shift or (cc0==0 and not decks[0].playing()) or (cc0==3 and not decks[1].playing()):
            shifted=True
        if not PITCHBEND and not shifted:
            chan = 0 if cc == 0 else 1
            polarity = -15 if msg.value == 127 else 15
            msg = mido.Message(type="control_change", channel=chan, control=34, value=64+polarity)
            prn(" "*40+">>",msg," = ",msg.hex())
            rbox.send(msg)
        else:
            msg.channel = 0 if cc == 0 else 1
            cc = 0 if msg.value == 127 else 1
            msg = mido.Message(type="note_on", channel=msg.channel, note=cc, velocity=127)
            if shifted:
                msg.channel += 4
            
            rbox.send(msg)
            prn(" "*40+">>",msg," = ",msg.hex())
            msg.velocity = 0
            rbox.send(msg)
            prn(" "*40+">>",msg," = ",msg.hex())
        return

    # Convert "note_off" into "note_on" + velocity=0
    if msg.type == "note_off":
        m = msg.dict()
        m['type'] = "note_on"
        msg = mido.Message(**m)
        msg.velocity = 0

    # This button used for FX channel assign, cycles between 3 buttons
    # 0: 1 on --> initial state
    # 1: 1 off, 2 on --> 2 only
    # 2: 1 on --> 1+2
    # 3: 2 off --> 1 on
    if msg.type == "note_on" and msg.note == 47:
        def togglefx(c):
            msg.channel = 13 if c==2 else 14
            msg.velocity=127
            rbox.send(msg)
            prn(" "*40+">>",msg," = ",msg.hex())
            msg.velocity=0
            rbox.send(msg)
            prn(" "*40+">>",msg," = ",msg.hex())

        if msg.velocity > 0:
            if fxchan == 0:
                # 1 on -> 1 on
                togglefx(1)
                fxchan = 1
            elif fxchan == 1:
                # 1 off, 2 on -> 2 on
                togglefx(1)
                togglefx(2)
                fxchan = 2
            elif fxchan == 2:
                # 1 on --> 1+2 on
                togglefx(1)
                fxchan = 3
            elif fxchan == 3:
                # 2 off -> 1 on
                togglefx(2)
                fxchan = 1

            msg.channel = 14
            msg.note += (fxchan-1)*36
            msg.velocity=127
            xone.send(msg)
            prn(" "*40+"<<",msg," = ",msg.hex())

        return

    # Handle layer button
    l0 = layer
    if msg.type == "note_on" and msg.channel == 14 and msg.note == 15:
        skipshift=True # don't be affected by shift key
        dup = True # send two commands (so we can mirror it for both decks)
        if msg.velocity == 0:
            layer = (layer+1)%2
        update_layer_color()

    # If shifting, modify channel
    if shift and not skipshift:
        if msg.channel == 14:
            msg.channel = 13
        else:
            msg.channel += 4
    
    # Modify channel based on layer, for bottom buttons only
    if msg.type == "note_on" and ((msg.note >= 24 and msg.note <= 39) or msg.note==15):
        msg.channel -= l0*2

    rbox.send(msg)
    prn(" "*40+">>",msg," = ",msg.hex())

    # Duplicate some messages (so we can midi map to 2 commands in rbox)
    if dup:
        msg.channel-=1
        prn(" "*40+">>",msg," = ",msg.hex())
        rbox.send(msg)

def recon():
    global xone_in
    global xone
    try:
        xone_in.close()
    except:
        pass
    try:
        xone.close()
    except:
        pass
    ok = False
    while not ok:
        print("recon")
        time.sleep(1)
        try:
            xone_in = find_port("XONE", False)    
            xone_in.callback = handle_xone
        except:
            try:
                xone_in.close()
            except:
                pass
            continue
        try:
            xone = find_port("XONE", True)    
        except:
            try:
                xone.close()
            except:
                pass
            continue
        print("recon ok")
        ok = True

#def loop():
#    while True:
#        try:
#            handle_rbox(rbox.receive())
#        except:
#            prn("Err handling rbox")
#            prn(traceback.format_exc())
#            #recon()
#
#from threading import Thread
#t = Thread(target=loop, daemon=True)
#t.start()
#
update_layer_color()

#rbox.callback = handle_rbox
rbox_in.callback = handle_rbox
xone_in.callback = handle_xone
ping = mido.Message(type="note_on", channel=14, note=0, velocity=0)
tt = 0
while True:
    try:
        tt += 1
        if tt > 20:
            tt = 0
            xone.send(ping)
    except:
        recon()
    if msvcrt.kbhit():
        key = str(msvcrt.getch(), 'UTF-8')
        if key == "p":
            PITCHBEND = not PITCHBEND
            print(">> Pitch" if PITCHBEND else ">> Scratch")
        if key == "x":
            print(">>> Recon")
            recon()
            last_xone = time.time()
        if key == "q":
            print(">>> Quitting")
            break
        if key == "d":
            DBG = not DBG
            print(">>> Debug=",DBG)
        if key == "v":
            VU_ON = (VU_ON+1)%3
            labels = ['never', 'only in beatjump', 'always']
            print(">>> VU Meter: %s" % labels[VU_ON])
            update_layer_color()
    try:
        time.sleep(0.1)
    except:
        print("Exiting")
        break
rbox.close()
rbox_in.close()
xone.close()
xone_in.close()
#    try:
#        handle_xone(xone_in.receive())
#    except:
#        print("Err handling xone")
#        recon()

