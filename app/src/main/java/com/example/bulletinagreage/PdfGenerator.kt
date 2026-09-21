package com.example.bulletinagreage

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
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
    val impur2Total:String,val mitadin:String,val bleTendre:String,val mitadinTotal:String,
    val decisionRefused:Boolean = false,
    val stickers: BulletinPageLayout.StickerConfig = BulletinPageLayout.StickerConfig(
        690f, 548f, 1f, 690f, 650f, 1f
    )
)

object PdfGenerator {
    fun generateAndOpen(activity: Activity, d: BulletinData, r: CalculationResult) {
        try {
            val doc = PdfDocument()
            val page = doc.startPage(PdfDocument.PageInfo.Builder(595, 842, 1).create())
            val editor = BulletinPageLayout(activity)
            editor.populate(d)
            editor.setDecision(d.decisionRefused)
            editor.applyStickerConfig(d.stickers)
            editor.setStickerTexts(d.priceNoticeText, d.refusalNoticeText)
            val imp1 = d.impur1Total.replace(',', '.').toDoubleOrNull() ?: 0.0
            val imp2 = d.impur2Total.replace(',', '.').toDoubleOrNull() ?: 0.0
            val mit = d.mitadinTotal.replace(',', '.').toDoubleOrNull() ?: 0.0
            editor.setResult(r, imp1, imp2, mit)

            val c: Canvas = page.canvas
            c.drawColor(Color.WHITE)
            c.save()
            c.scale(595f / BulletinPageLayout.DESIGN_W, 846f / BulletinPageLayout.DESIGN_H)
            editor.drawForPdf(c, BulletinPageLayout.DESIGN_W.toInt(), BulletinPageLayout.DESIGN_H.toInt())
            c.restore()
            doc.finishPage(page)

            val name = "Bulletin_Agreage_" +
                    SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date()) + ".pdf"
            val uri: Uri
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, name)
                    put(MediaStore.Downloads.MIME_TYPE, "application/pdf")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/BulletinAgreage")
                }
                uri = activity.contentResolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                ) ?: error("Impossible de créer le fichier")
                activity.contentResolver.openOutputStream(uri).use { doc.writeTo(it) }
            } else {
                val file = java.io.File(
                    activity.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS), name
                )
                file.outputStream().use { doc.writeTo(it) }
                uri = Uri.fromFile(file)
            }
            doc.close()
            Toast.makeText(activity, "PDF enregistré dans Téléchargements/BulletinAgreage", Toast.LENGTH_LONG).show()
            activity.startActivity(Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/pdf")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            })
        } catch (e: Exception) {
            Toast.makeText(activity, "Erreur PDF : " + e.message, Toast.LENGTH_LONG).show()
        }
    }
}
