package com.example.bulletinagreage
import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import java.util.Locale
class MainActivity : Activity() {
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState); setContentView(R.layout.activity_main)
  findViewById<Button>(R.id.calculer).setOnClickListener { calculer() }
  findViewById<Button>(R.id.genererPdf).setOnClickListener { PdfGenerator.generateAndOpen(this, collectForm(), calculer()) }
 }
 private fun calculer(): CalculationResult {
  val poids=value(R.id.poidsSpecifique); val humidite=value(R.id.humidite); val ergot=value(R.id.ergot)
  val impuretes1=(value(R.id.tamis)?:0.0)+(value(R.id.debris)?:0.0)+(value(R.id.grainesNuisibles)?:0.0)
  val casses=value(R.id.grainsCasses)?:0.0; val boutes=value(R.id.grainsBoutes)?:0.0
  val impuretes2=casses+boutes+(value(R.id.grainsRoux)?:0.0)+(value(R.id.grainsMouchetes)?:0.0)+(value(R.id.grainsPunaises)?:0.0)+(value(R.id.grainsPiques)?:0.0)
  val mitadin=value(R.id.mitadin)?:0.0; val bleTendre=value(R.id.bleTendre)?:0.0; val mitadinTotal=mitadin+bleTendre
  findViewById<EditText>(R.id.impur1Total).setText(format(impuretes1)); findViewById<EditText>(R.id.impur2Total).setText(format(impuretes2)); findViewById<EditText>(R.id.mitadinTotal).setText(format(mitadinTotal))
  val result=CalculateurBleDur.calculer(poids,humidite,ergot,impuretes1,casses,boutes,impuretes2,mitadinTotal,bleTendre,value(R.id.differencePrix))
  val lines=mutableListOf("BONIFICATION : ${format(result.bonification)} DA","RÉFACTION : ${format(result.refaction)} DA","SOLDE : ${format(result.total)} DA","Impuretés 1ère catégorie : ${format(impuretes1)} %","Impuretés 2ème catégorie : ${format(impuretes2)} %","Mitadin brut : ${format(mitadinTotal)} %","Blé tendre : ${format(bleTendre)} %")
  if(humidite!=null&&humidite>17) lines+="⚠ Humidité > 17 %"; if(ergot!=null&&ergot>1) lines+="⚠ Ergot > 1 ‰"; lines+=result.notes.map{"⚠ $it"}
  findViewById<TextView>(R.id.resultat).text=lines.joinToString("\n"); return result
 }
 private fun collectForm()=BulletinData(text(R.id.producteur),text(R.id.adresse),text(R.id.pointCollecte),text(R.id.agreur),text(R.id.date),text(R.id.quantite),text(R.id.numeroBon),text(R.id.carteIdentite),text(R.id.poidsSpecifique),text(R.id.humidite),text(R.id.ergot),text(R.id.tamis),text(R.id.debris),text(R.id.grainesNuisibles),text(R.id.impur1Total),text(R.id.grainsCasses),text(R.id.grainsBoutes),text(R.id.grainsRoux),text(R.id.grainsMouchetes),text(R.id.grainsPunaises),text(R.id.grainsPiques),text(R.id.impur2Total),text(R.id.mitadin),text(R.id.bleTendre),text(R.id.mitadinTotal))
 private fun text(id:Int)=findViewById<EditText>(id).text.toString().trim()
 private fun value(id:Int)=text(id).replace(',','.').toDoubleOrNull()
 private fun format(v:Double)=String.format(Locale.FRANCE,"%.3f",v)
}