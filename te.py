import ctypes
from ctypes import *
import time

vm = ctypes.WinDLL("c:/windows/system32/teVirtualMIDI.dll")
getver = vm.virtualMIDIGetVersion
getver.restype=c_wchar_p

major,minor,release,build=c_int(),c_int(),c_int(),c_int()
val = getver(byref(major), byref(minor), byref(release), byref(build))
print(val,major,minor,release,build)

#typedef void ( CALLBACK *LPVM_MIDI_DATA_CB )( LPVM_MIDI_PORT midiPort, LPBYTE midiDataBytes, DWORD length, DWORD_PTR dwCallbackInstance );
#CALLBACK = CFUNCTYPE(None, c_void_p, c_char_p, c_long, POINTER(c_long))

#LPVM_MIDI_PORT CALLBACK virtualMIDICreatePortEx2( LPCWSTR portName, LPVM_MIDI_DATA_CB callback, DWORD_PTR dwCallbackInstance, DWORD maxSysexLength, DWORD flags );
createPort2 = vm.virtualMIDICreatePortEx2
createPort2.restype = c_void_p
createPort2.argtypes = [c_wchar_p, c_void_p, POINTER(c_long), c_long, c_long]

closePort = vm.virtualMIDIClosePort
closePort.restype = c_void_p #CALLBACK
closePort.argtypes = [c_void_p]

getData = vm.virtualMIDIGetData
getData.restype = c_bool
getData.argtypes = [c_void_p, c_char_p, POINTER(c_int)]

sendData = vm.virtualMIDISendData
sendData.restype = c_bool
sendData.argtypes = [c_void_p, c_char_p, c_int]

def tester():
    def mycb(port, data, length, cbinst):
        print("Got msg: "+str(length))

    myport = createPort2("myport", None, None, 10240, 1 + 2 + 4 + 8)
    print(myport)
    t=0
    buf = create_string_buffer(1024)
    while t<1000:
        t+=1
        sz = c_int(1024) 
        res = getData(myport, buf, byref(sz))
        print(res,sz,buf.raw[0:sz.value])
        print(buf.raw[0:sz.value].hex())
        time.sleep(0.01)
    time.sleep(3)
    res = closePort(myport)
    print(res)

if __name__ == "__main__":
    tester()
