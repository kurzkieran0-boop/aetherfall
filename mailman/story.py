"""Story text + visual beats for "The Mailman Skips Our House".

Each sentence: (id, text, beats, light). CAPS words are shown in RED captions.
EXTRA beats are only inserted (before scene 17) if the voice track runs short of MIN_AUDIO.
"""
MIN_AUDIO = 140.0
MAX_AUDIO = 165.0


def B(set_, cam, tgt, **kw):
    d = dict(set=set_, cam=cam, tgt=tgt)
    d.update(kw)
    return d


def C(card):
    return dict(card=card)


DAY, GOLD, DUSK, NIGHT = "day", "golden", "dusk", "night"
SC = {"dobbs": "scared"}

S = [
    ("s01", "The mailman has skipped our house for forty days. And every time he walks past, he looks SCARED.", [
        B("town", "drone", "pt:-40,-4,0"),
        B("street", "chase", "dobbs", faces=SC),
        C("forty"),
        B("street", "track", "dobbs", faces=SC),
        B("gate", "ecu", "dobbs", faces=SC),
    ], DAY),
    ("s02", "My name is Eli. I'm eleven. Our town has exactly one mailman, Mr. Dobbs, and he has never missed a house. "
            "Not once. Not in thirty years.", [
        B("street", "tilt", "eli"),
        B("street", "cu", "eli", faces={"eli": "blank"}),
        B("town", "drone", "pt:20,0,0"),
        B("follow_bakery", "low", "dobbs"),
        B("follow_bakery", "cu", "dobbs"),
        C("thirty"),
        B("street", "ecu", "eli", faces={"eli": "tired"}),
    ], DAY),
    ("s03", "Until day one. He walked up our street, stopped at our gate, looked at our mailbox, and kept walking.", [
        B("street", "wide", "dobbs"),
        B("gate", "low", "dobbs"),
        B("gate", "prop", "mailbox"),
        B("gate", "ecu", "dobbs", faces=SC, acts={"dobbs": "look_mailbox"}),
        B("street", "chase", "dobbs"),
    ], DAY),
    ("s04", "I figured it was a mistake. Day two, same thing. Day three, he crossed the street to avoid us.", [
        B("street", "ots", "dobbs", over="eli"),
        B("gate", "high", "dobbs"),
        B("cross", "wide", "dobbs", faces=SC),
        B("cross", "whip", "dobbs", faces=SC),
        B("cross", "cu", "eli", faces={"eli": "blank"}),
    ], DAY),
    ("s05", "By day ten, he was walking faster. By day twenty, he was running. By day thirty, he wore his cap pulled "
            "down over his eyes, like he didn't want our house to see his face.", [
        B("street", "track", "dobbs", faces=SC),
        B("runpast", "chase", "dobbs", faces=SC),
        B("runpast", "low", "dobbs", faces=SC),
        C("days"),
        B("capdown", "cu", "dobbs", capdown=True),
        B("capdown", "ecu", "dobbs", capdown=True),
        B("capdown", "prop", "eli_house"),
        B("capdown", "ots", "dobbs", over="eli", capdown=True),
    ], DAY),
    ("s06", "Everyone else got mail. The baker got bills. Mrs. Pell got postcards from her sister. The mayor got a letter "
            "every single morning, and he always read it standing in the street, and he always went pale.", [
        B("town", "drone", "pt:0,4,0"),
        B("bakery", "ots", "baker", over="dobbs", faces={"baker": "tired"}),
        B("bakery", "ecu", "baker", faces={"baker": "tired"}),
        B("pell", "cu", "pell"),
        B("pell", "low", "pell"),
        B("mayor_st", "wide", "mayor"),
        B("mayor_st", "push", "mayor"),
        B("mayor_st", "ecu", "mayor", faces={"mayor": "shocked"}),
        B("mayor_st", "dutch", "mayor", faces={"mayor": "scared"}),
    ], DAY),
    ("s07", "Our mailbox got nothing. Just dust and one very confused spider.", [
        B("mailbox", "push", "mailbox"),
        B("mailbox", "prop", "mailbox_in", paper=False),
        B("mailbox", "cu", "eli", faces={"eli": "tired"}),
    ], DAY),
    ("s08", 'So I asked Mom. She said, "Maybe nobody writes to us." Dad said, "Eat your soup." '
            "Which is what Dad says when he's lying.", [
        B("kitchen", "wide", "eli"),
        B("kitchen", "cu", "mom", acts={"mom": "talk"}),
        B("kitchen", "ots", "mom", over="eli"),
        B("kitchen", "ecu", "dad", acts={"dad": "talk"}),
        B("kitchen", "high", "eli"),
        B("kitchen", "ecu", "dad", faces={"dad": "tired"}),
        B("kitchen", "ecu", "eli", faces={"eli": "blank"}),
    ], DAY),
    ("s09", "That's when I knew something was up. So I made a plan.", [
        B("kitchen", "dutch", "eli", faces={"eli": "blank"}),
        B("street", "cu", "eli"),
        B("street", "push", "eli"),
    ], DAY),
    ("s10", "Plan one: ask him directly. I waited at the corner at six a.m. He saw me from a block away, turned around, "
            "and ran. A grown man. With a mailbag the size of a sheep. Running.", [
        C("plan1"),
        B("corner", "low", "eli"),
        B("corner", "wide", "eli"),
        B("corner", "ecu", "dobbs", faces={"dobbs": "shocked"}),
        B("corner_run", "chase", "dobbs", faces=SC),
        B("corner_run", "track", "dobbs", faces=SC),
        B("corner_run", "low", "dobbs", faces=SC),
        B("corner_run", "high", "dobbs", faces=SC),
        B("corner", "cu", "eli", faces={"eli": "tired"}),
    ], GOLD),
    ("s11", "Plan two: follow him.", [
        C("plan2"),
        B("follow_bakery", "ots", "dobbs", over="eli"),
    ], DAY),
    ("s12", "He went to the bakery. Dropped a letter. The mill. Dropped a letter. Town hall. Dropped three.", [
        B("follow_bakery", "chase", "dobbs"),
        B("bakery", "prop", "bakery_sign"),
        B("follow_mill", "wide", "mill"),
        B("follow_mill", "low", "dobbs", acts={"dobbs": "give"}),
        B("follow_hall", "wide", "hall_sign"),
        B("follow_hall", "chase", "dobbs"),
        B("follow_hall", "cu", "eli"),
    ], DAY),
    ("s13", "Then he stopped at the end of the road, opened his bag, and pulled out one more envelope. Cream colored. "
            "Red wax seal. He stared at it for a long time.", [
        B("road_end", "wide", "dobbs"),
        B("road_end", "low", "dobbs"),
        B("road_end", "prop", "dobbs_env", paper=True),
        B("road_end", "ecu", "dobbs_env", paper=True),
        B("road_end", "ecu", "dobbs", faces=SC),
        B("road_end", "ots", "dobbs", over="eli"),
        B("road_end", "orbit", "dobbs"),
    ], DUSK),
    ("s14", 'Then he looked straight at our house. And whispered, "Not yet."', [
        B("road_end", "cu", "dobbs", acts={"dobbs": "look_house"}),
        B("road_end", "prop", "eli_house"),
        B("road_end", "ecu", "dobbs", acts={"dobbs": "whisper"}, faces=SC),
    ], DUSK),
    ("s15", "He put the letter back. And walked away.", [
        B("road_end", "prop", "dobbs_env", acts={"dobbs": "hold"}, paper=True),
        B("road_end", "chase", "dobbs", acts={"dobbs": "walk"}),
    ], DUSK),
    ("s16", 'Not YET? What does "not yet" mean?', [
        C("notyet"),
        B("road_end", "ecu", "eli", faces={"eli": "shocked"}),
        B("road_end", "dutch", "eli"),
    ], DUSK),
    ("s17", "That night I snuck out. Mr. Dobbs lives in the tiny blue house behind the post office. The light was on. "
            "I crept up to the window.", [
        B("night_st", "high", "eli"),
        B("night_st", "track", "eli"),
        B("dobbs_ext", "wide", "post_office"),
        B("dobbs_ext", "push", "dobbs_house"),
        B("dobbs_ext", "low", "eli"),
        B("window", "ots", "dobbs_window", over="eli"),
        B("window", "ecu", "eli"),
    ], NIGHT),
    ("s18", "Inside, the walls were covered in envelopes. Hundreds. Maybe thousands. Every one cream colored. "
            "Every one sealed in red wax.", [
        B("window", "ots", "env_wall", over="eli", paper=True),
        B("int", "pan", "env_wall", paper=True),
        B("int", "orbit_room", "pt:40,30,1.7", paper=True),
        B("int", "tilt_wall", "env_wall_back", paper=True),
        B("int", "ecu_wall", "env_wall", paper=True),
        B("window", "ecu", "eli", faces={"eli": "shocked"}),
        B("int", "push", "env_wall_back", paper=True),
    ], NIGHT),
    ("s19", "And every one had a name on it. The baker. Mrs. Pell. The mayor. Even Mr. Dobbs himself.", [
        B("int", "ecu_wall", "env_wall_back", paper=True),
        B("bakery", "ecu", "baker", light=DUSK),
        B("pell", "ecu", "pell", light=DUSK),
        B("mayor_st", "ecu", "mayor", light=DUSK),
        B("int", "ecu_wall", "env_wall", paper=True),
        B("window", "cu", "eli", faces={"eli": "scared"}),
    ], NIGHT),
    ("s20", "There was a whole shelf with the name of every kid in town. Clara. Theo. Maya. Jonah. All of them.", [
        B("int", "push", "shelf", paper=True),
        B("int", "prop", "shelf", paper=True),
        B("int", "shelf_pan", "shelf", paper=True),
        B("int", "ecu_wall", "shelf", paper=True),
        B("window", "ecu", "eli", faces={"eli": "scared"}),
    ], NIGHT),
    ("s21", "And in the middle, alone on a little hook, one letter that said: ELI.", [
        B("int", "push", "hook", paper=True),
        B("int", "prop", "hook", paper=True),
        B("window", "ecu", "eli", faces={"eli": "shocked"}),
        B("int", "ecu_hook", "hook", paper=True),
    ], NIGHT),
    ("s22", "I almost fell off the windowsill. Then the door creaked open behind me.", [
        B("window", "low", "eli", acts={"eli": "stagger"}, faces={"eli": "shocked"}),
        B("int_door", "cu", "eli", faces={"eli": "scared"}),
        B("int_door", "wide", "door_int", door="opening"),
        B("int_door", "low", "dobbs", door="open", faces=SC),
    ], NIGHT),
    ("s23", '"You weren\'t supposed to see that," said Mr. Dobbs. His hands were shaking.', [
        B("int_door", "cu", "dobbs", door="open", acts={"dobbs": "talk"}, faces=SC),
        B("int_door", "ots", "dobbs", over="eli", door="open"),
        B("int_door", "cu", "dobbs", door="open", acts={"dobbs": "shake"}, faces=SC),
        B("int_door", "ecu", "dobbs", door="open", faces=SC),
    ], NIGHT),
    ("s24", '"What are those letters?" I asked. He looked at the floor. "Every letter in this town is from the FUTURE."', [
        B("int_talk", "cu", "eli", acts={"eli": "talk"}, door="open"),
        B("int_talk", "high", "dobbs", acts={"dobbs": "look_down"}, door="open"),
        B("int_talk", "ots", "dobbs", over="eli", acts={"dobbs": "talk"}, door="open"),
        C("future"),
        B("int_talk", "ecu", "dobbs", faces={"dobbs": "tired"}, door="open"),
    ], NIGHT),
    ("s25", '"They show up on my doorstep a day before anyone writes them. Nobody knows who sends them."', [
        B("int_talk", "orbit_room", "pt:40,30,1.7", door="open", paper=True),
        B("int_talk", "cu", "dobbs", acts={"dobbs": "talk"}, door="open"),
        B("int_talk", "prop", "door_int", door="open"),
        B("int_talk", "ecu", "eli", faces={"eli": "scared"}, door="open"),
    ], NIGHT),
    ("s26", '"Mostly they\'re boring. Bills. Birthdays. Recipes. But sometimes they say what\'s going to happen to you."', [
        B("int_talk", "ots", "dobbs", over="eli", acts={"dobbs": "talk"}, door="open"),
        B("int", "ecu_wall", "env_wall", paper=True),
        B("bakery", "ecu", "baker", faces={"baker": "tired"}),
        B("int", "ecu_wall", "env_wall_back", paper=True),
        B("int_talk", "ecu", "dobbs", faces=SC, door="open"),
    ], NIGHT),
    ("s27", '"Last year I delivered a letter to old Mr. Harlan. It said his barn would burn. He laughed. '
            'The barn burned the next morning."', [
        B("barn", "wide", "barn", light=DAY),
        B("barn", "cu", "harlan", light=DAY),
        C("harlan"),
        B("barn", "low", "harlan", acts={"harlan": "laugh"}, faces={"harlan": "talk"}, light=DAY),
        B("barn_fire", "wide", "barn", fire=True, light=GOLD),
        B("barn_fire", "high", "barn", fire=True, light=GOLD),
        B("barn_fire", "ecu", "harlan", fire=True, faces={"harlan": "shocked"}, light=GOLD),
    ], NIGHT),
    ("s28", '"So I stopped delivering the bad ones. But yours is the worst one I\'ve ever seen."', [
        B("int_talk", "cu", "dobbs", acts={"dobbs": "talk"}, door="open"),
        B("int", "push", "hook", paper=True),
        B("int_talk", "dutch", "dobbs", faces=SC, door="open"),
        B("int_talk", "ecu", "eli", faces={"eli": "shocked"}, door="open"),
    ], NIGHT),
    ("s29", 'My stomach dropped. "What does it say?"', [
        B("int_talk", "high", "eli", faces={"eli": "scared"}, door="open"),
        B("int_talk", "cu", "eli", acts={"eli": "talk"}, door="open"),
    ], NIGHT),
    ("s30", '"I can\'t tell you." "Then give it to me." "You don\'t want it." "Mr. Dobbs. It\'s MY letter. '
            'It\'s my house. It\'s my life."', [
        B("int_talk", "ecu", "dobbs", faces=SC, door="open"),
        B("int_talk", "ots", "eli", over="dobbs", acts={"eli": "talk"}, door="open"),
        B("int_talk", "ecu", "dobbs", faces={"dobbs": "tired"}, door="open"),
        B("int_talk", "cu", "eli", acts={"eli": "point"}, door="open"),
        B("int_talk", "ecu", "eli", door="open"),
        B("int_talk", "push", "eli", acts={"eli": "talk"}, door="open"),
    ], NIGHT),
    ("s31", "He stared at me for a long time. Then he took the cream envelope with my name and put it in my hands.", [
        B("int_talk", "ecu", "dobbs", faces={"dobbs": "tired"}, door="open"),
        B("int_talk", "prop", "hook", paper=True),
        B("int_talk", "ots", "dobbs", over="eli", acts={"dobbs": "give"}, door="open", paper=True),
        B("int_final", "prop", "eli_env", acts={"eli": "hold"}, door="open", hide=["eli2"], paper=True),
    ], NIGHT),
    ("s32", "The wax was warm. Like someone had just pressed it.", [
        B("int_final", "ecu", "eli_env", acts={"eli": "read"}, door="open", hide=["eli2"], paper=True),
        B("int_final", "ecu", "eli", acts={"eli": "read"}, faces={"eli": "scared"}, door="open", hide=["eli2"]),
    ], NIGHT),
    ("s33", "I broke it open. Inside was one short note, in handwriting I knew better than my own.", [
        B("int_final", "prop", "eli_env", acts={"eli": "read"}, door="open", hide=["eli2"], paper=True),
        B("int_final", "high", "eli", acts={"eli": "read"}, door="open", hide=["eli2"], paper=True),
        B("int_final", "ecu", "eli", acts={"eli": "read"}, faces={"eli": "shocked"}, door="open", hide=["eli2"]),
    ], NIGHT),
    ("s34", 'It said: "Dear Eli. By now you\'ve followed the mailman, climbed his window, and broken the seal. '
            'Please don\'t turn around."', [
        C("letter1"),
        C("letter2"),
        B("int_final", "ecu", "eli", acts={"eli": "read"}, faces={"eli": "scared"}, door="open", nodobbs=True, hide=["eli2"]),
        C("letter3"),
        B("int_final", "dutch", "eli", acts={"eli": "read"}, faces={"eli": "scared"}, door="open", nodobbs=True, hide=["eli2"]),
    ], NIGHT),
    ("s35", 'It was signed: "Eli."', [
        C("signed"),
        B("int_final", "ecu", "eli", acts={"eli": "read"}, faces={"eli": "blank"}, door="open", nodobbs=True, hide=["eli2"]),
    ], NIGHT),
    ("s36", "I turned around.", [
        B("int_final", "cu", "eli", acts={"eli": "turn"}, faces={"eli": "scared"}, door="open", nodobbs=True),
    ], NIGHT),
    ("s37", "Mr. Dobbs was gone. The door was wide open. And standing in the doorway, holding a cream envelope with "
            "Mr. Dobbs's name on it... was ME.", [
        B("int_final", "push", "eli2", door="open", nodobbs=True, eli_turned=True),
        B("int_final", "cu", "eli2", door="open", nodobbs=True, eli_turned=True, faces={"eli2": "blank"}),
        B("int_final", "ots", "eli2", over="eli", door="open", nodobbs=True, eli_turned=True),
        B("int_final", "low", "eli2", door="open", nodobbs=True, eli_turned=True, faces={"eli2": "blank"}),
        B("int_final", "ecu", "eli2_env", door="open", nodobbs=True, eli_turned=True, paper=True),
        B("int_final", "ecu", "eli", door="open", nodobbs=True, eli_turned=True, faces={"eli": "shocked"}),
        B("int_final", "ecu", "eli2", door="open", nodobbs=True, eli_turned=True, faces={"eli2": "blank"}),
    ], NIGHT),
]

# extra story beats (inserted before s17 only if the narration is short)
EXTRA = [
    ("s16", ("e01", "So I checked the neighbors. The baker's mailbox: three bills and a coupon for flour. Mrs. Pell's: "
                    "a postcard with a goat on it. The mayor's: a cream envelope with a red wax seal.", [
        B("bakery", "prop", "bakery_sign"),
        B("pell", "cu", "pell"),
        B("mayor_st", "prop", "mayor_env", paper=True),
        B("mayor_st", "ecu", "mayor", faces={"mayor": "scared"}),
    ], DUSK)),
    ("e01", ("e02", "That evening I watched the mayor walk out to the field, read his letter, crumple it, and stuff it "
                    "in his pocket like it had bitten him.", [
        B("mayor_st", "wide", "mayor"),
        B("mayor_st", "ecu", "mayor_env", paper=True),
        B("mayor_st", "dutch", "mayor", faces={"mayor": "shocked"}),
    ], DUSK)),
    ("e02", ("e03", "At dinner, Mom and Dad were whispering. I heard one word. Letter. Then they saw me and started "
                    "talking about soup.", [
        B("kitchen", "cu", "mom", acts={"mom": "talk"}),
        B("kitchen", "ecu", "dad", faces={"dad": "tired"}),
        B("kitchen", "high", "eli"),
    ], DUSK)),
]

# lined-paper insert cards: key -> (lines, struck_line_indexes)
CARDS = {
    "forty": (["40 DAYS.", "0 LETTERS."], []),
    "thirty": (["30 YEARS.", "0 MISSED", "HOUSES."], []),
    "days": (["DAY 10: FASTER", "DAY 20: RUNNING", "DAY 30: CAP DOWN"], []),
    "plan1": (["PLAN ONE:", "ASK HIM", "DIRECTLY."], []),
    "plan2": (["PLAN ONE", "PLAN TWO:", "FOLLOW HIM."], [0]),
    "notyet": (["“NOT YET.”"], []),
    "future": (["FROM THE", "FUTURE."], []),
    "harlan": (["MR. HARLAN:", "YOUR BARN", "WILL BURN."], []),
    "letter1": (["DEAR ELI."], []),
    "letter2": (["BY NOW YOU'VE", "FOLLOWED THE", "MAILMAN, CLIMBED", "HIS WINDOW, AND", "BROKEN THE SEAL."], []),
    "letter3": (["PLEASE DON'T", "TURN AROUND."], []),
    "signed": (["— ELI"], []),
}


def build_script(use_extras):
    order = list(S)
    for after, sent in EXTRA[:use_extras]:
        idx = [s[0] for s in order].index(after)
        order.insert(idx + 1, sent)
    return order
