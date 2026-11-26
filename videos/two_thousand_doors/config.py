"""In This Town, You Get 2,000 Doors - config (video 5)."""
SLUG = "two_thousand_doors"
TITLE = "In This Town, You Get 2,000 Doors"
NARRATOR = "Theo"
STYLE = "B"
VOICE = "en_US-joe-medium"            # natural boy-ish narrator (own voice; no pitch shift, no tempo change)
LENGTH_SCALE = 0.95                    # auto-tuned by kit/tts.py into the WPS window
WPS = (3.0, 3.6)
MIN_AUDIO = 140.0
MIN_SHOTS = 80
SHOT_TARGET = 1.4
SAMPLES = 8
COUNTER = dict(label="doors", who="theo")
RED_NUMBERS = True
RED_ALWAYS = ("stone",)
TEST_SHOT = None
