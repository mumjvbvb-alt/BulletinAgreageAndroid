from dataclasses import dataclass, field
from typing import Dict, Optional

SPECIES = ("Blé Dur", "Blé Tendre", "Orge")

@dataclass(frozen=True)
class AnalysisRule:
    key: str
    label: str
    unit: str
    reference: str = ""

@dataclass
class CalculationResult:
    bonifications: Dict[str,float] = field(default_factory=dict)
    refactions: Dict[str,float] = field(default_factory=dict)
    observations: Dict[str,str] = field(default_factory=dict)
    total_bonification: float = 0.0
    total_refaction: float = 0.0
    price_to_discuss: bool = False
    refusal: bool = False
    reason: str = ""

RULES = {
 "Blé Dur": [
  AnalysisRule("poids_specifique","Poids spécifique","kg/hl","76 – 80"),
  AnalysisRule("humidite","Teneur en eau","%","≤ 17"),
  AnalysisRule("impurites_1","Impuretés 1ère catégorie","%","1 – 3"),
  AnalysisRule("impurites_2","Impuretés 2ème catégorie","%","≤ 10"),
  AnalysisRule("grains_casses","Grains cassés","%","≤ 5"),
  AnalysisRule("grains_boutes","Grains fortement boutés","%","≤ 5"),
  AnalysisRule("mitadin","Grains mitadinés","%",""),
  AnalysisRule("ble_tendre","Blé tendre dans blé dur","%","≤ 5")
 ],
 "Blé Tendre": [
  AnalysisRule("poids_specifique","Poids spécifique","kg/hl","74 – 77"),
  AnalysisRule("humidite","Teneur en eau","%","≤ 17"),
  AnalysisRule("impurites_1","Impuretés 1ère catégorie","%","1 – 3"),
  AnalysisRule("impurites_2","Impuretés 2ème catégorie","%","≤ 6"),
  AnalysisRule("grains_casses","Grains cassés","%","≤ 4"),
  AnalysisRule("grains_punaises","Grains punaisés","%","≤ 2")
 ],
 "Orge": [
  AnalysisRule("poids_specifique","Poids spécifique","kg/hl","58 – 62"),
  AnalysisRule("humidite","Teneur en eau","%","≤ 17"),
  AnalysisRule("impurites","Impuretés diverses","%","≤ 2"),
  AnalysisRule("ergot","Ergot","‰","≤ 1")
 ]
}

def parse_number(value: Optional[object]):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None

def format_number(value):
    return "" if value is None else f"{value:.2f}"

def calculate(species, values):
    # Legal formula implementation is intentionally isolated and will only
    # be enabled after verification against the official JO tables.
    result = CalculationResult()
    for key, raw in values.items():
        if parse_number(raw) is None:
            continue
        result.observations[key] = ""
    return result
