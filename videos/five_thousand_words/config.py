"""In This Town, You Get 5,000 Words - config (video 3, Style B, chest word counter)."""
SLUG = "five_thousand_words"
TITLE = "In This Town, You Get 5,000 Words"
NARRATOR = "Finn"
STYLE = "B"
VOICE = "en_US-bryce-medium"           # natural young male narrator (ryan-high mangled the yell) (no pitch shift, no tempo change)
LENGTH_SCALE = 0.95                    # auto-tuned by kit/tts.py into the WPS window
WPS = (3.0, 3.6)
MIN_AUDIO = 140.0
MIN_SHOTS = 80
SHOT_TARGET = 1.4
SAMPLES = 8
COUNTER = dict(label="words", who="finn")
RED_NUMBERS = True
RED_ALWAYS = ("stone",)
TEST_SHOT = None                       # set after shots.py (Finn face + readable counter + town)
