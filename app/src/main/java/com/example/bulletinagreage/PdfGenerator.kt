package com.example.bulletinagreage

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.graphics.*
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class BulletinData(
    val producteur:String,val adresse:String,val pointCollecte:String,val agreur:String,val date:String,
    val quantite:String,val numeroBon:String,val carteIdentite:String,val poids:String,val humidite:String,
    val ergot:String,val tamis:String,val debris:String,val grainesNuisibles:String,val impur1Total:String,
    val casses:String,val boutes:String,val roux:String,val mouchetes:String,val punaises:String,val piques:String,
    val impur2Total:String,val mitadin:String,val bleTendre:String,val mitadinTotal:String
)

object PdfGenerator {
    fun generateAndOpen(activity: Activity, d: BulletinData, r: CalculationResult) {
        try {
            val doc = PdfDocument()
            val page = doc.startPage(PdfDocument.PageInfo.Builder(595,842,1).create())
            val c=page.canvas
            val border=Paint(1).apply{color=Color.BLACK;style=Paint.Style.STROKE;strokeWidth=.7f}
            val normal=Paint(1).apply{color=Color.BLACK;textSize=7f}
            val bold=Paint(1).apply{color=Color.BLACK;textSize=10f;typeface=Typeface.DEFAULT_BOLD}
            val small=Paint(1).apply{color=Color.BLACK;textSize=5.8f}
            fun t(s:String,x:Float,y:Float,p:Paint=normal){c.drawText(s.take(75),x,y,p)}
            fun cell(s:String,l:Float,top:Float,rr:Float,b:Float,p:Paint=small){c.drawRect(l,top,rr,b,border);t(s,l+2,top+(b-top)/2+2,p)}
            t("OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES",170f,22f,bold)
            t("Coopérative de Céréales et des Légumes Secs de BATNA",155f,35f)
            t("BULLETIN D'AGREAGE",236f,51f,bold)
            t("Espèce : Blé Dur",35f,66f);t("Date : "+d.date,420f,66f)
            cell("Nom du producteur : "+d.producteur,35f,74f,295f,91f)
            cell("Nom de l'agréeur : "+d.agreur,295f,74f,560f,91f)
            cell("Adresse : "+d.adresse,35f,91f,295f,108f)
            cell("Quantité : "+d.quantite,295f,91f,560f,108f)
            cell("Point de collecte : "+d.pointCollecte,35f,108f,295f,125f)
            cell("N° Bon d'entrée : "+d.numeroBon,295f,108f,560f,125f)

            val x0=35f;val x1=225f;val x2=310f;val x3=370f;val x4=425f;val x5=490f;val x6=560f
            var y=133f;val h=18f
            cell("Paramètres",x0,y,x1,y+h,bold);cell("Limites (sans bonification ni réfaction)",x1,y,x2,y+h,small)
            cell("Valeurs",x2,y,x3,y+h,bold);cell("Bonification",x3,y,x4,y+h,small);cell("Réfaction",x4,y,x5,y+h,small);cell("Observation",x5,y,x6,y+h,small);y+=h
            fun row(a:String,b:String,v:String){cell(a,x0,y,x1,y+h);cell(b,x1,y,x2,y+h);cell(v,x2,y,x3,y+h);cell("",x3,y,x4,y+h);cell("",x4,y,x5,y+h);cell("",x5,y,x6,y+h);y+=h}
            row("Poids spécifique (kg/hl)","[76 - 80]",d.poids)
            row("Teneur en eau (%)","≤ 17",d.humidite)
            row("Ergot (‰)","≤ 1",d.ergot)
            row("IMPURETES 1ère CATEGORIE","","")
            row("Matières passant au tamis 20 × 2,1 mm","-",d.tamis)
            row("Débris végétaux / éléments minéraux","-",d.debris)
            row("Graines nuisibles (%)","≤ 0,25",d.grainesNuisibles)
            row("Total (%)","[1 - 3]",d.impur1Total)
            row("IMPURETES 2ème CATEGORIE","","")
            row("Grains cassés (%)","≤ 5",d.casses)
            row("Grains fortement boutés (%)","≤ 5",d.boutes)
            row("Grains roux (%)","-",d.roux)
            row("Grains fortement mouchetés (%)","-",d.mouchetes)
            row("Grains punaisés (%)","-",d.punaises)
            row("Grains piqués (%)","-",d.piques)
            row("Total (%)","≤ 10",d.impur2Total)
            row("GRAINS MITADINES","","")
            row("Grains mitadinés (%)","-",d.mitadin)
            row("Blé tendre dans blé dur (%)","≤ 5",d.bleTendre)
            row("Total (%)","[10 - 20]",d.mitadinTotal)
            cell("TOTAL DES BONIFICATIONS ET REFACTIONS",x0,y,x2,y+25,bold)
            cell(String.format(Locale.FRANCE,"%.3f",r.bonification),x2,y,x3,y+25)
            cell(String.format(Locale.FRANCE,"%.3f",r.refaction),x3,y,x4,y+25)
            cell("SOLDE "+String.format(Locale.FRANCE,"%.3f",r.total),x4,y,x6,y+25)
            y+=34
            t("Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction",35f,y,small)
            t("applicables aux céréales et aux légumes secs. 1ère partie : Relations entre producteurs et organismes stockeurs.",35f,y+9,small)
            t("Producteur",80f,y+30);t("N° de la carte d’identité : "+d.carteIdentite,210f,y+30);t("Agréeur",475f,y+30)
            doc.finishPage(page)

            val name="Bulletin_Agreage_"+SimpleDateFormat("yyyyMMdd_HHmmss",Locale.US).format(Date())+".pdf"
            val uri:Uri
            if(Build.VERSION.SDK_INT>=29){
                val v=ContentValues().apply{put(MediaStore.Downloads.DISPLAY_NAME,name);put(MediaStore.Downloads.MIME_TYPE,"application/pdf");put(MediaStore.Downloads.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS+"/BulletinAgreage")}
                uri=activity.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,v) ?: error("Impossible de créer le fichier")
                activity.contentResolver.openOutputStream(uri).use{doc.writeTo(it)}
            }else{
                val f=java.io.File(activity.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS),name)
                f.outputStream().use{doc.writeTo(it)}
                uri=Uri.fromFile(f)
            }
            doc.close()
            Toast.makeText(activity,"PDF enregistré : Téléchargements/BulletinAgreage",Toast.LENGTH_LONG).show()
            activity.startActivity(Intent(Intent.ACTION_VIEW).apply{setDataAndType(uri,"application/pdf");addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)})
        }catch(e:Exception){Toast.makeText(activity,"Erreur PDF : "+e.message,Toast.LENGTH_LONG).show()}
    }
}
