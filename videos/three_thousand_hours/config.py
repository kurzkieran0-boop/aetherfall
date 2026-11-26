"""In This Town, You Get 3,000 Hours Awake - config (video 6)."""
SLUG = "three_thousand_hours"
TITLE = "In This Town, You Get 3,000 Hours Awake"
NARRATOR = "Nora"
STYLE = "B"
VOICE = "en_US-kristin-medium"          # natural young-sounding narrator (not used by any other video)
LENGTH_SCALE = 0.765                    # starting pace (kit auto-tunes into WPS); keeps 552 verbatim words under 2:50
WPS = (3.0, 3.6)
MIN_AUDIO = 140.0
MIN_SHOTS = 80                          # counted excluding blind POV shots
SHOT_TARGET = 1.4
SAMPLES = 8
COUNTER = dict(label="hours awake", who="nora")
RED_NUMBERS = True
RED_ALWAYS = ("stone",)
TEST_SHOT = "shot_032"
