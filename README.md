# ОКО БОД Manager

**Менеджер устройства БОД (Блок обработки данных)** — кроссплатформенное приложение для управления устройством ОКО через USB (serial) и WiFi (TCP).

![Platform](https://img.shields.io/badge/platform-Windows%207%2B%20%7C%20Linux%20%7C%20Android-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Требования](#-требования)
- [Установка](#-установка)
- [Запуск](#-запуск)
- [Сборка](#-сборка)
- [Использование](#-использование)
- [Архитектура](#-архитектура)
- [Тестирование](#-тестирование)
- [Поддержка](#-поддержка)

---

## ✨ Возможности

### Подключение
- **USB (Serial)** — подключение по COM-порту с автоопределением скорости (baud rate)
- **WiFi (TCP)** — подключение по сети к устройству (порт 20000)
- Автообнаружение устройств при подключении

### Интерфейс
- **Обзор** — статус устройства, LED-индикаторы, информация о прошивке, настройках
- **Диагностика** — тест аппаратуры (VIBRO, SPK, GPS, оптические датчики), тест динамика
- **Конфигурация** — настройка GSM (APN, логин, пароль), MQTT, громкости, типа регистратора
- **Калибровка** — пошаговый мастер калибровки оптических датчиков
- **Мониторинг** — реалтайм GPS, GSM сигнал, журнал событий
- **Терминал** — ручной ввод команд с автоподсказками

### Дополнительно
- Экспорт/импорт конфигурации в JSON
- Валидация всех полей ввода
- Логирование в файл
- Кроссплатформенность: Windows 7+, Linux, Android

---

## 📋 Требования

### Desktop (Windows/Linux)
- Python 3.8+
- PyQt5 >= 5.15.0
- pyserial >= 3.5
- pyinstaller >= 5.0

### Mobile (Android)
- Python 3.8+
- kivy >= 2.2.0
- buildozer (для сборки APK)
- Android SDK + NDK (для сборки APK)

---

## 📦 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd oko
```

### 2. Установка зависимостей

```bash
# Desktop
pip install -r requirements.txt

# Mobile (опционально)
pip install kivy buildozer
```

### 3. Настройка прав доступа к COM-порту (Linux)

```bash
# Добавьте текущего пользователя в группу dialout
sudo usermod -aG dialout $USER

# Перезагрузитесь или перелогиньтесь
```

---

## 🚀 Запуск

### Desktop

```bash
python main.py
```

### Mobile (для тестирования на ПК)

```bash
python oko_mobile/main.py
```

---

## 📦 Сборка

### Desktop — Windows 7 (релиз 1.0, onefile)

Полевые ноутбуки — Windows 7, собираются **два одиночных EXE** (x86 и x64,
без установки, без DLL рядом) через GitHub Actions:

- `oko-manager-win7-x64` — для 64-бит Win7 SP1+;
- `oko-manager-win7-x86` — для 32-бит (работает и на 64-бит).

Запуск: push в `main`/`master`, тег `v*` или вручную (Actions → Build Windows EXE).
Артефакты лежат 90 дней.

Почему именно так (важно, не менять наугад):

- Python **3.8.10** — последний с поддержкой Win7 (3.9+ требует Windows 8.1+);
- PyInstaller **5.13.2** — последний с Win7-совместимым bootloader (6.x не стартует на Win7);
- PyQt5 **5.15.9**, pyserial 3.5 — см. `requirements-win7.txt`.

Локальная сборка для текущей ОС (проверка spec, НЕ для Win7):

```bash
python build.py          # dist/oko_manager.exe (onefile)
python build.py --clean  # очистить build/dist
```

### Mobile — Android (релиз 1.0)

- WiFi — основной канал (ТД платы `OKO_XXXXXX`, `192.168.4.1:1234`);
- USB OTG — резерв (кнопка на экране подключения).

APK собирается в CI (buildozer работает только на Linux): Actions →
Build Android APK. Артефакт `oko-manager-android`, minSdk 21 (Android 5.0).

Локально (Linux/WSL):

```bash
pip install "cython==0.29.36" buildozer
buildozer android debug   # dist/*.apk
```

---

## 📖 Использование

### Подключение по USB

1. Подключите устройство ОКО к ПК через USB
2. Выберите порт в выпадающем списке (или дождитесь автоподключения)
3. Нажмите "Подключить"
4. Приложение автоматически запросит версию, серийный номер, GPS, GSM и настройки

### Подключение по WiFi

Плата поднимает точку доступа `OKO_XXXXXX` (XXXXXX — серийник платы,
пароль `222333444`). Подключите ноутбук к этой сети, затем:

1. Переключитесь на "WiFi (TCP)" в панели подключения
2. IP уже подставлен: `192.168.4.1`, порт `1234`
3. Нажмите "Подключить" — дальше автоопрос (VER/serial/SET/POS/GSM) идёт сам

### Конфигурация

1. Перейдите на вкладку "Конфигурация"
2. Заполните поля:
   - **GSM**: APN, логин, пароль SIM-карты
   - **MQTT**: адрес сервера (IP:порт)
   - **Устройство**: громкость, тип регистратора, режим GPS
3. Нажмите "Применить" для каждой секции
4. Нажмите "Сохранить всё (SET AS)" для записи в EEPROM

### Экспорт/Импорт

- **Экспорт**: сохраните текущую конфигурацию в JSON-файл
- **Импорт**: загрузите конфигурацию из JSON-файла в поля

---

## 🏗 Архитектура

```
oko/
├── oko_app/                    # Основное приложение
│   ├── core/                   # Ядро (общее для desktop/mobile)
│   │   ├── serial_worker.py    # Работа с serial-портом
│   │   ├── commands.py         # Реестр команд устройства
│   │   ├── permissions.py      # Проверка прав доступа
│   │   ├── logger.py           # Логирование
│   │   └── validators.py       # Валидация ввода
│   ├── transport/              # Абстракция транспорта
│   │   └── __init__.py         # SerialTransport + TcpTransport
│   ├── ui/                     # Desktop UI (PyQt5)
│   │   ├── main_window.py      # Главное окно
│   │   ├── connection_panel.py # Панель подключения
│   │   ├── dashboard.py        # Обзор устройства
│   │   ├── diagnostics.py      # Диагностика
│   │   ├── configuration.py    # Конфигурация
│   │   ├── calibration.py      # Калибровка
│   │   ├── live_monitor.py     # Мониторинг
│   │   ├── terminal.py         # Терминал
│   │   └── theme.py            # Тема оформления
│   └── resources/              # Ресурсы (иконки и т.д.)
├── oko_mobile/                 # Мобильная версия (Kivy)
│   └── main.py                 # Mобильный UI
├── tests/                      # Тесты
│   ├── test_serial_reader.py   # Тесты serial worker
│   ├── test_validators.py      # Тесты валидаторов
│   └── test_transport.py       # Тесты транспорта
├── main.py                     # Точка входа (desktop)
├── build.py                    # Сборка desktop
├── build_mobile.py             # Сборка mobile
├── build.spec                  # PyInstaller spec
├── requirements.txt            # Зависимости
└── generate_icon.py            # Генерация иконки
```

### Ключевые компоненты

- **SerialWorker** — управление serial-подключением, очередь команд, парсинг ответов
- **TcpTransport** — WiFi-подключение через TCP/IP
- **CommandDef** — реестр всех команд устройства с типами параметров
- **ConfigValidator** — валидация полей конфигурации

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
PYTHONPATH=. python tests/test_serial_reader.py
PYTHONPATH=. python tests/test_validators.py
PYTHONPATH=. python tests/test_transport.py

# Или через pytest (если установлен)
pip install pytest
pytest tests/ -v
```

---

## 🛠 Разработка

### Добавление новой команды

1. Отредактируйте `oko_app/core/commands.py`
2. Добавьте `CommandDef` в соответствующую категорию
3. Добавьте команду в список `ALL_COMMANDS`
4. Добавьте обработку ответа в `SerialWorker._parse_line()`

### Поддержка нового транспорта

1. Создайте класс в `oko_app/transport/`
2. Наследуйтесь от `BaseTransport`
3. Реализуйте методы: `connect()`, `disconnect()`, `send()`, `scan()`
4. Подключите в `ConnectionPanel`

---

## 📄 Лицензия

© Гореловский Иван Александрович

---

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте лог-файл (если настроен)
2. Убедитесь, что устройство подключено корректно
3. Проверьте права доступа к порту (Linux)
4. Создайте issue в репозитории

### Полезные команды (Linux)

```bash
# Проверить доступные порты
ls -la /dev/ttyUSB* /dev/ttyACM*

# Добавить пользователя в группу dialout
sudo usermod -aG dialout $USER

# Проверить права
ls -la /dev/ttyUSB0
```

