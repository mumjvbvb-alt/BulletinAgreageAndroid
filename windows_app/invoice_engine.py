from dataclasses import dataclass, field
from math import ceil
from typing import Optional

SPECIES=("Blé Dur","Blé Tendre","Orge")

@dataclass(frozen=True)
class Rule:
    key:str; label:str; unit:str; reference:str

@dataclass
class Calculation:
    rows:dict=field(default_factory=dict); bonus:float=0.0; refaction:float=0.0
    observation:str=""; price_to_discuss:bool=False; refused:bool=False; reason:str=""

RULES={
"Blé Dur":[
Rule("poids","Poids spécifique","kg/hl","76 – 80"),Rule("humidite","Teneur en eau","%","≤ 17"),
Rule("ergot","Ergot","‰","≤ 1"),Rule("tamis","Matières au tamis","%","—"),
Rule("debris","Débris végétaux et minéraux","%","—"),Rule("graines_nuisibles","Graines nuisibles","%","≤ 0,25"),
Rule("impur1","Impuretés 1ère catégorie","%","1 – 3"),Rule("casses","Grains cassés","%","≤ 5"),
Rule("boutes","Grains fortement boutés","%","≤ 5"),Rule("roux","Grains roux","%","—"),
Rule("mouchetes","Grains fortement mouchetés","%","—"),Rule("punaises","Grains punaisés","%","—"),
Rule("piques","Grains piqués","%","—"),Rule("impur2","Impuretés 2ème catégorie","%","≤ 10"),
Rule("mitadin","Grains mitadinés","%","10 – 20"),Rule("ble_tendre","Blé tendre dans blé dur","%","≤ 5"),
Rule("mitadin_total","Total mitadin","%","10 – 20")],
"Blé Tendre":[
Rule("poids","Poids spécifique","kg/hl","74 – 77"),Rule("humidite","Teneur en eau","%","≤ 17"),
Rule("ergot","Ergot","‰","≤ 1"),Rule("impur1","Impuretés 1ère catégorie","%","1 – 3"),
Rule("casses","Grains cassés","%","≤ 4"),Rule("boutes","Grains boutés","%","≤ 5"),
Rule("punaises","Grains punaisés","%","≤ 2"),Rule("impur2","Impuretés 2ème catégorie","%","≤ 6")],
"Orge":[Rule("poids","Poids spécifique","kg/hl","58 – 62"),Rule("humidite","Teneur en eau","%","≤ 17"),
Rule("impurites","Impuretés diverses","%","≤ 2"),Rule("ergot","Ergot","‰","≤ 1")]}

def num(v:object)->Optional[float]:
    if v is None or str(v).strip()=="": return None
    try:return float(str(v).strip().replace(",",".")) 
    except ValueError:return None

def fmt(v): return "" if v is None else f"{v:.2f}"
def tranche(excess,size): return max(0,ceil((excess-1e-9)/size))

def calc_bd(v):
    r=Calculation()
    def add(k,b=0,rfa=0): r.rows[k]=(b,rfa) if (b or rfa) else r.rows.get(k,(0,0)); r.bonus+=b; r.refaction+=rfa
    p=num(v.get("poids"))
    if p is not None:
        if p>80:
            b=tranche(min(p,82)-80,.25)*.15+tranche(min(max(p-82,0),1),.25)*.10+tranche(min(max(p-83,0),1),.25)*.05+tranche(max(p-84,0),.25)*.05
            add("poids",b=b)
        elif p<76 and p>=72:
            rfa=tranche(min(76-p,1),.25)*.10+tranche(min(max(75-p,0),1),.25)*.20+tranche(max(74-p,0),.25)*.30
            add("poids",rfa=rfa)
        elif p<72:r.observation="Poids spécifique inférieur à 72 kg/hl : lot hors critère sain, loyal et marchand."
    h=num(v.get("humidite"))
    if h is not None and h>17:r.observation="Teneur en eau supérieure à 17 % : lot hors limite."
    e=num(v.get("ergot"))
    if e is not None and e>1:r.observation="Présence d'ergot supérieure à 1 ‰ : lot hors limite."
    x=num(v.get("impur1"))
    if x is not None:
        if x<1:add("impur1",b=tranche(1-x,.25)*.125)
        elif x>3 and x<=6:add("impur1",rfa=tranche(x-3,.25)*.125)
        elif x>6:r.price_to_discuss=True;r.observation="Impuretés 1ère catégorie > 6 % : prix à débattre."
    x=num(v.get("casses"))
    if x is not None and x>5:add("casses",rfa=tranche(x-5,.25)*.075)
    x=num(v.get("boutes"))
    if x is not None and x>5:add("boutes",rfa=tranche(x-5,1)*.05)
    x=num(v.get("impur2"))
    if x is not None and 10<x<=20:add("impur2",rfa=tranche(x-10,1)*.50)
    elif x is not None and x>20:r.observation="Impuretés 2ème catégorie > 20 % : lot hors barème."
    x=num(v.get("mitadin"))
    if x is not None:
        if 0<=x<=10:add("mitadin",b=.25)
        elif 20<x<=70:add("mitadin",rfa=tranche(x-20,1)*.05)
        elif x>70:r.observation="Au-delà de 70 % de mitadin, paiement au prix du blé tendre."
    x=num(v.get("ble_tendre"))
    if x is not None and x>5:
        r.observation="Blé tendre > 5 % : réfaction selon la différence de prix blé dur/blé tendre." if x<=10 else "Blé tendre > 10 % : paiement au prix du blé tendre avec son barème."
    return r

def calc_bt(v):
    r=Calculation()
    def add(k,b=0,rfa=0): r.rows[k]=(b,rfa) if (b or rfa) else r.rows.get(k,(0,0)); r.bonus+=b; r.refaction+=rfa
    p=num(v.get("poids"))
    if p is not None:
        if p>77:
            b=tranche(min(p,78)-77,.25)*.10+tranche(min(max(p-78,0),2),.25)*.05+tranche(max(p-80,0),.25)*.02
            add("poids",b=b)
        elif p<74 and p>=69:
            rfa=tranche(min(74-p,2),.25)*.04+tranche(min(max(72-p,0),2),.25)*.10+tranche(max(70-p,0),.25)*.20
            add("poids",rfa=rfa)
        elif p<69:r.observation="Poids spécifique inférieur à 69 kg/hl : lot hors critère."
    h=num(v.get("humidite"))
    if h is not None and h>17:r.observation="Teneur en eau supérieure à 17 % : lot hors limite."
    e=num(v.get("ergot"))
    if e is not None and e>1:r.observation="Présence d'ergot supérieure à 1 ‰ : lot hors limite."
    x=num(v.get("impur1"))
    if x is not None:
        if x<1:add("impur1",b=tranche(1-x,.25)*.12)
        elif x>3 and x<=6:add("impur1",rfa=tranche(x-3,.25)*.12)
        elif x>6:r.price_to_discuss=True;r.observation="Impuretés 1ère catégorie > 6 % : prix à débattre."
    x=num(v.get("casses"))
    if x is not None and x>4:add("casses",rfa=tranche(x-4,.25)*.04)
    x=num(v.get("boutes"))
    if x is not None and x>5:add("boutes",rfa=tranche(x-5,.25)*.20)
    x=num(v.get("punaises"))
    if x is not None and x>2:
        if x<=10:add("punaises",rfa=tranche(x-2,.25)*.08)
        else:r.price_to_discuss=True;r.observation="Grains punaisés > 10 % : prix à débattre."
    x=num(v.get("impur2"))
    if x is not None and 6<x<=15:
        add("impur2",rfa=(tranche(min(x,10)-6,.25)*.05+tranche(max(x-10,0),.25)*.08))
    elif x is not None and x>15:r.observation="Impuretés 2ème catégorie > 15 % : lot hors barème."
    return r

def calc_orge(v):
    r=Calculation()
    def add(k,b=0,rfa=0): r.rows[k]=(b,rfa) if (b or rfa) else r.rows.get(k,(0,0)); r.bonus+=b; r.refaction+=rfa
    p=num(v.get("poids"))
    if p is not None:
        if p>62:add("poids",b=tranche(p-62,.5)*.24)
        elif p<58:add("poids",rfa=tranche(58-p,.5)*.12)
    x=num(v.get("impurites"))
    if x is not None and x>2:add("impurites",rfa=tranche(x-2,.5)*.12)
    e=num(v.get("ergot"))
    if e is not None and e>1:r.observation="Présence d'ergot supérieure à 1 ‰ : lot hors limite."
    h=num(v.get("humidite"))
    if h is not None and h>17:r.observation="Teneur en eau supérieure à 17 % : lot hors limite."
    return r

def calculate(species,values):
    return calc_bd(values) if species=="Blé Dur" else calc_bt(values) if species=="Blé Tendre" else calc_orge(values)
