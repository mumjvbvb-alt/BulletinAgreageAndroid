from invoice_engine import calculate

assert calculate("Blé Dur",{"poids":"80"}).bonus==0
assert calculate("Blé Dur",{"poids":"80.25"}).bonus==0.15
assert calculate("Blé Dur",{"impur1":"2"}).bonus==0
assert calculate("Blé Dur",{"impur1":"0.50"}).bonus==0.25
assert calculate("Blé Dur",{"casses":"5.25"}).refaction==0.075
assert calculate("Blé Dur",{"boutes":"17"}).refaction==0.50
assert calculate("Blé Dur",{"ergot":"0.20"}).refaction==0.40
assert calculate("Blé Dur",{"ergot":"1.20"}).price_to_discuss

assert calculate("Blé Tendre",{"poids":"77.25"}).bonus==0.10
assert calculate("Blé Tendre",{"casses":"4.25"}).refaction==0.04
assert calculate("Blé Tendre",{"boutes_forts":"0.25"}).refaction==0.40
assert calculate("Blé Tendre",{"boutes_faibles":"0.25"}).refaction==0.20
assert calculate("Blé Tendre",{"punaises":"10.25"}).price_to_discuss

assert calculate("Orge",{"poids":"62.5"}).bonus==0.24
assert calculate("Orge",{"impurites_total":"2.5"}).refaction==0.12
assert calculate("Orge",{"ergot":"1.1"}).price_to_discuss

print("engine tests passed")
