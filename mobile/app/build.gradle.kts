plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ru.aura.wellness"
    compileSdk = 34

    defaultConfig {
        applicationId = "ru.aura.wellness"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    // Подпись релиза: путь/пароли берутся из переменных окружения,
    // чтобы ключ и секреты не попадали в git. Без переменных сборка
    // остаётся debug-подписуемой (для локальных проверок).
    val ksPath = System.getenv("AURA_KEYSTORE")
    if (ksPath != null) {
        signingConfigs {
            create("release") {
                storeFile = file(ksPath)
                storePassword = System.getenv("AURA_KEYSTORE_PASS")
                keyAlias = System.getenv("AURA_KEY_ALIAS") ?: "aura"
                keyPassword = System.getenv("AURA_KEYSTORE_PASS")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (ksPath != null) signingConfig = signingConfigs.getByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.2")
    implementation("androidx.webkit:webkit:1.11.0")
}
