"""Style B texture assignment (plain data, safe inside Blender's Python)."""
from common import ASSETS

TEX = ASSETS / "tex"

# which flat palette colours become which texture in Style B
TEXMAP = {
    "#8c8a5c": ("grass", 6.0), "#76784a": ("grass", 2.0), "#6b7044": ("grass", 2.0), "#858456": ("grass", 2.0),
    "#a68a66": ("dirt", 5.0), "#8f7656": ("dirt", 4.0), "#b8a282": ("cobble", 2.5), "#6e553e": ("dirt", 3.0),
    "#5c4532": ("dirt", 2.0),
    "#c8b08a": ("plaster", 3.0), "#b9a07c": ("plaster", 3.0), "#a88f72": ("plaster", 3.0), "#cdbb98": ("plaster", 3.0),
    "#9fa38a": ("plaster", 3.0), "#b59a86": ("plaster", 3.0), "#8fa0a8": ("plaster", 3.0), "#c2a88a": ("plaster", 3.0),
    "#d6bf92": ("plaster", 3.0), "#8b9aa6": ("plaster", 3.0), "#5f86a8": ("wood", 2.0), "#c9bfa8": ("stone", 3.0),
    "#c9b48e": ("plaster", 3.0),
    "#7a4a36": ("shingle", 2.0), "#6a5040": ("shingle", 2.0), "#5d4a3c": ("shingle", 2.0), "#80563c": ("shingle", 2.0),
    "#5a5f62": ("shingle", 2.0), "#6e4434": ("shingle", 2.0), "#7d4734": ("shingle", 2.0), "#5e4c3e": ("shingle", 2.0),
    "#4f4a52": ("shingle", 2.0), "#4a4440": ("shingle", 2.0),
    "#5b4030": ("wood", 1.5), "#7d6448": ("wood", 1.5), "#8a7052": ("wood", 1.5), "#6a4a30": ("wood", 1.5),
    "#5e4028": ("wood", 1.5), "#7a5534": ("wood", 1.5), "#8a6a4a": ("wood", 2.0), "#7a5c40": ("wood", 1.5),
    "#5e4430": ("wood", 1.5), "#6a4e36": ("wood", 1.5), "#7a5636": ("wood", 1.2), "#8a4436": ("wood", 2.0),
    "#4f3a2a": ("wood", 1.5), "#9a7a58": ("wood", 1.5), "#5e4a38": ("wood", 1.5), "#6d6252": ("stone", 2.0),
    "#8f877a": ("stone", 2.0), "#a39b8c": ("stone", 2.0), "#e2dccb": ("stone", 2.0), "#6e5e52": ("stone", 1.5),
    "#7c7a74": ("stone", 2.0), "#9a9488": ("stone", 2.0),
    "#5c4634": ("bark", 1.0), "#5f6b3e": ("leaves", 2.0), "#6a7244": ("leaves", 2.0), "#56603a": ("leaves", 2.0),
    "#6f7a48": ("leaves", 2.0), "#6d7a3c": ("leaves", 1.0),
    "#4a7a9a": ("water", 6.0), "#3f6f8f": ("water", 6.0),
}

# Style B brightens the muted palette a little so daylight reads sunny
B_TINT = {"#8c8a5c": "#7fa04e", "#76784a": "#6f9444", "#6b7044": "#678a3e", "#858456": "#86a052",
          "#a68a66": "#b89a72", "#5f6b3e": "#5d8a3a", "#6a7244": "#689440", "#56603a": "#4f7c34", "#6f7a48": "#76a04a",
          "#6d7a3c": "#6f9a3a", "#7a4a36": "#9a4a34", "#6a5040": "#7a5440", "#80563c": "#9a5c3a"}

