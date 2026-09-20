package com.example.bulletinagreage

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.text.InputType
import android.util.AttributeSet
import android.view.Gravity
import android.widget.EditText
import android.widget.FrameLayout
import kotlin.math.roundToInt
import java.util.Locale

class BulletinPageLayout @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null
) : FrameLayout(context, attrs) {

    companion object {
        const val DESIGN_W = 1338f
        const val DESIGN_H = 1900f
    }

    private data class Spec(
        val id: Int, val x: Float, val y: Float, val w: Float, val h: Float,
        val numeric: Boolean = false, val readOnly: Boolean = false
    )

    private val specs = listOf(
        Spec(R.id.date, 710f, 276f, 340f, 45f),
        Spec(R.id.producteur, 205f, 366f, 315f, 38f),
        Spec(R.id.adresse, 185f, 402f, 345f, 38f),
        Spec(R.id.pointCollecte, 205f, 438f, 330f, 38f),
        Spec(R.id.agreur, 705f, 366f, 320f, 38f),
        Spec(R.id.quantite, 705f, 402f, 300f, 38f),
        Spec(R.id.numeroBon, 705f, 438f, 335f, 38f),
        Spec(R.id.carteIdentite, 110f, 1778f, 360f, 40f),
        Spec(R.id.poidsSpecifique, 655f, 640f, 105f, 30f, true),
        Spec(R.id.humidite, 655f, 674f, 105f, 32f, true),
        Spec(R.id.ergot, 655f, 708f, 105f, 32f, true),
        Spec(R.id.tamis, 655f, 750f, 105f, 95f, true),
        Spec(R.id.debris, 655f, 855f, 105f, 80f, true),
        Spec(R.id.grainesNuisibles, 655f, 941f, 105f, 60f, true),
        Spec(R.id.impur1Total, 655f, 1008f, 105f, 34f, true, true),
        Spec(R.id.grainsCasses, 655f, 1087f, 105f, 44f, true),
        Spec(R.id.grainsBoutes, 655f, 1138f, 105f, 44f, true),
        Spec(R.id.grainsRoux, 655f, 1188f, 105f, 42f, true),
        Spec(R.id.grainsMouchetes, 655f, 1238f, 105f, 66f, true),
        Spec(R.id.grainsPunaises, 655f, 1278f, 105f, 42f, true),
        Spec(R.id.grainsPiques, 655f, 1320f, 105f, 42f, true),
        Spec(R.id.impur2Total, 655f, 1369f, 105f, 36f, true, true),
        Spec(R.id.mitadin, 655f, 1420f, 105f, 45f, true),
        Spec(R.id.bleTendre, 655f, 1473f, 105f, 50f, true),
        Spec(R.id.mitadinTotal, 655f, 1526f, 105f, 48f, true, true)
    )

    private val fields = mutableMapOf<Int, EditText>()
    private var bonus = ""
    private var refaction = ""
    private var observation = ""
    private var rowAdjustments: Map<String, RowAdjustment> = emptyMap()
    private val page = PageCanvas(context)

    init {
        setWillNotDraw(false)
        setBackgroundColor(Color.WHITE)
        addView(page, LayoutParams(-1, -1))
        specs.forEach { addField(it) }
    }

    private fun addField(s: Spec) {
        val e = EditText(context)
        e.id = s.id
        e.setTextColor(Color.BLACK)
        e.setHintTextColor(Color.TRANSPARENT)
        e.background = null
        e.setPadding(2, 0, 2, 0)
        e.gravity = Gravity.CENTER
        e.textSize = if (s.numeric) 9f else 10f
        e.includeFontPadding = false
        e.maxLines = 1
        e.inputType = if (s.numeric)
            InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
        else InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        if (s.readOnly) {
            e.isFocusable = false
            e.isClickable = false
        }
        fields[s.id] = e
        addView(e, LayoutParams(1, 1))
    }

    fun field(id: Int): EditText = fields[id]!!

    fun setResult(result: CalculationResult, imp1: Double, imp2: Double, mitadin: Double) {
        bonus = String.format(Locale.FRANCE, "%.3f", result.bonification)
        refaction = String.format(Locale.FRANCE, "%.3f", result.refaction)
        observation = result.notes.firstOrNull() ?: ""
        rowAdjustments = result.rows
        field(R.id.impur1Total).setText(String.format(Locale.FRANCE, "%.3f", imp1))
        field(R.id.impur2Total).setText(String.format(Locale.FRANCE, "%.3f", imp2))
        field(R.id.mitadinTotal).setText(String.format(Locale.FRANCE, "%.3f", mitadin))
        page.invalidate()
    }

    fun populate(d: BulletinData) {
        val values = mapOf(
            R.id.producteur to d.producteur, R.id.adresse to d.adresse,
            R.id.pointCollecte to d.pointCollecte, R.id.agreur to d.agreur,
            R.id.date to d.date, R.id.quantite to d.quantite, R.id.numeroBon to d.numeroBon,
            R.id.carteIdentite to d.carteIdentite, R.id.poidsSpecifique to d.poids,
            R.id.humidite to d.humidite, R.id.ergot to d.ergot, R.id.tamis to d.tamis,
            R.id.debris to d.debris, R.id.grainesNuisibles to d.grainesNuisibles,
            R.id.impur1Total to d.impur1Total, R.id.grainsCasses to d.casses,
            R.id.grainsBoutes to d.boutes, R.id.grainsRoux to d.roux,
            R.id.grainsMouchetes to d.mouchetes, R.id.grainsPunaises to d.punaises,
            R.id.grainsPiques to d.piques, R.id.impur2Total to d.impur2Total,
            R.id.mitadin to d.mitadin, R.id.bleTendre to d.bleTendre,
            R.id.mitadinTotal to d.mitadinTotal
        )
        values.forEach { (id, value) -> field(id).setText(value) }
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = resources.displayMetrics.widthPixels
        val height = (width * DESIGN_H / DESIGN_W).roundToInt()
        setMeasuredDimension(width, height)
        page.measure(android.view.View.MeasureSpec.makeMeasureSpec(width, android.view.View.MeasureSpec.EXACTLY),
            android.view.View.MeasureSpec.makeMeasureSpec(height, android.view.View.MeasureSpec.EXACTLY))
        specs.forEach { s ->
            fields[s.id]?.measure(
                android.view.View.MeasureSpec.makeMeasureSpec((s.w * width / DESIGN_W).roundToInt(), android.view.View.MeasureSpec.EXACTLY),
                android.view.View.MeasureSpec.makeMeasureSpec((s.h * width / DESIGN_W).roundToInt(), android.view.View.MeasureSpec.EXACTLY)
            )
        }
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val scale = measuredWidth / DESIGN_W
        page.layout(0, 0, measuredWidth, measuredHeight)
        specs.forEach { s ->
            val x = (s.x * scale).roundToInt(); val y = (s.y * scale).roundToInt()
            val w = (s.w * scale).roundToInt(); val h = (s.h * scale).roundToInt()
            fields[s.id]?.layout(x, y, x + w, y + h)
        }
    }

    fun drawForPdf(canvas: Canvas, width: Int, height: Int) {
        measure(MeasureSpec.makeMeasureSpec(width, MeasureSpec.EXACTLY),
            MeasureSpec.makeMeasureSpec(height, MeasureSpec.EXACTLY))
        layout(0, 0, width, height)
        draw(canvas)
    }

    private inner class PageCanvas(context: Context) : android.view.View(context) {
        private val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.BLACK }
        private val thin = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK; style = Paint.Style.STROKE; strokeWidth = 1.4f
        }
        private val bold = Typeface.create("serif", Typeface.BOLD)
        private val normal = Typeface.create("serif", Typeface.NORMAL)
        private val italic = Typeface.create("serif", Typeface.ITALIC)

        override fun onDraw(canvas: Canvas) {
            val s = width / DESIGN_W
            canvas.save(); canvas.scale(s, s); drawPage(canvas); canvas.restore()
        }

        private fun txt(c: Canvas, text: String, x: Float, y: Float, size: Float,
                        align: Paint.Align = Paint.Align.LEFT, typeface: Typeface = normal) {
            p.style = Paint.Style.FILL; p.textSize = size; p.textAlign = align; p.typeface = typeface
            c.drawText(text, x, y, p)
        }

        private fun centered(c: Canvas, text: String, x: Float, y: Float, w: Float, size: Float,
                             typeface: Typeface = normal) =
            txt(c, text, x + w / 2f, y, size, Paint.Align.CENTER, typeface)

        private fun line(c: Canvas, x1: Float, y1: Float, x2: Float, y2: Float) =
            c.drawLine(x1, y1, x2, y2, thin)

        private fun rect(c: Canvas, l: Float, t: Float, r: Float, b: Float) =
            c.drawRect(l, t, r, b, thin)

        private fun drawLogo(c: Canvas, cx: Float, cy: Float) {
            val bmp = CompanyLogo.bitmap() ?: return
            val dst = android.graphics.RectF(cx - 48f, cy - 48f, cx + 48f, cy + 48f)
            c.drawBitmap(bmp, null, dst, null)
        }

        private fun dotted(c: Canvas, x1: Float, y: Float, x2: Float) {
            p.style = Paint.Style.STROKE; p.strokeWidth = 1.5f
            var x = x1
            while (x < x2) { c.drawLine(x, y, minOf(x + 4f, x2), y, p); x += 9f }
        }

        private fun drawPage(c: Canvas) {
            c.drawColor(Color.WHITE)
            drawLogo(c, 70f, 55f); drawLogo(c, DESIGN_W - 70f, 55f)
            centered(c, "OFFICE ALGERIEN INTERPROFESSIONNEL DES CEREALES", 115f, 78f, 1108f, 31f, bold)
            centered(c, "Coopérative de Céréales et des Légumes Secs de BATNA", 170f, 142f, 998f, 28f, bold)
            centered(c, "Bulletin d'Agréage", 330f, 205f, 678f, 38f, italic)
            txt(c, "Espèce :", 104f, 270f, 28f, Paint.Align.LEFT, bold)
            txt(c, "Blé Dur", 235f, 270f, 32f, Paint.Align.LEFT, italic)
            line(c, 230f, 276f, 365f, 276f)
            txt(c, "Date :", 700f, 270f, 28f, Paint.Align.LEFT, bold); dotted(c, 805f, 270f, 1030f)
            txt(c, "Nom du producteur :", 104f, 360f, 24f, Paint.Align.LEFT, bold); dotted(c, 380f, 360f, 535f)
            txt(c, "Adresse :", 104f, 397f, 24f, Paint.Align.LEFT, bold); dotted(c, 250f, 397f, 535f)
            txt(c, "Point de collecte :", 104f, 434f, 24f, Paint.Align.LEFT, bold); dotted(c, 340f, 434f, 535f)
            txt(c, "Nom de l'agréeur :", 700f, 360f, 24f, Paint.Align.LEFT, bold); dotted(c, 940f, 360f, 1050f)
            txt(c, "Quantité :", 700f, 397f, 24f, Paint.Align.LEFT, bold); dotted(c, 835f, 397f, 1010f)
            txt(c, "N° Bon d'entrée:", 700f, 434f, 24f, Paint.Align.LEFT, bold); dotted(c, 885f, 434f, 1050f)
            drawTable(c)
            txt(c, "Référence : Décret n°88-152 du 26 juillet 1988 fixant les barèmes de bonification et de réfaction", 104f, 1660f, 15f)
            txt(c, "applicables aux céréales et aux légumes secs. 1ère partie : Relations entre producteurs et organismes stockeurs.", 104f, 1681f, 15f)
            txt(c, "Producteur", 105f, 1740f, 22f, Paint.Align.LEFT, bold)
            txt(c, "N° de la carte d’identité", 105f, 1800f, 21f, Paint.Align.LEFT, bold)
            txt(c, "Agréeur", 1030f, 1740f, 22f, Paint.Align.CENTER, bold)
        }

        private fun drawTable(c: Canvas) {
            val x0=102f; val x1=530f; val x2=653f; val x3=760f; val x4=927f; val x5=1063f; val x6=1155f
            val ys = floatArrayOf(530f,638f,670f,710f,753f,828f,937f,1005f,1047f,1084f,1135f,1184f,1235f,1274f,1317f,1367f,1417f,1471f,1515f,1576f,1618f)
            rect(c,x0,ys[0],x6,ys.last())
            for (i in 1 until ys.size-1) line(c,x0,ys[i],x6,ys[i])
            line(c,x1,ys[0],x1,ys.last()); line(c,x2,ys[0],x2,ys.last()); line(c,x3,ys[0],x3,ys.last())
            line(c,x4,ys[0],x4,ys.last()); line(c,x5,ys[0],x5,ys.last())
            centered(c,"Paramètres",x0,575f,x1-x0,24f,bold)
            centered(c,"Limites",x1,557f,x2-x1,23f,bold); centered(c,"(sans",x1,582f,x2-x1,14f,bold)
            centered(c,"bonification ni",x1,599f,x2-x1,14f,bold); centered(c,"réfaction)",x1,616f,x2-x1,14f,bold)
            centered(c,"Valeurs",x2,575f,x3-x2,23f,bold)
            centered(c,"Bonification",x3,560f,x4-x3,21f,bold); centered(c,"(D.A.)",x3,585f,x4-x3,19f,bold)
            centered(c,"Réfaction",x4,560f,x5-x4,21f,bold); centered(c,"(D.A.)",x4,585f,x5-x4,19f,bold)
            centered(c,"Observation",x5,575f,x6-x5,20f,bold)
            row(c,638f,670f,"Poids spécifique (kg/hl)","[76 - 80]")
            row(c,670f,710f,"Teneur en eau (%)","≤ 17")
            row(c,710f,753f,"Ergot (‰)","≤ 1")
            vertical(c,"Impuretés 1ère catégorie",120f,752f,1005f)
            multiline(c,"Matières qui passent à travers\nle tamis 20 mm x2.1mm (%)",145f,790f,19f,bold)
            centered(c,"-",x1,805f,x2-x1,22f,bold)
            multiline(c,"Les débris végétaux et les\néléments minéraux (%)\nRetenus par le tamis 20 mm x2.1mm",145f,870f,18f,bold)
            centered(c,"-",x1,895f,x2-x1,22f,bold)
            row(c,937f,1005f,"Graines nuisibles (%)","≤ 0,25")
            row(c,1005f,1047f,"Total (%)","[1 - 3]")
            vertical(c,"Impuretés 2ème catégorie",120f,1047f,1417f)
            row(c,1047f,1084f,"Grains cassés (%)","≤ 5")
            row(c,1084f,1135f,"Grains fortement boutés (%)","≤ 5")
            row(c,1135f,1184f,"Grains Roux (%)","-")
            multiline(c,"Grains fortement mouchetés\n(%)",145f,1260f,18f,bold); centered(c,"-",x1,1270f,x2-x1,22f,bold)
            row(c,1274f,1317f,"Grains punaisés (%)","-")
            row(c,1317f,1367f,"Grains piqués (%)","-")
            row(c,1367f,1417f,"Total (%)","≤ 10")
            vertical(c,"Grains\nmitadinés",120f,1417f,1576f)
            row(c,1417f,1471f,"Grains mitadinés (%)","-")
            row(c,1471f,1515f,"Blé tendre dans blé dur (%)","≤ 5")
            row(c,1515f,1576f,"Total (%)","[10 - 20]")
            centered(c,"Total des Bonifications et Réfactions",x0,1603f,x2-x0,20f,bold)
            if (bonus.isNotEmpty()) centered(c,bonus,x3,1603f,x4-x3,21f,bold)
            if (refaction.isNotEmpty()) centered(c,refaction,x4,1603f,x5-x4,21f,bold)
            if (bonus.isNotEmpty() || refaction.isNotEmpty()) centered(c,observation.take(16),x5,1603f,x6-x5,13f)
        }

        private fun row(c:Canvas, top:Float, bottom:Float, label:String, limit:String, key:String?) {
            val cy=(top+bottom)/2f+7f
            txt(c,label,145f,cy,19f,Paint.Align.LEFT,bold)
            centered(c,limit,530f,cy,123f,20f,bold)
            key?.let {
                val a=rowAdjustments[it] ?: return@let
                if (a.bonification != 0.0) centered(c,String.format(Locale.FRANCE,"%.3f",a.bonification),760f,cy,167f,18f,bold)
                if (a.refaction != 0.0) centered(c,String.format(Locale.FRANCE,"%.3f",a.refaction),927f,cy,136f,18f,bold)
            }
        }

        private fun multiline(c:Canvas,text:String,x:Float,y:Float,size:Float,typeface:Typeface) {
            text.split("\n").forEachIndexed { i,s -> txt(c,s,x,y+i*(size+7f),size,Paint.Align.LEFT,typeface) }
        }

        private fun vertical(c:Canvas,text:String,cx:Float,top:Float,bottom:Float) {
            c.save(); c.rotate(-90f,cx,(top+bottom)/2f)
            text.split("\n").forEachIndexed { i,s ->
                txt(c,s,cx,(top+bottom)/2f - (text.length*4f) + i*22f,20f,Paint.Align.CENTER,bold)
            }
            c.restore()
        }
    }
}
