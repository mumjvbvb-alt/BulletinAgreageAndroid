package com.example.bulletinagreage

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64

object CompanyLogo {
    private const val DATA = "$data"
    fun bitmap(): Bitmap {
        val bytes = Base64.decode(DATA, Base64.DEFAULT)
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }
}
