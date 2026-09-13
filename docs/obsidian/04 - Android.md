# Android

Entry point тот же `main.py`; при `ANDROID_ARGUMENT` запускается `OkoMobileApp`.

Основной канал — WiFi TCP `192.168.4.1:1234`, резервный — USB OTG serial. KivyMD зафиксирован на 2.0.0, обязательны `materialyoucolor==3.0.4` и `materialshapes==0.3`.

При проблемах запуска читать `oko-startup.log` и `oko-mobile.log` в sandbox приложения. Все polling callback отменяются при отключении.
