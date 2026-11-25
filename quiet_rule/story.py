"""Story text + visual beats for "The Quiet Rule".

Each sentence: (id, text, beats, light, pause_after)
CAPS words in text are spoken normally but shown in RED in captions.
Extra beats (ids starting with E) are only inserted if the base voice track
is shorter than MIN_AUDIO seconds (LENGTH RULE).
"""

MIN_AUDIO = 141.0  # seconds of voice timeline we want before the end black


def B(set_, cam, tgt, **kw):
    d = dict(set=set_, cam=cam, tgt=tgt)
    d.update(kw)
    return d


def C(card):
    return dict(card=card)


DAY, GOLD, DUSK, IN = "day", "golden", "dusk", "interior"

S = []  # base script (verbatim)
S.append(("s01", "In our town, you LOSE a word every time you lie.", [
    B("town", "drone", "pt:0,0,0"),
    B("street", "whip", "t5"),
    B("street", "ecu", "eli"),
], DAY, 0.45))
S.append(("s02", "Nobody knows why. It's just the rule.", [
    B("street", "push", "t6", faces={"t6": "blank"}),
    C("rule"),
    B("street", "low", "eli"),
], DAY, 0.5))
S.append(("s03", "My name is Eli. I'm eleven. I have never lost a word. Mostly.", [
    B("street", "tilt", "eli"),
    B("street", "orbit", "eli"),
    B("street", "cu", "eli", faces={"eli": "blank"}),
    B("street", "ecu", "eli", faces={"eli": "tired"}),
], DAY, 0.5))
S.append(("s04", 'Last week the baker told a customer his bread was fresh. It was not fresh. '
          'He lost the word "fresh." Now he just sells... bread. Sad bread.', [
    B("bakery", "wide", "bakery_sign"),
    B("bakery", "ots", "baker", over="t1", acts={"baker": "talk"}),
    B("bakery", "prop", "stall_bread"),
    B("bakery", "ecu", "baker", faces={"baker": "shocked"}),
    C("fresh"),
    B("bakery", "cu", "baker", faces={"baker": "sad"}),
    B("bakery", "dutch", "stall_bread"),
], DAY, 0.5))
S.append(("s05", 'Mrs. Pell said she loved her neighbor\'s singing. Gone. "Loved." '
          'Now she says she "tolerates" things.', [
    B("pell", "wide", "pt:15,7,1.8"),
    B("pell", "cu", "t2", acts={"t2": "sing"}),
    B("pell", "ots", "pell", over="t2", acts={"pell": "talk"}),
    B("pell", "ecu", "pell", faces={"pell": "shocked"}),
    C("loved"),
    B("pell", "cu", "pell", faces={"pell": "tired"}),
], DAY, 0.5))
S.append(("s06", "Everyone in town talks carefully now. Short sentences. Boring. HONEST.", [
    B("town", "drone", "pt:10,0,0"),
    B("street", "track", "t5"),
    B("street", "cu", "t6", faces={"t6": "blank"}),
    B("street", "high", "pt:-5,0,0"),
    B("street", "ecu", "t1", faces={"t1": "tired"}),
], DAY, 0.45))
S.append(("s07", "Except the mayor.", [
    B("plaza", "whip", "mayor"),
    B("plaza", "low", "mayor"),
], DAY, 0.45))
S.append(("s08", 'The mayor lied about the taxes. He lost "taxes." Then he lied about the roads. '
          'He lost "roads." Then the budget. Gone. By Monday he talked like a broken radio.', [
    B("plaza", "push", "mayor", acts={"mayor": "talk"}),
    C("taxes"),
    B("plaza", "cu", "mayor", faces={"mayor": "shocked"}),
    B("town", "high", "pt:-10,0,0"),
    B("plaza", "ecu", "mayor", faces={"mayor": "sad"}),
    B("plaza", "orbit", "mayor", acts={"mayor": "talk"}),
    B("plaza", "dutch", "mayor", acts={"mayor": "talk"}, faces={"mayor": "tired"}),
    B("plaza", "whip", "t3", faces={"t3": "blank"}),
], DAY, 0.5))
S.append(("s09", "On Tuesday, the town MONEY disappeared. All of it. Forty-one thousand coins, "
          "straight out of the town hall safe.", [
    B("plaza", "wide", "hall_sign"),
    B("safe", "push", "safe"),
    B("safe", "prop", "safe_in"),
    C("coins"),
    B("safe", "low", "mayor", faces={"mayor": "shocked"}),
    B("safe", "whip", "safe"),
], DAY, 0.5))
S.append(("s10", 'The mayor stood on the podium and said, "I have no idea where it went." '
          'He lost "idea." Then "where." Then "went." Then "it."', [
    B("plaza", "low", "mayor", acts={"mayor": "talk"}),
    B("plaza", "ots", "mayor", over="eli", acts={"mayor": "talk"}),
    B("plaza", "cu", "mayor", acts={"mayor": "talk"}),
    B("plaza", "ecu", "mayor", faces={"mayor": "shocked"}),
    B("plaza", "push", "t5", faces={"t5": "shocked", "t6": "shocked", "t1": "shocked"}),
    B("plaza", "ecu", "mayor", faces={"mayor": "sad"}),
    B("plaza", "dutch", "mayor", faces={"mayor": "tired"}),
], DAY, 0.55))
S.append(("s11", "By Wednesday, he had one word left.", [
    B("plaza", "pull", "mayor", faces={"mayor": "tired"}),
    B("plaza", "ecu", "mayor", faces={"mayor": "tired"}),
], GOLD, 0.6))
S.append(("s12", '"The."', [
    C("the"),
], GOLD, 0.9))
S.append(("s13", "So I did what nobody else would. I followed him.", [
    B("plaza", "cu", "eli", faces={"eli": "blank"}),
    B("follow", "track", "mayor"),
    B("follow", "low", "eli"),
], GOLD, 0.5))
S.append(("s14", 'He walked to the bakery. "The." He walked to the gate. "The." He walked to the field. '
          '"The." Everywhere he went, he stared at the ground.', [
    B("bakery_walk", "wide", "mayor"),
    B("bakery_walk", "ecu", "mayor", faces={"mayor": "tired"}),
    B("gate", "wide", "gate"),
    B("gate", "ecu", "mayor", faces={"mayor": "tired"}),
    B("field", "drone", "pt:-90,0,0"),
    B("field", "cu", "mayor", faces={"mayor": "tired"}),
    B("field", "high", "mayor"),
    B("field", "prop", "mayor_feet"),
], GOLD, 0.55))
S.append(("s15", "A man with one word left has to be very careful. One more lie costs him everything. "
          "So I knew he was about to tell the TRUTH.", [
    B("field", "orbit", "mayor", faces={"mayor": "tired"}),
    B("field", "ecu", "mayor", faces={"mayor": "sad"}),
    B("gate", "pull", "mayor"),
    B("field", "cu", "eli"),
    B("field", "push", "eli", faces={"eli": "neutral"}),
], DUSK, 0.55))
S.append(("s16", 'I stood in front of him and asked, "Mayor, where is the money?"', [
    B("corner", "wide", "pt:30,3,1.5"),
    B("corner", "ots", "mayor", over="eli"),
    B("corner", "cu", "eli", acts={"eli": "talk"}),
    C("where"),
], DUSK, 0.6))
S.append(("s17", 'He opened his mouth. Nothing came out. His eyes went wide. He had one word. '
          'And he used it. "The."', [
    B("corner", "ecu", "mayor", faces={"mayor": "talk"}),
    B("corner", "ots", "eli", over="mayor"),
    B("corner", "ecu", "mayor", faces={"mayor": "shocked"}),
    B("corner", "push", "mayor", faces={"mayor": "tired"}),
    B("corner", "low", "mayor", acts={"mayor": "talk"}),
    B("corner", "dutch", "mayor", faces={"mayor": "shocked"}),
], DUSK, 0.6))
S.append(("s18", "Then he lifted his arm. Slowly. And pointed. Not at the safe. Not at the hall. "
          "At the little house at the end of Carrot Street.", [
    B("corner", "low", "mayor", acts={"mayor": "point_slow"}),
    B("corner", "orbit", "mayor", acts={"mayor": "point"}),
    B("corner", "ots", "eli_house", over="mayor", acts={"mayor": "point"}),
    B("safe", "prop", "safe"),
    B("plaza", "wide", "hall_sign"),
    B("carrot", "push", "eli_house"),
    B("carrot", "whip", "carrot_sign"),
    B("carrot", "push", "eli_house"),
], DUSK, 0.55))
S.append(("s19", "My house.", [
    B("corner", "ecu", "eli", faces={"eli": "shocked"}, acts={"mayor": "point"}),
    B("carrot", "push", "eli_house"),
], DUSK, 0.8))
S.append(("s20", "I almost laughed. Then I remembered something. The rule only counts WORDS. "
          "Hands can lie all they want.", [
    B("corner", "cu", "eli", acts={"mayor": "point"}),
    B("corner", "ecu", "eli", faces={"eli": "blank"}, acts={"mayor": "point"}),
    C("words"),
    B("corner", "prop", "mayor_hand", acts={"mayor": "point"}),
    B("corner", "orbit", "mayor", acts={"mayor": "point"}, faces={"mayor": "blank"}),
], DUSK, 0.5))
S.append(("s21", "So I ran home anyway.", [
    B("carrot_run", "track", "eli"),
    B("carrot_run", "low", "eli"),
], DUSK, 0.6))
S.append(("s22", "Dad was at the kitchen table. He'd been quiet all week. I thought he was tired.", [
    B("kitchen", "wide", "dad"),
    B("kitchen", "ots", "dad", over="eli"),
    B("kitchen", "cu", "dad", faces={"dad": "tired"}),
    B("kitchen", "push", "dad", faces={"dad": "tired"}),
], IN, 0.5))
S.append(("s23", "He wasn't tired. He had said exactly zero words since Sunday.", [
    B("kitchen", "ecu", "dad", faces={"dad": "blank"}),
    C("zero"),
    B("kitchen", "dutch", "dad", faces={"dad": "blank"}),
], IN, 0.55))
S.append(("s24", 'I asked, "Dad? Where did you go on Tuesday night?"', [
    B("kitchen", "cu", "eli", acts={"eli": "talk"}),
    B("kitchen", "ots", "dad", over="eli"),
    B("kitchen", "ecu", "eli"),
], IN, 0.6))
S.append(("s25", 'He opened his mouth. Closed it. Opened it again. Nothing. Not even "the."', [
    B("kitchen", "ecu", "dad", faces={"dad": "talk"}),
    B("kitchen", "ecu", "dad", faces={"dad": "blank"}),
    B("kitchen", "ecu", "dad", faces={"dad": "talk"}),
    B("kitchen", "push", "dad", faces={"dad": "blank"}),
    B("kitchen", "high", "dad", faces={"dad": "blank"}),
], IN, 0.6))
S.append(("s26", "Under the table, something clinked. A bag. A heavy one.", [
    B("kitchen", "low", "bag"),
    B("kitchen", "prop", "bag"),
    B("kitchen", "ecu", "eli", faces={"eli": "shocked"}),
], IN, 0.6))
S.append(("s27", "Then the front door opened behind me. And the whole town was standing there.", [
    B("kitchen", "push", "door", door="opening"),
    B("kitchen", "ecu", "eli", faces={"eli": "shocked"}, door="open"),
    B("door", "wide", "door", door="open"),
    B("door", "push", "mayor", door="open"),
], IN, 0.6))
S.append(("s28", "Not one of them said a WORD.", [
    B("door", "ecu", "pell", door="open"),
    B("door", "ecu", "baker", door="open"),
    B("door", "ecu", "mayor", door="open"),
    B("door", "push", "door", door="open"),
], IN, 0.9))

# ---- extra beats (only used if needed, inserted before scene 20) ----
EXTRA = [
    # (insert_after_id, sentence)
    ("s03", ("e01", 'I tested the rule once. I told my teacher my dog ate my homework. '
             'I don\'t have a dog. I lost the word "dog." It\'s fine. I didn\'t need it.', [
        B("teacher", "ots", "t4", over="eli", acts={"t4": "talk"}),
        B("teacher", "cu", "eli", acts={"eli": "talk"}),
        B("teacher", "push", "t4", faces={"t4": "tired"}),
        C("dog"),
        B("teacher", "ecu", "eli", faces={"eli": "blank"}),
        B("teacher", "high", "eli", acts={"eli": "shrug"}),
    ], DAY, 0.5)),
    ("s05", ("e02", 'The mailman lied about the weather. He lost "sunny." Now every day is just... "a day."', [
        B("mail", "low", "t3", acts={"t3": "talk"}),
        B("mail", "sky", "t3"),
        B("mail", "ecu", "t3", faces={"t3": "shocked"}),
        C("sunny"),
        B("mail", "cu", "t3", faces={"t3": "tired"}),
    ], DAY, 0.5)),
    ("s14", ("e03", "I checked the bakery for clues. Just bread. Sad bread.", [
        B("bakery_check", "push", "eli"),
        B("bakery", "prop", "stall_bread"),
        B("bakery_check", "cu", "eli", faces={"eli": "tired"}),
    ], GOLD, 0.45)),
    ("e03", ("e04", "I checked the gate. Nothing. Just a gate.", [
        B("gate_check", "low", "eli"),
        B("gate", "prop", "gate"),
        B("gate_check", "cu", "eli", faces={"eli": "blank"}),
    ], GOLD, 0.45)),
    ("e04", ("e05", "I checked the field. Carrots. Rows of them. No money.", [
        B("field_check", "high", "eli"),
        B("field", "prop", "carrots"),
        B("field_check", "ecu", "eli", faces={"eli": "tired"}),
    ], GOLD, 0.5)),
]

# Note-card inserts: key -> (lines, struck_line_indexes)
CARDS = {
    "rule": (["THE RULE:", "LIE =", "LOSE A WORD"], []),
    "dog": (["DOG"], [0]),
    "fresh": (["FRESH", "BREAD"], [0]),
    "loved": (["LOVED", "TOLERATES"], [0]),
    "sunny": (["SUNNY", "A DAY."], [0]),
    "taxes": (["TAXES", "ROADS", "BUDGET"], [0, 1, 2]),
    "coins": (["41,000 COINS", "MISSING"], []),
    "the": (["“THE.”"], []),
    "where": (["WHERE IS", "THE MONEY?"], []),
    "words": (["ONLY", "WORDS", "COUNT."], []),
    "zero": (["WORDS SINCE", "SUNDAY:", "0"], []),
}


def build_script(use_extras):
    """Return ordered list of sentences, inserting the first `use_extras` extras."""
    order = list(S)
    for after, sent in EXTRA[:use_extras]:
        idx = [s[0] for s in order].index(after)
        order.insert(idx + 1, sent)
    return order
