# ddj4deck
python script to control 4 rekordbox decks from a ddj400 controller

# xone.py
python script to do some midi translations on a XONE K2 controller to make rekordbox understand it better (workaround for RB's limited midi mapping features).

## Usage:
1. Launch xone.py
2. Launch rekordbox
3. Open MIDI mapping panel
4. Select "PIONEER DDJ-SX" virtual device
5. Delete all existing mappings
6. Import "PIONEER DDJ-SX.csv"

## Mapping:

When two options A/B given, B is the shift feature.
Except for the Hotcue / beatjump section -- those are toggled with the toggle button.
Shift + hotcue == delete hotcue

| | Deck 1 | Deck 1 | Deck 2 | Deck 2 |
| --- | --- | --- | --- | --- |
| Rotary | Pitch bend / seek<br>Press: Browse area | Browse / Waveform Zoom<br>Press: Load left / Inst Dbls | Browse / Waveform Zoom<br>Press: Load left / Inst Dbls | Pitch bend / seek<br>Press: Browse toggle |
| LED | | |  |  |
| Knob | Headphone mix | EQ High | EQ High | Master Level |
| Btn |    | Headphone cue / PartISO | Headphone cue / PartISO | Master cue |
| Knob | Headphone level | EQ Mid | EQ Mid | FX1 Level |
| Btn | CFX On | Cue | Cue | FX1 On |
| Knob | CFX | EQ Low | EQ Low | CFX |
| Btn | Sync | Play / Preview play| Play / Preview skip | Sync |
| Fader | Tempo | Volume | Volume | Tempo |
| Btn | A / <1 | E / >1 | A / <1 | E / >1 |
| Btn | B / <4 | F / >4 | B / <4 | F / >4 |
| Btn | C / <8 | G / >8 | C / <8 | G / >8 |
| Btn | D / <32 | H / >32 | D / <32 | H / >32 |
| Btn / Rotary| Shift | Loop size<br>Press: Autoloop | Loop size<br>Press: Autoloop | Hotcue / Beatjump toggle |
