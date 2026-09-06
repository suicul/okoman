"""Command registry for OKO БОД (Блок обработки данных).

All serial commands documented in the service manual.
Format: [Operator] [Space] [Operand] [Space] [Parameter]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommandType(Enum):
    """Category of command."""

    QUERY = "query"
    SET = "set"
    DEBUG = "debug"
    TEST = "test"
    CONTROL = "control"
    MAINTENANCE = "maintenance"


class ParamType(Enum):
    """Expected parameter type for a command."""

    NONE = "none"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    CHOICE = "choice"


@dataclass(frozen=True)
class CommandDef:
    """Definition of a single serial command."""

    name: str
    description: str
    command_type: CommandType
    syntax: str
    param_type: ParamType = ParamType.NONE
    choices: tuple[str, ...] = ()
    example: str = ""
    response_hint: str = ""


# ── Query commands ──────────────────────────────────────────────────────────

CMD_VER = CommandDef(
    name="VER",
    description="Версия прошивки",
    command_type=CommandType.QUERY,
    syntax="VER",
    example="VER",
    response_hint="Firmware Version: 2.2.0\\nBuild Date: Jan 15 2025",
)

CMD_SERIAL = CommandDef(
    name="serial",
    description="Серийный номер платы",
    command_type=CommandType.QUERY,
    syntax="serial",
    example="serial",
    response_hint="Serial: 002503",
)

CMD_SET_NO_PARAM = CommandDef(
    name="SET (все настройки)",
    description="Показать все текущие настройки",
    command_type=CommandType.QUERY,
    syntax="SET",
    example="SET",
)

# ── SET commands ────────────────────────────────────────────────────────────

CMD_SET_SPK_VOL = CommandDef(
    name="SET SpkVol",
    description="Установка громкости динамика",
    command_type=CommandType.SET,
    syntax="SET SpkVol <0.0-1.0>",
    param_type=ParamType.FLOAT,
    example="SET SpkVol 0.7",
)

CMD_SET_GSM_APN = CommandDef(
    name="SET GSM_APN",
    description="Точка доступа APN для SIM-карты",
    command_type=CommandType.SET,
    syntax="SET GSM_APN <apn>",
    param_type=ParamType.STRING,
    example="SET GSM_APN internet.provider.com",
)

CMD_SET_GSM_USER = CommandDef(
    name="SET GSM_USER",
    description="Логин SIM-карты",
    command_type=CommandType.SET,
    syntax="SET GSM_USER <login>",
    param_type=ParamType.STRING,
    example="SET GSM_USER login",
)

CMD_SET_GSM_PWD = CommandDef(
    name="SET GSM_PWD",
    description="Пароль SIM-карты",
    command_type=CommandType.SET,
    syntax="SET GSM_PWD <password>",
    param_type=ParamType.STRING,
    example="SET GSM_PWD password",
)

CMD_SET_MQTT_URL = CommandDef(
    name="SET MQTT_URL",
    description="Адрес MQTT-сервера (IP:порт)",
    command_type=CommandType.SET,
    syntax="SET MQTT_URL <ip:port>",
    param_type=ParamType.STRING,
    example="SET MQTT_URL mqtt.oko-server.com:1883",
)

CMD_SET_AS = CommandDef(
    name="SET AS",
    description="Сохранить настройки в EEPROM",
    command_type=CommandType.SET,
    syntax="SET AS",
    example="SET AS",
    response_hint="Настройки сохранены",
)

CMD_SET_REG = CommandDef(
    name="SET REG",
    description="Тип регистратора (4 или 8 каналов)",
    command_type=CommandType.SET,
    syntax="SET REG <4|8>",
    param_type=ParamType.CHOICE,
    choices=("4", "8"),
    example="SET REG 4",
)

CMD_SET_GPS = CommandDef(
    name="SET Gps",
    description="Режим GPS (GNSS/GLONASS)",
    command_type=CommandType.SET,
    syntax="SET Gps",
    param_type=ParamType.CHOICE,
    choices=("GNSS", "GLONASS"),
    example="SET Gps GNSS",
)

# ── DEBUG commands ──────────────────────────────────────────────────────────

CMD_DEBUG_ONLY_BUT = CommandDef(
    name="DEBUG ONLY BUT",
    description="Отладка кнопки (нажатия)",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ONLY BUT",
    example="DEBUG ONLY BUT",
    response_hint="The Button pressed N times",
)

CMD_DEBUG_ONLY_POS = CommandDef(
    name="DEBUG ONLY POS",
    description="Отладка GPS-позиции",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ONLY POS",
    example="DEBUG ONLY POS",
    response_hint="Time, Date, Lat, Lng, Vel",
)

CMD_DEBUG_ONLY_GSM = CommandDef(
    name="DEBUG ONLY GSM",
    description="Отладка GSM-модуля и MQTT",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ONLY GSM",
    example="DEBUG ONLY GSM",
    response_hint="[GSM] Signal: 18, Errors: 0",
)

CMD_DEBUG_ONLY_FOK = CommandDef(
    name="DEBUG ONLY FOK",
    description="Проверка связи с датчиками",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ONLY FOK",
    example="DEBUG ONLY FOK",
)

CMD_DEBUG_ONLY_FTG = CommandDef(
    name="DEBUG ONLY FTG",
    description="Лог событий оптических датчиков",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ONLY FTG",
    example="DEBUG ONLY FTG",
)

CMD_DEBUG_ON_PWR = CommandDef(
    name="DEBUG ON PWR",
    description="Отладка связи с блоком питания",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ON PWR",
    example="DEBUG ON PWR",
)

CMD_DEBUG_ON_GPS = CommandDef(
    name="DEBUG ON GPS",
    description="Отладка GPS (полный лог)",
    command_type=CommandType.DEBUG,
    syntax="DEBUG ON GPS",
    example="DEBUG ON GPS",
)

# ── TEST commands ───────────────────────────────────────────────────────────

CMD_TEST_ON = CommandDef(
    name="TEST ON",
    description="Включить тестовый режим",
    command_type=CommandType.TEST,
    syntax="TEST ON",
    example="TEST ON",
)

CMD_TEST_OFF = CommandDef(
    name="TEST OFF",
    description="Выключить тестовый режим",
    command_type=CommandType.TEST,
    syntax="TEST OFF",
    example="TEST OFF",
)

CMD_TEST_HW = CommandDef(
    name="TEST HW",
    description="Тест аппаратуры (VIBRO, SPK, GPSANT, FTG)",
    command_type=CommandType.TEST,
    syntax="TEST HW",
    example="TEST HW",
    response_hint="TST: Hardware test: VIBRO=2493, SPK=2535/2524, GPSANT=0, FTG=0",
)

CMD_PWR_TM = CommandDef(
    name="PWR TM",
    description="Телеметрия блока питания",
    command_type=CommandType.TEST,
    syntax="PWR TM <секунды>",
    param_type=ParamType.INT,
    example="pwr tm 15",
)

# ── SPK commands ────────────────────────────────────────────────────────────

CMD_SPK_P = CommandDef(
    name="SPK P",
    description="Воспроизвести звук (0-13)",
    command_type=CommandType.CONTROL,
    syntax="SPK P <номер>",
    param_type=ParamType.INT,
    example="SPK P 5",
    response_hint="0=тихий, 5=тревога, 13=макс",
)

# ── LED commands ────────────────────────────────────────────────────────────

CMD_LED_ALL = CommandDef(
    name="LED ALL",
    description="Управление всеми светодиодами",
    command_type=CommandType.CONTROL,
    syntax="LED ALL <мс_вкл> <мс_выкл> #",
    param_type=ParamType.STRING,
    example="LED ALL 1000 500 #",
)

# ── OUT commands (triggers to recorder) ────────────────────────────────────

CMD_OUT = CommandDef(
    name="OUT",
    description="Триггер на регистратор (1/2/4/8)",
    command_type=CommandType.CONTROL,
    syntax="OUT <номер>",
    param_type=ParamType.CHOICE,
    choices=("1", "2", "4", "8"),
    example="OUT 1",
)

# ── Sensor simulation ──────────────────────────────────────────────────────

CMD_EYES = CommandDef(
    name="EYES_1..3",
    description="Имитация: закрыть глаза",
    command_type=CommandType.TEST,
    syntax="EYES_<1-3>",
    param_type=ParamType.STRING,
    example="EYES_1",
    response_hint="Не вижу ваши глаза",
)

CMD_FACE = CommandDef(
    name="FACE_4",
    description="Имитация: отвернуться",
    command_type=CommandType.TEST,
    syntax="FACE_4",
    example="FACE_4",
    response_hint="Не вижу ваше лицо",
)

CMD_PHONE = CommandDef(
    name="PHONE5",
    description="Имитация: телефон у уха",
    command_type=CommandType.TEST,
    syntax="PHONE5",
    example="PHONE5",
    response_hint="Не отвлекайтесь на телефон",
)

CMD_SMOKE = CommandDef(
    name="SMOKE6",
    description="Имитация: курение",
    command_type=CommandType.TEST,
    syntax="SMOKE6",
    example="SMOKE6",
    response_hint="Пожалуйста, не курите за рулём",
)

# ── Maintenance commands ───────────────────────────────────────────────────

CMD_RST = CommandDef(
    name="RST",
    description="Перезагрузка устройства",
    command_type=CommandType.MAINTENANCE,
    syntax="RST",
    example="RST",
)

CMD_FIRMWARE_INIT = CommandDef(
    name="FIRMWARE INIT",
    description="Очистка прошивки (версии < 2.2.0)",
    command_type=CommandType.MAINTENANCE,
    syntax="FIRMWARE INIT",
    example="FIRMWARE INIT",
)

CMD_UPDATE_CLEAR = CommandDef(
    name="UPDATE CLEAR",
    description="Очистка (версии >= 2.2.0)",
    command_type=CommandType.MAINTENANCE,
    syntax="UPDATE CLEAR",
    example="UPDATE CLEAR",
)

CMD_TM_PURGE = CommandDef(
    name="TM PURGE",
    description="Очистка буфера телеметрии",
    command_type=CommandType.MAINTENANCE,
    syntax="TM PURGE",
    example="TM PURGE",
)

CMD_SET_SQUEEZE = CommandDef(
    name="SET SQUEEZE",
    description="Оптимизация памяти (>= 2.2.0)",
    command_type=CommandType.MAINTENANCE,
    syntax="SET SQUEEZE",
    example="SET SQUEEZE",
)

# ── Registries ──────────────────────────────────────────────────────────────

ALL_COMMANDS: list[CommandDef] = [
    # Query
    CMD_VER,
    CMD_SERIAL,
    CMD_SET_NO_PARAM,
    # SET
    CMD_SET_SPK_VOL,
    CMD_SET_GSM_APN,
    CMD_SET_GSM_USER,
    CMD_SET_GSM_PWD,
    CMD_SET_MQTT_URL,
    CMD_SET_AS,
    CMD_SET_REG,
    CMD_SET_GPS,
    # DEBUG
    CMD_DEBUG_ONLY_BUT,
    CMD_DEBUG_ONLY_POS,
    CMD_DEBUG_ONLY_GSM,
    CMD_DEBUG_ONLY_FOK,
    CMD_DEBUG_ONLY_FTG,
    CMD_DEBUG_ON_PWR,
    CMD_DEBUG_ON_GPS,
    # TEST
    CMD_TEST_ON,
    CMD_TEST_OFF,
    CMD_TEST_HW,
    CMD_PWR_TM,
    # Control
    CMD_SPK_P,
    CMD_LED_ALL,
    CMD_OUT,
    # Sensor simulation
    CMD_EYES,
    CMD_FACE,
    CMD_PHONE,
    CMD_SMOKE,
    # Maintenance
    CMD_RST,
    CMD_FIRMWARE_INIT,
    CMD_UPDATE_CLEAR,
    CMD_TM_PURGE,
    CMD_SET_SQUEEZE,
]

COMMANDS_BY_TYPE: dict[CommandType, list[CommandDef]] = {}
for _cmd in ALL_COMMANDS:
    COMMANDS_BY_TYPE.setdefault(_cmd.command_type, []).append(_cmd)


def build_command_string(cmd: CommandDef, param: str = "") -> str:
    """Build the raw serial command string.

    Handles different command types:
    - NONE: returns syntax as-is (e.g. "SET AS", "VER")
    - CHOICE/STRING/FLOAT/INT: appends param to syntax base
    """
    if cmd.param_type == ParamType.NONE:
        return cmd.syntax

    # Extract base command (before < if present, else full syntax)
    if "<" in cmd.syntax:
        base = cmd.syntax.split("<")[0].strip()
    else:
        base = cmd.syntax.strip()

    if param:
        return "{} {}".format(base, param).strip()
    return base
