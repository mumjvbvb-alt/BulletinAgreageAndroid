from invoice_engine import calculate
assert calculate("Blé Dur",{"poids":"80"}).bonus==0
assert calculate("Blé Dur",{"poids":"80.25"}).bonus==0.15
assert calculate("Blé Dur",{"impur1":"2"}).bonus==0
assert calculate("Blé Dur",{"impur1":"0.50"}).bonus==0.25
assert calculate("Blé Tendre",{"poids":"77.25"}).bonus==0.10
assert calculate("Orge",{"poids":"62.5"}).bonus==0.24
assert calculate("Orge",{"impurites":"2.5"}).refaction==0.12
print("engine tests passed")
