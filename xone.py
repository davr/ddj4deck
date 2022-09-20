#!/usr/bin/python3
import keyboard
import mido
import time
import sys

virtualPorts = mido.Backend('mido.backends.tevirtualmidi')
rbox = virtualPorts.open_ioport("PIONEER DDJ-SX", virtual=True)
#virt = virtualPorts.open_ioport("DDJ-400", virtual=True)

rtmidi = mido.Backend("mido.backends.rtmidi")
last_xone = time.time()
layer=0

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


# [shift][layer] = channel
layer2chan = {False: {0: 14, 1:12}, True: {0: 13, 1:11}}
# [channel] = (shift, layer)
chan2layer = {11:(True, 1), 12:(False, 1), 13:(True, 0), 14:(False, 0)}

#red + yell + green
# + 24 + 24
yellows = [45,46]
greens = [41,42]
def handle_rbox(msg):
    print("RB",msg," = ",msg.hex())
    if msg.type == "note_on":
        if msg.note == 15:
            return
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
                        msg.note += 36
                    else:
                        msg.note += 72
                else:
                    return
                print(s2, l2, layer)

    print(" "*20+"<<",msg," = ",msg.hex())
    try:
        xone.send(msg)
    except:
        print("XONE exception sending")
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

    chan = layer2chan[False][layer]
    for n,v in ledcache[chan].items():
        if v > 0:
            if layer == 0:
                n += 36
            if layer == 1:
                n += 72
            xone.send(mido.Message(type="note_on", channel=14, note=n, velocity=127))
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
    print("K2",msg," = ",msg.hex())
    if msg.type in ["note_on","note_off"] and msg.channel == 14 and msg.note == 12:
        shift = msg.velocity == 127
        xone.send(msg)
        return

    if msg.type == 'control_change' and msg.channel == 14 and msg.control in [0,3]:
        msg.channel = 0 if msg.control == 0 else 1
        msg.control = 0 if msg.value == 127 else 1
        msg = mido.Message(type="note_on", channel=msg.channel, note=msg.control, velocity=127)
        if shift:
            msg.channel += 4
        
        rbox.send(msg)
        print(" "*40+">>",msg," = ",msg.hex())
        msg.velocity = 0
        rbox.send(msg)
        print(" "*40+">>",msg," = ",msg.hex())
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
    print(" "*40+">>",msg," = ",msg.hex())

    if dup:
        msg.channel-=1
        print(" "*40+">>",msg," = ",msg.hex())
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

def loop():
    while True:
        try:
            handle_rbox(rbox.receive())
        except:
            print("Err handling rbox")
            #recon()

from threading import Thread
t = Thread(target=loop, daemon=True)
t.start()

update_layer_color()

#rbox.callback = handle_rbox
xone_in.callback = handle_xone
ping = mido.Message(type="note_on", channel=14, note=0, velocity=0)
while True:
    try:
        xone.send(ping)
    except:
        recon()
    if keyboard.is_pressed("x"):
        recon()
        last_xone = time.time()
    if keyboard.is_pressed("q"):
        print("Quitting")
        break
    try:
        time.sleep(1)
    except:
        print("Exiting")
        break

rbox.close()
xone.close()
xone_in.close()
#    try:
#        handle_xone(xone_in.receive())
#    except:
#        print("Err handling xone")
#        recon()

