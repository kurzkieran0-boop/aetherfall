"""In This Town, You Get 5,000 Words - config (video 3, Style B, chest word counter)."""
SLUG = "five_thousand_words"
TITLE = "In This Town, You Get 5,000 Words"
NARRATOR = "Finn"
STYLE = "B"
VOICE = "en_US-bryce-medium"           # natural young male narrator (ryan-high mangled the yell)
LENGTH_SCALE = 0.595                   # auto-tuned by kit/tts.py into the WPS window (bryce is a slow voice)
SENT_GAP = 0.14                        # tighter sentence gaps / silence squeeze keep 582 words under 2:50
MAX_SIL = 0.26
SQUEEZE_TO = 0.16
WPS = (3.0, 3.6)
MIN_AUDIO = 140.0
MIN_SHOTS = 80
SHOT_TARGET = 1.4
SAMPLES = 8
COUNTER = dict(label="words", who="finn")
RED_NUMBERS = True
RED_ALWAYS = ("stone",)
TEST_SHOT = "shot_026"                 # s09 "And then there's me." - Finn mcu, counter 4812, street + houses
