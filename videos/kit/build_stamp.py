"""Scene stamp (plain Python twin of build.scene_stamp): kit code + scene/config hash."""
import hashlib
from common import KIT, source_hash


def stamp(slug):
    h = hashlib.sha1(source_hash(slug, ("scene", "config")).encode())
    for p in sorted(KIT.glob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]
