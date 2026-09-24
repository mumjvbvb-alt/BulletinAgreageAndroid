import os, sys, time
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app import MainWindow, HistoryDialog, SettingsDialog, LayoutDialog
from invoice_engine import calculate

OUT=Path("screenshots")
OUT.mkdir(exist_ok=True)

app=QApplication(sys.argv)
w=MainWindow()
w.resize(1600,950)

# Realistic sample invoice data
w.species.setCurrentText("Blé Dur")
w.producer.setCurrentText("Ahmed Benali")
w.address.setText("Douar El Menia, Maghnia")
w.idcard.setText("123456789012345")
w.agreer.setText("Mohamed Ait")
w.quantity.setText("250.00")
w.point.setText("Point de collecte Batna")
w.bon.setText("2025")
w.status.setCurrentText("ACCEPTED")
w.analysis_fields["poids"].setText("80.25")
w.analysis_fields["humidite"].setText("12.50")
w.analysis_fields["impur1"].setText("2.50")
w.analysis_fields["casses"].setText("1.20")
w.update_preview()

def grab(widget,name):
    widget.repaint()
    app.processEvents()
    widget.grab().save(str(OUT/name))

grab(w,"01_saisie_et_apercu.png")

# History dialog
w.db.save_invoice(w.collect(), None)
h=HistoryDialog(w.db,w)
h.resize(1000,600)
grab(h,"02_historique.png")
h.close()

# Settings dialog
s=SettingsDialog(w.db,w)
s.resize(720,520)
grab(s,"03_parametres.png")
s.close()

# Layout dialog
d=LayoutDialog(w.preview,w)
d.resize(650,500)
grab(d,"04_mise_en_page.png")
d.close()

w.close()
app.quit()
