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

def make_map(row, col, extrain=0,extraout=0):
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
                if row['type'] == 'KnobSliderHiRes':
                    print(row)
                    valin, valout = make_map(row, 'deck1',0,0)
                    cmd_mapping[valin] = valout
                    print(hex(valin),hex(valout))
                    valin, valout = make_map(row, 'deck1',2,2)
                    cmd_mapping[valin] = valout
                    print(hex(valin),hex(valout))
                else:    
                    valin, valout = make_map(row, 'deck1')
                    cmd_mapping[valin] = valout
            if row['deck2'] is not None and row['deck2'] != '':
                if row['type'] == 'KnobSliderHiRes':
                    valin, valout = make_map(row, 'deck2',0,4)
                    cmd_mapping[valin] = valout
                    valin, valout = make_map(row, 'deck2',2,6)
                    cmd_mapping[valin] = valout
                else:    
                    valin, valout = make_map(row, 'deck2')
                    cmd_mapping[valin] = valout

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


ddj2virt = cmd_mapping
virt2ddj = {}
for k,v in cmd_mapping.items():
    virt2ddj[v] = k

def find_port(name, out=True):
    if out:
        names = mido.get_output_names()
    else:
        names = mido.get_input_names()
    
    for n in names:
        if n.startswith(name):
            print("Found %s (out=%s)"%(n,out))
            if out:
                return mido.open_output(n)
            else:
                return mido.open_input(n)
            
    print("Couldn't find %s (out=%s)" % (name,out))
    sys.exit()

djin = find_port("DDJ-400", False)    
djout = find_port("DDJ-400", True)    

#virtin = find_port("Virtual", False)    
#virtout = find_port("Virtual", True)    

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

def virtout_send(msg):
    global virt
    b = bytes(msg.bin())
    dp(b)
    res = te.sendData(virt, b, len(b))
    if not res:
        print("Error sending message!")
        sys.exit(0)
SHIFT1=False
SHIFT2=False
def handle_ddj(msg):
    global SHIFTED,SHIFT1,SHIFT2
    global ddj2virt
    dp(("DDJ",msg.hex(),msg))
    b = msg.bytes()
    if (b[0] == 0xB0 or b[0] == 0xB1) and b[1] in (0x21,0x22,0x23,0x29):
        if b[2] < 64: b[2] -= 5
        elif b[2] > 64: b[2] += 5
        msg = mido.Message.from_bytes(b)
    if SHIFTED:    
        msg = map_cmd(msg, ddj2virt)
    virtout_send(msg)
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
    
def handle_virt(msg):
    global SHIFTED,SHIFT1,SHIFT2
    dp(("Virt",msg.hex(),msg))
    if SHIFTED:
        msg = map_cmd(msg, virt2ddj)
    djout.send(msg)

djin.callback = handle_ddj

virt = te.createPort2("PIONEER DDJ-SX", None, None, 1024, 1 + 2 + 4 + 8)
buf = create_string_buffer(1024)

#virtin.callback = handle_virt
for i in range(0,20):
    sz = c_int(1024)
    res = te.getData(virt, buf, byref(sz))
    msg=mido.Message.from_bytes(buf.raw[0:sz.value])
    print(msg)

djout.send(mido.Message.from_bytes([0xF0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x02, 0x06, 0x00, 0x03, 0x01, 0xf7]))

while True:
    sz = c_int(1024)
    res = te.getData(virt, buf, byref(sz))
    if not res:
        print("Error getting midi message! Need size: "+str(sz))
        break

    msg = mido.Message.from_bytes(buf.raw[0:sz.value])
    handle_virt(msg)
    time.sleep(0.001)
