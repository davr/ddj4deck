# ddj4deck
python script to control 4 rekordbox decks from a ddj400 controller

# xone.py
python script to do some midi translations on a XONE K2 controller to make rekordbox understand it better (workaround for RB's limited midi mapping features).

## Usage:
1. Launch te.py
2. Launce xone.py
3. Launch rekordbox
4. Open MIDI mapping panel
5. Select "PIONEER DDJ-SX" virtual device
6. Delete all existing mappings (might not be needed?)
7. Import "PIONEER DDJ-SX.csv"

## Mapping:

* When two options A/B given, B is the shift feature.
* Except for the Hotcue / beatjump section -- those are toggled with the toggle button.
* Shift + hotcue == delete hotcue
* When in "PartISO" mode, the EQ knobs change to track separation ("Part Isolation") mode, controlling inst/vocal/drums instead of hi/mid/low. Note that there is no soft takeover, so if you don't reset the knobs to center before switching modes, you may get some unexpected jumps in values.
* FX1 Channel: Red=1, Orange=2, Green=1+2

| | Deck 1 | Deck 1 | Deck 2 | Deck 2 |
| --- | --- | --- | --- | --- |
| Rotary | Pitch bend / seek<br>Press: Browse area | Browse / Waveform Zoom<br>Press: Load left / Inst Dbls | Browse / Waveform Zoom<br>Press: Load left / Inst Dbls | Pitch bend / seek<br>Press: Browse toggle |
| LED | Warning | Loaded | Loaded | Warning |
| Knob | Headphone mix | EQ High / Inst | EQ High / Inst | Master Level |
| Btn | FX1 On | Headphone cue / PartISO | Headphone cue / PartISO | Master cue |
| Knob | Headphone level | EQ Mid / Vocal | EQ Mid / Vocal | FX1 Level |
| Btn | CFX On | Cue /  | Cue | FX1 Channel |
| Knob | CFX | EQ Low / Drums | EQ Low / Drums | CFX |
| Btn | Sync | Play / Preview play| Play / Preview skip | Sync |
| Fader | Tempo | Volume | Volume | Tempo |
| Btn | A / <1 | E / >1 | A / <1 | E / >1 |
| Btn | B / <4 | F / >4 | B / <4 | F / >4 |
| Btn | C / <8 | G / >8 | C / <8 | G / >8 |
| Btn | D / <32 | H / >32 | D / <32 | H / >32 |
| Btn / Rotary| Shift | Loop size<br>Press: Autoloop | Loop size<br>Press: Autoloop | Hotcue / Beatjump toggle |

## TODO:
* Combine te.py and xone.py into a single file -- the reason for both, is that if xone.py crashes (ie if the XONE:K2 disconnects), te.py stays running, and te.py is what talks to rekordbox. RB does not like it if a midi controller disappears mid-set, so this lets RB keep running in case of fault. But we could combine them, perhaps having te.py auto-launch xone.py, and restart it if it fails
* Implement soft-takeover for eq vs track sep knobs
* Add some fun animations when the controller is idle (like the built-in startup animation, but continuous)
* Add a fx type selector (re-use one of the redundant browse knobs?)