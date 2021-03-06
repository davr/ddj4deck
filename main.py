import mido
import sys
import time
import csv
import te
from ctypes import *
from glob import glob

mapping = glob("c:/Program Files*/Pioneer/rekordbox*/MidiMappings/DDJ-400.midi.csv")[0]
print("Midi mapping: %s"%mapping)
SHIFTED=False

# Translate a midi command from deck 1/2 into a midi command for deck 3/4, by adding a fixed value to it
# cmd = midi command to translate
# row = row from the mapping csv
# col = column from the mapping csv
# extrain/out = extra amount to add to the midi in/out command
def make_map(cmd, row, col, extrain=0,extraout=0):
    d1 = int(row[col])
    if d1 in [0,1]:
        d3 = d1+2
    elif d1 in [7,8,9,10]:
        d3 = d1+4
    else:
        print("Unknown deck %d"%d1)
        sys.exit()
    valin = int(cmd, 16)
    valin += d1<<8
    valin += extrain<<4
    valout = int(cmd, 16)
    valout += d3<<8
    valout += extraout<<4
    return valin, valout

from itertools import count
def remap(fieldnames):
    out=[]
    flag=0
    for f in fieldnames:
        if f.startswith('deck'):
            if flag < 4:
                f = f+'in'
            else:    
                f = f+'out'
            flag += 1    
        out += [f]        
    return out    


cmds = {}
cmd_mapping = {}
with open(mapping) as csvfile:
    csvfile.readline()
    reader = csv.reader(csvfile)
    fieldnames = remap(next(reader))
    for row in reader:
        row = dict(zip(fieldnames, row))
#        print(row)
        if not 'input' in row: continue
        if row['input'] == '903F':
            print(row)
        if row['input'] != '' and row['output'] != '' and row['input'] != row['output']:
            print("Unable to handle command with diff in/out msgs")
            print(row)
            continue
        # default to using the input command if available, otherwise use the output command
        cmd = row['input'] if row['input'] != '' else row['output']
        row['deck1'] = row['deck1out'] if row['deck1in'] == '' else row['deck1in']
        row['deck2'] = row['deck2out'] if row['deck2in'] == '' else row['deck2in']
        if cmd != '' and cmd is not None:
            cmd_map = cmd + "_"+row['deck1']+"_"+row['deck2']
            if cmd in cmds:
                print("Duplicate command:")
                print(cmds[cmd_map])
                print(row)
            cmds[cmd_map] = row
            if row['deck1'] is not None and row['deck1'] != '':
                if row['type'] == 'KnobSliderHiRes':  # special case for hi res sliders
                    print(row)
                    valin, valout = make_map(cmd, row, 'deck1',0,0)
                    cmd_mapping[valin] = valout
                    print(hex(valin),hex(valout))
                    valin, valout = make_map(cmd, row, 'deck1',2,2)
                    cmd_mapping[valin] = valout
                    print(hex(valin),hex(valout))
                else:    
                    valin, valout = make_map(cmd, row, 'deck1')
                    cmd_mapping[valin] = valout
            if row['deck2'] is not None and row['deck2'] != '':
                if row['type'] == 'KnobSliderHiRes':
                    valin, valout = make_map(cmd, row, 'deck2',0,4)
                    cmd_mapping[valin] = valout
                    valin, valout = make_map(cmd, row, 'deck2',2,6)
                    cmd_mapping[valin] = valout
                else:    
                    valin, valout = make_map(cmd, row, 'deck2')
                    cmd_mapping[valin] = valout

# don't map these special ones (i already forget what they were)
del cmd_mapping[0x903F]
del cmd_mapping[0x913F]

# Manually map load and loop indicators                    
cm = cmd_mapping
cm[0xb617] = 0xb619
cm[0xb617 + 0x20] = 0xb619 + 0x20
cm[0xb618] = 0xb61a
cm[0xb618 + 0x20] = 0xb61a + 0x20
cm[0x9646] = 0x9648
cm[0x9647] = 0x9649

#Jog Search B01F - B029

rtmidi = mido.Backend("mido.backends.rtmidi")

ddj2virt = cmd_mapping
virt2ddj = {}
for k,v in cmd_mapping.items():
    virt2ddj[v] = k

# find a midi device by name
def find_port(name, out=True):
    if out:
        names = rtmidi.get_output_names()
    else:
        names = rtmidi.get_input_names()
    
    for n in names:
        if n.startswith(name):
            print("Found %s (out=%s)"%(n,out))
            if out:
                return rtmidi.open_output(n)
            else:
                return rtmidi.open_input(n)
            
    print("Couldn't find %s (out=%s)" % (name,out))
    sys.exit()

djin = find_port("DDJ-400", False)    
djout = find_port("DDJ-400", True)    

#virtin = find_port("Virtual", False)    
#virtout = find_port("Virtual", True)    

# Overall program logic:
#
# ddj > virtual
#  if has deck
#    if deck is shifted
#      modify channel [0-1>2-3,7-10>11-14]
#    else
#      dont modify
#  else
#    dont modify
# virtual > ddj
#  if has deck
#    if matches active deck
#      if shifted
#        modify
#      else
#        dont modify
#    else
#      drop
#  else
#    dont modify
#
# TODO: mixer 3/4 on nanokontrol?
# pad mode buttons: duplicate to both decks (to make screen more clear)
# why is jog wheel laggin, cut down number of msgs / combine them?

debug=0
def dp(m):
    global debug
    if debug: print(m)

def map_cmd(msg, cmd_mapping):
    b = msg.bytes()
    cmd = (b[0]<<8) + b[1]
    if cmd in cmd_mapping:
        m = cmd_mapping[cmd]
        msg = mido.Message.from_bytes([m>>8, m&0xFF] + b[2:])
        dp((">>>",msg.hex(),msg))
    return msg    

SHIFT1=False
SHIFT2=False
ls=0
lst=0

# hasndle messages coming from ddj-400 controller
def handle_ddj(msg):
    global SHIFTED,SHIFT1,SHIFT2
    global ddj2virt
    global virt
    global ls,lst
    b = msg.bytes()
    if (b[0] == 0xB0 or b[0] == 0xB1) and b[1] in (0x21,0x22,0x23,0x29):
        if time.time() - lst < 0.005:
            nls = ls + b[2]-64
            if nls>-63 and nls < 63:
                ls=nls
                return
        if b[2] < 64: b[2] -= 5
        elif b[2] > 64: b[2] += 5
        b[2] += ls
        if b[2] < 0: b[2] = 0
        if b[2] > 127: b[2] = 127
        ls = 0
        lst = time.time()
        msg = mido.Message.from_bytes(b)
    dp(("DDJ",msg.hex(),msg))
    if SHIFTED:    
        msg = map_cmd(msg, ddj2virt)
    virt.send(msg)
    if b[0:2]==[0x90, 0x3f]:
        SHIFT1=b[2]==0x7f
        if SHIFT2 and SHIFT1:
            SHIFTED = not SHIFTED
            print(">>SHIFT %s"%SHIFTED)
    if b[0:2]==[0x91, 0x3f]:
        SHIFT2=b[2]==0x7f
        if SHIFT1 and SHIFT2: 
            SHIFTED = not SHIFTED
            print(">>SHIFT %s"%SHIFTED)
    
# handle messages from virtual midi port (ie, rekordbox)    
def handle_virt(msg):
    global SHIFTED,SHIFT1,SHIFT2
    dp(("Virt",msg.hex(),msg))
    if SHIFTED:
        msg = map_cmd(msg, virt2ddj)
    djout.send(msg)

#djin.callback = handle_ddj

virtualPorts = mido.Backend('mido.backends.tevirtualmidi')

virt = virtualPorts.open_ioport("PIONEER DDJ-SX", virtual=True)

#for i in range(0,20):
#    print(virt.receive())

djout.send(mido.Message.from_bytes([0xF0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x02, 0x06, 0x00, 0x03, 0x01, 0xf7]))

def loop():
    while True:
        handle_virt(virt.receive())
from threading import Thread
t = Thread(target=loop, daemon=True)
t.start()
while True:
    handle_ddj(djin.receive())
