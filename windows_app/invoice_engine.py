from dataclasses import dataclass, field
from math import ceil
from typing import Optional

SPECIES=("Blé Dur","Blé Tendre","Orge")

@dataclass(frozen=True)
class Rule:
    key:str; label:str; unit:str; reference:str

@dataclass
class Calculation:
    rows:dict=field(default_factory=dict)
    observations:dict=field(default_factory=dict)
    bonus:float=0.0; refaction:float=0.0
    observation:str=""; price_to_discuss:bool=False; refused:bool=False; reason:str=""

RULES={
"Blé Dur":[
 Rule("poids","Poids spécifique","kg/hl","76 – 80"),
 Rule("humidite","Teneur en eau","%","≤ 17"),
 Rule("ergot","Ergot","‰","≤ 1"),
 Rule("tamis","Matières qui passent à travers le tamis 20 mm x 2,1 mm","%","—"),
 Rule("debris","Débris végétaux et éléments minéraux retenus par le tamis 20 mm x 2,1 mm","%","—"),
 Rule("graines_nuisibles","Graines nuisibles","%","≤ 0,25"),
 Rule("impur1","Impuretés 1ère catégorie — Total","%","1 – 3"),
 Rule("casses","Grains cassés","%","≤ 5"),
 Rule("boutes","Grains fortement boutés","%","≤ 5"),
 Rule("roux","Grains roux","%","—"),
 Rule("mouchetes","Grains fortement mouchetés","%","—"),
 Rule("punaises","Grains punaisés","%","—"),
 Rule("piques","Grains piqués","%","—"),
 Rule("impur2","Impuretés 2ème catégorie — Total","%","≤ 10"),
 Rule("mitadin","Grains mitadinés","%","10 – 20"),
 Rule("ble_tendre","Blé tendre dans blé dur","%","≤ 5"),
 Rule("mitadin_total","Mitadin brut — Total","%","10 – 20")],
"Blé Tendre":[
 Rule("poids","Poids spécifique","kg/hl","74 – 77"),
 Rule("humidite","Teneur en eau","%","≤ 17"),
 Rule("ergot","Ergot","‰","≤ 1"),
 Rule("tamis","Matières qui passent à travers le tamis 20 mm x 2,1 mm","%","—"),
 Rule("debris","Débris végétaux et éléments minéraux retenus par le tamis 20 mm x 2,1 mm","%","—"),
 Rule("graines_nuisibles","Graines nuisibles","%","≤ 0,25"),
 Rule("impur1","Impuretés 1ère catégorie — Total","%","1 – 3"),
 Rule("casses","Grains cassés","%","≤ 4"),
 Rule("punaises","Grains punaisés","%","≤ 2"),
 Rule("boutes_forts","Grains fortement boutés","%","—"),
 Rule("boutes_faibles","Grains faiblement boutés","%","—"),
 Rule("mouchetes","Grains fortement mouchetés","%","—"),
 Rule("graines_betail","Graines étrangères utilisables pour le bétail","%","—"),
 Rule("impur2","Impuretés 2ème catégorie — Total","%","≤ 6")],
"Orge":[
 Rule("poids","Poids spécifique","kg/hl","58 – 62"),
 Rule("ergot","Ergot","‰","≤ 1"),
 Rule("grains_sans_valeur","Grains sans valeur","%","—"),
 Rule("impurites","Matières inertes","%","—"),
 Rule("impurites_total","Impuretés diverses — Total","%","≤ 2")]}

def num(v:object)->Optional[float]:
    if v is None or str(v).strip()=="": return None
    try:return float(str(v).strip().replace(",",".")) 
    except (ValueError,TypeError): return None

def fmt(v):
    return "" if v is None else f"{v:.2f}"

def tranche(excess,size):
    return max(0,ceil((excess-1e-9)/size))

def _add(r,key,b=0.0,rf=0.0):
    if b or rf:
        old=r.rows.get(key,(0.0,0.0)); r.rows[key]=(old[0]+b,old[1]+rf)
    r.bonus+=b; r.refaction+=rf

def _obs(r,key,text):
    r.observations[key]=text
    r.observation=text

def calc_bd(v):
    r=Calculation()
    p=num(v.get("poids"))
    if p is not None:
        if p>80:
            _add(r,"poids",b=tranche(min(p,82)-80,.25)*.15)
            _add(r,"poids",b=tranche(min(max(p-82,0),1),.25)*.10)
            _add(r,"poids",b=tranche(min(max(p-83,0),1),.25)*.05)
            _add(r,"poids",b=tranche(max(p-84,0),.25)*.05)
        elif 72<=p<76:
            _add(r,"poids",rf=tranche(min(76-p,1),.25)*.10)
            _add(r,"poids",rf=tranche(min(max(75-p,0),1),.25)*.20)
            _add(r,"poids",rf=tranche(max(74-p,0),.25)*.30)
        elif p<72:
            _obs(r,"poids","Poids spécifique inférieur à 72 kg/hl.")
    h=num(v.get("humidite"))
    if h is not None and h>17:_obs(r,"humidite","Teneur en eau supérieure à 17 %.")
    e=num(v.get("ergot"))
    if e is not None:
        if e<=0.01: pass
        elif e<=0.10:_add(r,"ergot",rf=.20)
        elif e<=0.50:_add(r,"ergot",rf=.40)
        elif e<=1.00:_add(r,"ergot",rf=.60)
        else:r.price_to_discuss=True; _obs(r,"ergot","Ergot supérieur à 1 ‰ : prix à débattre.")
    x=num(v.get("impur1"))
    if x is not None:
        if x<1:_add(r,"impur1",b=tranche(1-x,.25)*.125)
        elif x>3 and x<=6:_add(r,"impur1",rf=tranche(x-3,.25)*.125)
        elif x>6:r.price_to_discuss=True; _obs(r,"impur1","Impuretés 1ère catégorie > 6 % : prix à débattre.")
    x=num(v.get("casses"))
    if x is not None and x>5:_add(r,"casses",rf=tranche(x-5,.25)*.075)
    x=num(v.get("boutes"))
    if x is not None and x>5:_add(r,"boutes",rf=min(.50,tranche(x-5,1)*.05))
    x=num(v.get("impur2"))
    if x is not None and 10<x<=20:_add(r,"impur2",rf=tranche(x-10,1)*.50)
    elif x is not None and x>20:_obs(r,"impur2","Impuretés 2ème catégorie > 20 %.")
    x=num(v.get("mitadin"))
    if x is not None:
        if 0<=x<=10:_add(r,"mitadin",b=.25)
        elif 20<x<=70:_add(r,"mitadin",rf=tranche(x-20,1)*.05)
        elif x>70:_obs(r,"mitadin","Mitadin > 70 % : paiement au prix du blé tendre.")
    x=num(v.get("ble_tendre"))
    if x is not None and x>5:
        if x<=10:_add(r,"ble_tendre",rf=tranche(x-5,.25)*.05)
        else:_obs(r,"ble_tendre","Blé tendre > 10 % : paiement au prix du blé tendre.")
    return r

def calc_bt(v):
    r=Calculation()
    p=num(v.get("poids"))
    if p is not None:
        if p>77:
            _add(r,"poids",b=tranche(min(p,78)-77,.25)*.10)
            _add(r,"poids",b=tranche(min(max(p-78,0),2),.25)*.05)
            _add(r,"poids",b=tranche(max(p-80,0),.25)*.02)
        elif 69<=p<74:
            _add(r,"poids",rf=tranche(min(74-p,2),.25)*.04)
            _add(r,"poids",rf=tranche(min(max(72-p,0),2),.25)*.10)
            _add(r,"poids",rf=tranche(max(70-p,0),.25)*.20)
        elif p<69:_obs(r,"poids","Poids spécifique inférieur à 69 kg/hl.")
    h=num(v.get("humidite"))
    if h is not None and h>17:_obs(r,"humidite","Teneur en eau supérieure à 17 %.")
    e=num(v.get("ergot"))
    if e is not None:
        if e<=0.01: pass
        elif e<=0.10:_add(r,"ergot",rf=.20)
        elif e<=0.50:_add(r,"ergot",rf=.40)
        elif e<=1.00:_add(r,"ergot",rf=.60)
        else:r.price_to_discuss=True; _obs(r,"ergot","Ergot supérieur à 1 ‰ : prix à débattre.")
    x=num(v.get("impur1"))
    if x is not None:
        if x<1:_add(r,"impur1",b=tranche(1-x,.25)*.12)
        elif x>3 and x<=6:_add(r,"impur1",rf=tranche(x-3,.25)*.12)
        elif x>6:r.price_to_discuss=True; _obs(r,"impur1","Impuretés 1ère catégorie > 6 % : prix à débattre.")
    x=num(v.get("casses"))
    if x is not None and x>4:_add(r,"casses",rf=tranche(x-4,.25)*.04)
    x=num(v.get("boutes_forts"))
    if x is not None and x>0:_add(r,"boutes_forts",rf=tranche(x,.25)*.40)
    x=num(v.get("boutes_faibles"))
    if x is not None and x>0:_add(r,"boutes_faibles",rf=tranche(x,.25)*.20)
    x=num(v.get("punaises"))
    if x is not None:
        if x>2 and x<=10:_add(r,"punaises",rf=tranche(x-2,.25)*.08)
        elif x>10:r.price_to_discuss=True; _obs(r,"punaises","Grains punaisés > 10 % : prix à débattre.")
    x=num(v.get("impur2"))
    if x is not None and 6<x<=15:
        _add(r,"impur2",rf=tranche(min(x,10)-6,.25)*.05+tranche(max(x-10,0),.25)*.08)
    elif x is not None and x>15:_obs(r,"impur2","Impuretés 2ème catégorie > 15 %.")
    return r

def calc_orge(v):
    r=Calculation()
    p=num(v.get("poids"))
    if p is not None:
        if p>62:_add(r,"poids",b=tranche(p-62,.5)*.24)
        elif p<58:_add(r,"poids",rf=tranche(58-p,.5)*.12)
    x=num(v.get("impurites_total"))
    if x is None:x=num(v.get("impurites"))
    if x is not None and x>2:_add(r,"impurites_total",rf=tranche(x-2,.5)*.12)
    e=num(v.get("ergot"))
    if e is not None and e>1:r.price_to_discuss=True; _obs(r,"ergot","Ergot supérieur à 1 ‰ : prix à débattre.")
    return r

def calculate(species,values):
    return calc_bd(values) if species=="Blé Dur" else calc_bt(values) if species=="Blé Tendre" else calc_orge(values)
