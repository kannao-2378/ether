"""Small offline syllable/stress references, usable when future cards are created."""
import json,re
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def references():
    path=Path(__file__).parent/'resources/mainline_pronunciation.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}

def enrich(details,english):
    refs=references();key=english.strip().casefold()
    if key in refs:
        for field in ('syllables','stress'):
            if not details.get(field) and refs[key].get(field):details[field]=refs[key][field]
    elif not details.get('ipa_us') and not details.get('pronunciation_parts'):
        words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",english)
        ignored={'i','you','we','they','he','she','it','a','an','the','to','of','am','is','are','be','do','does','did'}
        candidates=[w for w in words if w.casefold() in refs and w.casefold() not in ignored] or [w for w in words if w.casefold() in refs]
        if candidates:
            word=candidates[0];ref=refs[word.casefold()]
            details['pronunciation_parts']=[dict(en=word,ipa='',syllables=ref['syllables'],stress=ref.get('stress',''))]
    return details
