#!/usr/bin/python3
print("start")
import mido

virtualPorts = mido.Backend('mido.backends.tevirtualmidi')
virt = virtualPorts.open_ioport("PIONEER DDJ-SX", virtual=True)
#virt = virtualPorts.open_ioport("DDJ-400", virtual=True)

rtmidi = mido.Backend("mido.backends.rtmidi")

# find a midi device by name
def find_port(name, out=True):
    print("Enumerating names")
    if out:
        names = rtmidi.get_output_names()
    else:
        names = rtmidi.get_input_names()
    print(names)
    
    for n in names:
        if n.startswith(name):
            print("Found %s (out=%s)"%(n,out))
            if out:
                return rtmidi.open_output(n)
            else:
                return rtmidi.open_input(n)
            
    print("Couldn't find %s (out=%s)" % (name,out))
    sys.exit()

djin = find_port("XONE", False)    
djout = find_port("XONE", True)    



def handle_virt(msg):
    print("RB",msg," = ",msg.hex())
    djout.send(msg)

# chan=14
# rotary = cc
# 0,1,2,3 top row
# 0 and 3
# left = 127, right = 1
shift = False
def handle_xone(msg):
    global shift
    print("K2",msg," = ",msg.hex())
    if msg.type in ["note_on","note_off"] and msg.channel == 14 and msg.note == 15:
        shift = msg.velocity == 127
        djout.send(msg)
        return

    if msg.type == 'control_change' and msg.channel == 14 and msg.control in [0,3]:
        msg.channel = 0 if msg.control == 0 else 1
        msg.control = 0 if msg.value == 127 else 1
        msg = mido.Message(type="note_on", channel=msg.channel, note=msg.control, velocity=127)
        if shift:
            msg.channel += 4
        
        virt.send(msg)
        print(">>",msg," = ",msg.hex())
        msg.velocity = 0
        virt.send(msg)
        print(">>",msg," = ",msg.hex())
        return
    elif msg.type == "note_off":
        m = msg.dict()
        m['type'] = "note_on"
        msg = mido.Message(**m)
        msg.velocity = 0


    if shift:
        if msg.channel == 14:
            msg.channel = 13
        else:
            msg.channel += 4
    
    virt.send(msg)
    print(">>",msg," = ",msg.hex())

    if msg.type == "note_on" and msg.channel == 14 and msg.note in [12,16,20]:
        print("DD c=13")
        msg.channel=13
        virt.send(msg)

def loop():
    while True:
        handle_virt(virt.receive())
from threading import Thread
t = Thread(target=loop, daemon=True)
t.start()
while True:
    handle_xone(djin.receive())

