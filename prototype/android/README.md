# Відновлений Android-прототип KOPANKA

Це знімок старого прототипу для відновлення тестової збірки, а не реалізація затвердженої карти 512×512.

Джерело: раніше завантажений архів `KOPANKA_2.0_source (1).zip`. Взято активні `app/src/main/java/com/kopanka/MainActivity.java`, `AndroidManifest.xml`, `styles.xml` та `app/build.gradle`. У вихідному архіві бракувало кореневих файлів Gradle; вони відновлені тут. Інші історичні копії MainActivity не включено, щоб уникнути плутанини.

У прототипі є старі ігрові екрани й герой. Вони збережені тільки для перевірки того, що проєкт збирається. Поточні рішення про нову карту визначені `../../docs/CURRENT_STAGE.md` та `../../docs/DECISIONS.md`. Архів 2.4 є окремим візуальним референсом і не застосований до цього знімка.

## Збірка

Потрібні JDK 17, Android SDK Platform 35, Gradle 8.9 і доступ до Google Maven. Із кореня цього каталогу:

```sh
gradle :app:assembleDebug
```

Тестовий APK після успішної збірки: `app/build/outputs/apk/debug/app-debug.apk`. Підпис релізної збірки й перевірка на телефоні — окремі кроки. Стан збірки показує workflow `Prototype Android debug APK` у GitHub Actions.
