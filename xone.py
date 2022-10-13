#!/usr/bin/python3
import traceback
import mido
import time
import sys
from math import ceil
import msvcrt

virtualPorts = mido.Backend('mido.backends.tevirtualmidi')
#rbox = virtualPorts.open_ioport("PIONEER DDJ-SX", virtual=True)
#virt = virtualPorts.open_ioport("DDJ-400", virtual=True)

rtmidi = mido.Backend("mido.backends.rtmidi")
last_xone = time.time()
layer=0

# 0 = never, 1 = when not in hotcue, 2 = always
VU_ON=1

DBG=False

def prn(*args):
    if DBG:
        print(*args)

# find a midi device by name
def find_port(name, out=True):
    print("Enumerating names")
    if out:
        names = rtmidi.get_output_names()
    else:
        names = rtmidi.get_input_names()
    print(names)
    
    for n in names:
        if name in n:
            print("Found %s (out=%s)"%(n,out))
            if out:
                return rtmidi.open_output(n)
            else:
                return rtmidi.open_input(n)
            
    raise Exception("Couldn't find %s (out=%s)" % (name,out))

xone_in = find_port("XONE", False)    
xone = find_port("XONE", True)    
rbox_in = find_port("Internal", False)
rbox = find_port("Internal", True)


# [shift][layer] = channel
layer2chan = {False: {0: 14, 1:12}, True: {0: 13, 1:11}}
# [channel] = (shift, layer)
chan2layer = {11:(True, 1), 12:(False, 1), 13:(True, 0), 14:(False, 0)}

#red + yell + green
# + 24 + 24
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
        if VU_ON == 0 or (VU_ON == 1 and layer == 0): return
        p = vu_mapping_1[val]+1
        m = vu_mapping_2[p]
        #prn(val," > ",p," > ",m)
        for i in range(0,4):
            note = m[i]+self._n
            velocity=127
            t = "note_on"
            if note<0:
                velocity=0
                note *= -1
                t = "note_off"
            msg=mido.Message(type=t, channel=14, note=note, velocity=velocity)
            #prn(msg)
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
#  E3 F3 F#3 G3
#0x34 35 36 37
#0=red, +36=orange, +72=green
vu_mapping_2 = [
        [-72-25, -72-29, -72-33, -72-37],
        [25+72, -72-29, -72-33, -72-37],
        [25+72, 29+72, -72-33, -72-37],
        [25+72, 29+72, 33+72, -72-37],
        [25+72, 29+72, 33+72, 37+72],
        [25+36, 29+72, 33+72, 37+72],
        [25+36, 29+36, 33+72, 37+72],
        [25+36, 29+36, 33+36, 37+72],
        [25+36, 29+36, 33+36, 37+36],
        [25, 29+36, 33+36, 37+36],
        [25, 29, 33+36, 37+36],
        [25, 29, 33, 37+36],
        [25, 29, 33, 37],
]
decks = [Deck(0),Deck(1)]
def handle_rbox(msg):
    prn("RB",msg," = ",msg.hex())
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
        if msg.note == 41:
            decks[0].play(msg.velocity == 127)
        if  msg.note == 42:
            decks[1].play(msg.velocity == 127)

        if msg.note == 15:
            return
        if msg.channel == 11:
            if msg.note == 0:
                decks[0].loaded(msg.velocity)
            if msg.note == 1:
                decks[1].loaded(msg.velocity)
            if msg.note == 4:
                decks[0].warn(msg.velocity)
            if msg.note == 5:
                decks[1].warn(msg.velocity)

        if msg.note in yellows:
            msg.note += 36
        if msg.note in greens:
            msg.note += 72
        if ((msg.note >= 24 and msg.note <= 39)) and msg.channel in ledcache.keys():
            ledcache[msg.channel][msg.note] = msg.velocity

            if msg.channel in chan2layer:
                s2, l2 = chan2layer[msg.channel]
                if l2 == layer:
                    msg.channel = 14
                    if l2 == 0:
                        if msg.velocity in pad_mapping:
                            msg.note += 36 * pad_mapping[msg.velocity]
                            msg.velocity = 127
                        else:
                            print("not found: %d"%msg.velocity)
                            msg.note += 36
                    else:
                        msg.note += 72
                else:
                    return
                prn(s2, l2, layer)

    prn(" "*20+"<<",msg," = ",msg.hex())
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


def update_layer_color():
    if layer == 0:
        xone.send(mido.Message(type="note_on", channel=14, note=0x0f))
    elif layer == 2:
        xone.send(mido.Message(type="note_on", channel=14, note=0x13))
    elif layer == 1:
        xone.send(mido.Message(type="note_on", channel=14, note=0x17))

    # if VU overrides hotcue, dont update
    if VU_ON == 2: return

    chan = layer2chan[False][layer]
    for n,v in ledcache[chan].items():
        if v > 0:
            if layer == 0:
                if v in pad_mapping:
                    n += 36 * pad_mapping[v]
                else:
                    n += 36
            if layer == 1:
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
    global last_xone,shift,layer
    last_xone = time.time()
    skipshift=False
    dup=False
    prn("K2",msg," = ",msg.hex())
    if msg.type in ["note_on","note_off"] and msg.channel == 14 and msg.note == 12:
        shift = msg.velocity == 127
        xone.send(msg)
        return

    if msg.type == 'control_change' and msg.channel == 14 and msg.control in [0,3]:
        cc = cc0 = msg.control
        msg.channel = 0 if cc == 0 else 1
        cc = 0 if msg.value == 127 else 1
        msg = mido.Message(type="note_on", channel=msg.channel, note=cc, velocity=127)
        if shift or (cc0==0 and not decks[0].playing()) or (cc0==3 and not decks[1].playing()):
            msg.channel += 4
        
        rbox.send(msg)
        prn(" "*40+">>",msg," = ",msg.hex())
        msg.velocity = 0
        rbox.send(msg)
        prn(" "*40+">>",msg," = ",msg.hex())
        return
    elif msg.type == "note_off":
        m = msg.dict()
        m['type'] = "note_on"
        msg = mido.Message(**m)
        msg.velocity = 0


    l0 = layer
    if msg.type == "note_on" and msg.channel == 14 and msg.note == 15:
        skipshift=True
        dup = True
        if msg.velocity == 0:
            layer = (layer+1)%2
        update_layer_color()

    if shift and not skipshift:
        if msg.channel == 14:
            msg.channel = 13
        else:
            msg.channel += 4
    
    if msg.type == "note_on" and ((msg.note >= 24 and msg.note <= 39) or msg.note==15):
        msg.channel -= l0*2

    rbox.send(msg)
    prn(" "*40+">>",msg," = ",msg.hex())

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
        key = msvcrt.getch()
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
            print(">>> VU: %d" % VU_ON)
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

