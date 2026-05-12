from re import compile
from .rules import DETECTORS
def dedupe(rows):
    best={}
    for code,name,pattern,score,hashcat,john,reasons in rows:
        key=(name,pattern)
        old=best.get(key)
        if not old or score>old[3]:
            best[key]=(code,name,pattern,score,hashcat,john,reasons)
    return best.values()
RULES=[
{"id":code,"name":name,"pattern":compile(pattern),"score":score,"hashcat":hashcat,"john":john,"reasons":reasons}
for code,name,pattern,score,hashcat,john,reasons in dedupe(DETECTORS)
]
def detect(value,strict=False,top=None):
    hits=[
    {k:v for k,v in rule.items() if k!="pattern"}
    for rule in RULES
    if rule["pattern"].fullmatch(value)
    ]
    hits.sort(key=lambda hit:(-hit["score"],hit["name"]))
    if strict and any(hit["score"]>=70 for hit in hits):
        hits=[hit for hit in hits if hit["score"]>=70]
    if top:
        hits=hits[:top]
    return hits
