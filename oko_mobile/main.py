#!/usr/bin/env python3
"""OKO Service Tool — Mobile (Android) version using KivyMD.

Shares core logic (commands, protocol) with desktop but uses
touch-friendly KivyMD UI. Primary connection: WiFi (TCP).
Secondary: USB serial (via usb4a on Android).
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import traceback

# Add project root to path for shared core imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.lang import Builder
from kivy.utils import get_color_from_hex
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDListItem, MDListItemHeadlineText, MDListItemSupportingText
from kivymd.uix.list import MDListItemLeadingIcon, MDListItemTrailingIcon
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

# ── Shared color palette ────────────────────────────────────────────────────
from oko_mobile.theme import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER, BORDER_ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_ACCENT,
    ACCENT, ACCENT_HOVER, DANGER, SUCCESS, WARNING,
    LED_POWER, LED_GPS, LED_GSM, LED_OPTICS, LED_OFF,
)

# ── KV Stylesheet ───────────────────────────────────────────────────────────
KVStyleSheet = f"""
#:import get_color_from_hex kivy.utils.get_color_from_hex

<MDScreenManager>
    md_bg_color: get_color_from_hex("{BG_PRIMARY}")

<MDBottomNavigation>
    panel_color: get_color_from_hex("{BG_SECONDARY}")
    text_color_normal: get_color_from_hex("{TEXT_SECONDARY}")
    text_color_active: get_color_from_hex("{ACCENT}")
    icon_color_active: get_color_from_hex("{ACCENT}")

<MDTopAppBar>
    md_bg_color: get_color_from_hex("{BG_SECONDARY}")
    theme_text_color: "Custom"
    text_color: get_color_from_hex("{TEXT_ACCENT}")

<MDCard>
    md_bg_color: get_color_from_hex("{BG_SECONDARY}")
    line_color: get_color_from_hex("{BORDER}")
    style: "elevated"
    elevation: 0
    padding: dp(16)
    spacing: dp(8)

<MDLabel>
    theme_text_color: "Custom"
    text_color: get_color_from_hex("{TEXT_PRIMARY}")

<MDButton>
    style: "filled"

<MDButtonText>
    theme_text_color: "Custom"
    text_color: get_color_from_hex("{BG_PRIMARY}")

<MDTextField>
    mode: "outlined"
    line_color_normal: get_color_from_hex("{BORDER}")
    line_color_focus: get_color_from_hex("{ACCENT}")
    hint_text_color_normal: get_color_from_hex("{TEXT_SECONDARY}")
    hint_text_color_focus: get_color_from_hex("{ACCENT}")
    text_color_normal: get_color_from_hex("{TEXT_PRIMARY}")
    text_color_focus: get_color_from_hex("{TEXT_PRIMARY}")
    fill_color_normal: get_color_from_hex("{BG_TERTIARY}")
    fill_color_focus: get_color_from_hex("{BG_TERTIARY}")

<MDListItem>
    md_bg_color: get_color_from_hex("{BG_SECONDARY}")

<MDListItemHeadlineText>
    theme_text_color: "Custom"
    text_color: get_color_from_hex("{TEXT_PRIMARY}")

<MDListItemSupportingText>
    theme_text_color: "Custom"
    text_color: get_color_from_hex("{TEXT_SECONDARY}")
"""


# ── KV Screen Layouts ───────────────────────────────────────────────────────

KV_CONNECTION = f"""
ConnectionScreen:

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(16)
        padding: dp(24)

        Image:
            source: "oko_icon.png"
            size_hint_y: None
            height: dp(96)
            allow_stretch: True
            keep_ratio: True

        MDLabel:
            text: "ОКО Service Tool"
            font_style: "Headline"
            role: "large"
            halign: "center"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("{TEXT_ACCENT}")

        MDLabel:
            text: "Сервисное обслуживание БОД"
            halign: "center"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("{TEXT_SECONDARY}")

        MDCard:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(12)

            MDLabel:
                text: "Подключение по WiFi"
                font_style: "Title"
                role: "medium"
                theme_text_color: "Custom"
                text_color: get_color_from_hex("{TEXT_ACCENT}")

            MDTextField:
                id: ip_field
                text: "192.168.4.1"
                hint_text: "IP-адрес устройства"
                icon_left: "lan"

            MDTextField:
                id: port_field
                text: "1234"
                hint_text: "Порт"
                icon_left: "ethernet"

            MDButton:
                size_hint_y: None
                height: dp(48)
                style: "filled"
                pos_hint: {{"center_x": 0.5}}
                on_release: root.do_connect()

                MDButtonText:
                    text: "Подключиться по WiFi"
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("{BG_PRIMARY}")

            MDButton:
                size_hint_y: None
                height: dp(48)
                style: "outlined"
                pos_hint: {{"center_x": 0.5}}
                on_release: root.do_connect_usb()

                MDButtonText:
                    text: "USB OTG (резерв)"
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("{TEXT_ACCENT}")

        MDLabel:
            id: status_label
            text: "Ожидание подключения"
            halign: "center"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("{TEXT_SECONDARY}")
"""

KV_DASHBOARD = f"""
DashboardScreen:

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Обзор"
            left_action_items: [["logout", lambda x: root.disconnect()]]

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

                # LED indicators row
                MDCard:
                    orientation: "horizontal"
                    padding: dp(12)
                    spacing: dp(16)
                    size_hint_y: None
                    height: dp(60)

                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        MDLabel:
                            text: "●"
                            font_style: "Display"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{LED_POWER}")
                        MDLabel:
                            text: "Power"
                            halign: "center"
                            font_size: "10sp"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")

                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        MDLabel:
                            id: led_gps
                            text: "●"
                            font_style: "Display"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{LED_OFF}")
                        MDLabel:
                            text: "GPS"
                            halign: "center"
                            font_size: "10sp"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")

                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        MDLabel:
                            id: led_gsm
                            text: "●"
                            font_style: "Display"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{LED_OFF}")
                        MDLabel:
                            text: "GSM"
                            halign: "center"
                            font_size: "10sp"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")

                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        MDLabel:
                            text: "●"
                            font_style: "Display"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{LED_OFF}")
                        MDLabel:
                            text: "Optics"
                            halign: "center"
                            font_size: "10sp"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")

                # Device info card
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Информация об устройстве"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Прошивка:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: ver_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Серийный:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: serial_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "GPS:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: gps_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "GSM:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: gsm_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                # Settings card
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Настройки"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Адрес сервера:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: mqtt_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "APN:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: apn_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Регистратор:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: rec_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")
"""

KV_DIAGNOSTICS = f"""
DiagnosticsScreen:

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Диагностика"

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

                # HW Test
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Тест аппаратуры"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDLabel:
                        id: hw_status
                        text: "Не выполнялся"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_SECONDARY}")

                    MDButton:
                        id: btn_hw_test
                        style: "filled"
                        pos_hint: {{"center_x": 0.5}}
                        on_release: root.do_hw_test()

                        MDButtonText:
                            text: "TEST HW"

                # Speaker test
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Тест динамика"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDLabel:
                        id: spk_status
                        text: "Не выполнялся"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_SECONDARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)
                        size_hint_y: None
                        height: dp(48)

                        MDButton:
                            style: "filled"
                            on_release: root.do_test_on()

                            MDButtonText:
                                text: "TEST ON"

                        MDButton:
                            style: "outlined"
                            on_release: root.do_test_off()

                            MDButtonText:
                                text: "TEST OFF"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")

                # Output test
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Тест выходов"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)
                        size_hint_y: None
                        height: dp(48)

                        MDButton:
                            style: "filled"
                            on_release: root.do_out("1")

                            MDButtonText:
                                text: "OUT 1"

                        MDButton:
                            style: "outlined"
                            on_release: root.do_out("2")

                            MDButtonText:
                                text: "OUT 2"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)
                        size_hint_y: None
                        height: dp(48)

                        MDButton:
                            style: "filled"
                            on_release: root.do_out("4")

                            MDButtonText:
                                text: "OUT 4"

                        MDButton:
                            style: "outlined"
                            on_release: root.do_out("8")

                            MDButtonText:
                                text: "OUT 8"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")
"""

KV_CONFIGURATION = f"""
ConfigurationScreen:

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Конфигурация"
            left_action_items: [["refresh", lambda x: root.reread()]]

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

                # GSM section
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "GSM"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDTextField:
                        id: apn_field
                        hint_text: "APN"
                        icon_left: "web"

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)

                        MDTextField:
                            id: gsm_user_field
                            hint_text: "Логин"
                            icon_left: "account"

                        MDTextField:
                            id: gsm_pass_field
                            hint_text: "Пароль"
                            icon_left: "lock"
                            password: True

                    MDButton:
                        style: "filled"
                        pos_hint: {{"center_x": 0.5}}
                        on_release: root.apply_gsm()

                        MDButtonText:
                            text: "Применить GSM"

                # MQTT section
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Сервер"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDTextField:
                        id: mqtt_field
                        hint_text: "Адрес сервера (IP:порт)"
                        icon_left: "server-network"

                    MDButton:
                        style: "filled"
                        pos_hint: {{"center_x": 0.5}}
                        on_release: root.apply_mqtt()

                        MDButtonText:
                            text: "Применить сервер"

                # Device section
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Устройство"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)

                        MDTextField:
                            id: vol_field
                            hint_text: "Громкость"
                            input_filter: "int"
                            icon_left: "volume-high"

                        MDTextField:
                            id: rec_field
                            hint_text: "Тип регистратора"
                            icon_left: "record"

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)

                        MDButton:
                            style: "filled"
                            on_release: root.apply_device()

                            MDButtonText:
                                text: "Применить"

                        MDButton:
                            style: "outlined"
                            on_release: root.save_all()

                            MDButtonText:
                                text: "Сохранить всё"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")

                # Export/Import
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Экспорт / Импорт"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: dp(8)
                        size_hint_y: None
                        height: dp(48)

                        MDButton:
                            style: "outlined"
                            on_release: root.export_config()

                            MDButtonText:
                                text: "Экспорт JSON"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")

                        MDButton:
                            style: "outlined"
                            on_release: root.import_config()

                            MDButtonText:
                                text: "Импорт JSON"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("{TEXT_ACCENT}")
"""

KV_MONITOR = f"""
MonitorScreen:

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Мониторинг"
            left_action_items: [["play", lambda x: root.start_monitor()]]

        MDScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

                # GPS card
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "GPS / ГЛОНАСС"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Широта:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: lat_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Долгота:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: lon_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Спутники:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: sats_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                # GSM card
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "GSM / SIM"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Оператор:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: operator_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "Сигнал:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: signal_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint_y: None
                        height: dp(36)
                        MDLabel:
                            text: "SIM:"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_SECONDARY}")
                        MDLabel:
                            id: sim_value
                            text: "—"
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("{TEXT_PRIMARY}")

                # Event log card
                MDCard:
                    orientation: "vertical"
                    spacing: dp(8)

                    MDLabel:
                        text: "Журнал событий"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                    MDLabel:
                        id: log_text
                        text: ""
                        size_hint_y: None
                        height: dp(200)
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_PRIMARY}")
"""

KV_TERMINAL = f"""
TerminalScreen:

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Терминал"

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(16)
            spacing: dp(8)

            # Command output
            MDCard:
                orientation: "vertical"
                padding: dp(8)
                size_hint_y: 0.7

                MDLabel:
                    id: terminal_output
                    text: ""
                    size_hint_y: None
                    height: dp(400)
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("{TEXT_PRIMARY}")

            # Command input
            MDBoxLayout:
                orientation: "horizontal"
                spacing: dp(8)
                size_hint_y: None
                height: dp(56)

                MDTextField:
                    id: cmd_field
                    hint_text: "Введите команду..."
                    icon_left: "console"
                    on_text_validate: root.send_command()

                MDButton:
                    style: "filled"
                    on_release: root.send_command()

                    MDButtonText:
                        text: ">"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{BG_PRIMARY}")

            # Quick commands
            MDBoxLayout:
                orientation: "horizontal"
                spacing: dp(8)
                size_hint_y: None
                height: dp(48)

                MDButton:
                    style: "outlined"
                    on_release: root.quick_cmd("VER")

                    MDButtonText:
                        text: "VER"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                MDButton:
                    style: "outlined"
                    on_release: root.quick_cmd("POS")

                    MDButtonText:
                        text: "POS"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                MDButton:
                    style: "outlined"
                    on_release: root.quick_cmd("GSM")

                    MDButtonText:
                        text: "GSM"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")

                MDButton:
                    style: "outlined"
                    on_release: root.quick_cmd("SET")

                    MDButtonText:
                        text: "SET"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("{TEXT_ACCENT}")
"""


# ── Screens ─────────────────────────────────────────────────────────────────

class ConnectionScreen(MDScreen):
    """WiFi connection screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None

    def set_app(self, app):
        self._app = app

    def do_connect(self):
        ip = self.ids.ip_field.text.strip()
        port_str = self.ids.port_field.text.strip()

        if not ip:
            self.ids.status_label.text = "Введите IP-адрес"
            self.ids.status_label.text_color = get_color_from_hex(DANGER)
            return

        try:
            port = int(port_str)
        except ValueError:
            self.ids.status_label.text = "Неверный порт"
            self.ids.status_label.text_color = get_color_from_hex(DANGER)
            return

        self.ids.status_label.text = "Подключение..."
        self.ids.status_label.text_color = get_color_from_hex(WARNING)

        if self._app:
            self._app.connect_tcp(ip, port)

    def do_connect_usb(self):
        self.ids.status_label.text = "Поиск USB (OTG)..."
        self.ids.status_label.text_color = get_color_from_hex(WARNING)
        if self._app:
            self._app.connect_usb_otg()


class DashboardScreen(MDScreen):
    """Main dashboard with device status and LED indicators."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None

    def set_app(self, app):
        self._app = app

    def disconnect(self):
        if self._app:
            self._app.disconnect()


class DiagnosticsScreen(MDScreen):
    """Diagnostics with HW test, speaker test, output test."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None

    def set_app(self, app):
        self._app = app

    def do_hw_test(self):
        if self._app:
            self._app.send_cmd("TEST HW")
            self.ids.btn_hw_test.disabled = True
            self.ids.hw_status.text = "Выполняется..."

    def do_test_on(self):
        if self._app:
            self._app.send_cmd("TEST ON")
            self.ids.spk_status.text = "Тест включён"

    def do_test_off(self):
        if self._app:
            self._app.send_cmd("TEST OFF")
            self.ids.spk_status.text = "Тест выключен"

    def do_out(self, num):
        if self._app:
            self._app.send_cmd(f"OUT {num}")


class ConfigurationScreen(MDScreen):
    """Configuration with GSM, MQTT, device settings."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None

    def set_app(self, app):
        self._app = app

    def reread(self):
        if self._app:
            self._app.send_cmd("SET")

    def apply_gsm(self):
        if self._app:
            apn = self.ids.apn_field.text.strip()
            user = self.ids.gsm_user_field.text.strip()
            pwd = self.ids.gsm_pass_field.text.strip()
            if apn:
                self._app.send_cmd(f"SET GSM APN={apn}")
            if user:
                self._app.send_cmd(f"SET GSM USER={user}")
            if pwd:
                self._app.send_cmd(f"SET GSM PASS={pwd}")

    def apply_mqtt(self):
        if self._app:
            mqtt = self.ids.mqtt_field.text.strip()
            if mqtt:
                self._app.send_cmd(f"SET MQTT={mqtt}")

    def apply_device(self):
        if self._app:
            vol = self.ids.vol_field.text.strip()
            rec = self.ids.rec_field.text.strip()
            if vol:
                self._app.send_cmd(f"SET VOL={vol}")
            if rec:
                self._app.send_cmd(f"SET REC={rec}")

    def save_all(self):
        if self._app:
            self._app.send_cmd("SET AS")

    def export_config(self):
        """Экспорт: JSON в user_data_dir/oko_config.json (доступен файловым
        менеджером; на Android не требует разрешений)."""
        if not self._app:
            return
        try:
            cfg = {
                "version": "1.0",
                "gsm": {
                    "apn": self.ids.apn_field.text.strip(),
                    "user": self.ids.gsm_user_field.text.strip(),
                    "password": self.ids.gsm_pass_field.text.strip(),
                },
                "mqtt": {"url": self.ids.mqtt_field.text.strip()},
                "device": {
                    "volume": self.ids.vol_field.text.strip(),
                    "registrar": self.ids.rec_field.text.strip(),
                },
            }
            path = os.path.join(self._app.user_data_dir, "oko_config.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            self._app._show_snackbar(f"Сохранено: {path}")
        except Exception as e:
            self._app._show_snackbar(f"Ошибка экспорта: {e}")

    def import_config(self):
        """Импорт: чтение oko_config.json из user_data_dir в поля."""
        if not self._app:
            return
        try:
            path = os.path.join(self._app.user_data_dir, "oko_config.json")
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            gsm = cfg.get("gsm", {})
            self.ids.apn_field.text = gsm.get("apn", "")
            self.ids.gsm_user_field.text = gsm.get("user", "")
            self.ids.gsm_pass_field.text = gsm.get("password", "")
            self.ids.mqtt_field.text = cfg.get("mqtt", {}).get("url", "")
            dev = cfg.get("device", {})
            self.ids.vol_field.text = str(dev.get("volume", ""))
            self.ids.rec_field.text = str(dev.get("registrar", ""))
            self._app._show_snackbar("Конфигурация загружена в поля")
        except FileNotFoundError:
            self._app._show_snackbar("Файл oko_config.json не найден")
        except Exception as e:
            self._app._show_snackbar(f"Ошибка импорта: {e}")


class MonitorScreen(MDScreen):
    """Real-time monitoring with GPS, GSM stats."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None
        self._monitoring = False

    def set_app(self, app):
        self._app = app

    def start_monitor(self):
        self._monitoring = True
        if self._app:
            self._app.send_cmd("POS")


class TerminalScreen(MDScreen):
    """Raw terminal for sending commands."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app = None

    def set_app(self, app):
        self._app = app

    def send_command(self):
        cmd = self.ids.cmd_field.text.strip()
        if cmd and self._app:
            self._app.send_cmd(cmd)
            self.ids.cmd_field.text = ""

    def quick_cmd(self, cmd):
        if self._app:
            self._app.send_cmd(cmd)


# ── Main Application ────────────────────────────────────────────────────────

class OkoMobileApp(MDApp):
    """OKO Service Tool — Mobile version."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "ОКО Service Tool"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        # Transport reference (set externally or via connect dialog)
        self.transport = None
        self.transport_kind = "tcp"  # tcp | serial (USB OTG резерв)
        self._response_handler = None
        self._log_path = ""

    def _configure_logging(self):
        self._log_path = os.path.join(self.user_data_dir, "oko-mobile.log")
        os.makedirs(self.user_data_dir, exist_ok=True)
        logging.basicConfig(
            filename=self._log_path,
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        logging.info("Starting OKO Service Tool; python=%s", sys.version)
        logging.info("argv=%r", sys.argv)

        def exception_hook(exc_type, exc_value, exc_traceback):
            logging.critical(
                "Unhandled exception:\n%s",
                "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            )
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = exception_hook

    def build(self):
        self._configure_logging()
        logging.info("Building mobile UI")
        self.load_kv_string(KVStyleSheet)
        self.load_kv_string(KV_CONNECTION)
        self.load_kv_string(KV_DASHBOARD)
        self.load_kv_string(KV_DIAGNOSTICS)
        self.load_kv_string(KV_CONFIGURATION)
        self.load_kv_string(KV_MONITOR)
        self.load_kv_string(KV_TERMINAL)

        # Screen manager
        self.sm = MDScreenManager()

        self.connection_screen = ConnectionScreen(name="connection")
        self.connection_screen.set_app(self)
        self.sm.add_widget(self.connection_screen)

        self.dashboard_screen = DashboardScreen(name="dashboard")
        self.dashboard_screen.set_app(self)
        self.sm.add_widget(self.dashboard_screen)

        self.diagnostics_screen = DiagnosticsScreen(name="diagnostics")
        self.diagnostics_screen.set_app(self)
        self.sm.add_widget(self.diagnostics_screen)

        self.config_screen = ConfigurationScreen(name="configuration")
        self.config_screen.set_app(self)
        self.sm.add_widget(self.config_screen)

        self.monitor_screen = MonitorScreen(name="monitor")
        self.monitor_screen.set_app(self)
        self.sm.add_widget(self.monitor_screen)

        self.terminal_screen = TerminalScreen(name="terminal")
        self.terminal_screen.set_app(self)
        self.sm.add_widget(self.terminal_screen)

        # Bottom navigation
        layout = MDBoxLayout(orientation="vertical")

        bottom_nav = MDBottomNavigation()
        bottom_nav.add_widget(
            MDBottomNavigationItem(
                name="dashboard_tab",
                text="Обзор",
                icon="information",
            )
        )
        bottom_nav.add_widget(
            MDBottomNavigationItem(
                name="diagnostics_tab",
                text="Диагностика",
                icon="bug-check",
            )
        )
        bottom_nav.add_widget(
            MDBottomNavigationItem(
                name="configuration_tab",
                text="Настройки",
                icon="cog",
            )
        )
        bottom_nav.add_widget(
            MDBottomNavigationItem(
                name="monitor_tab",
                text="Монитор",
                icon="chart-line",
            )
        )
        bottom_nav.add_widget(
            MDBottomNavigationItem(
                name="terminal_tab",
                text="Терминал",
                icon="console",
            )
        )

        # Tab switching
        bottom_nav.bind(
            on_tab_switch=lambda instance, tab, tab_text: self._on_tab_switch(tab.name)
        )

        layout.add_widget(self.sm)
        layout.add_widget(bottom_nav)

        return layout

    def _on_tab_switch(self, tab_name):
        screen_map = {
            "dashboard_tab": "dashboard",
            "diagnostics_tab": "diagnostics",
            "configuration_tab": "configuration",
            "monitor_tab": "monitor",
            "terminal_tab": "terminal",
        }
        screen = screen_map.get(tab_name)
        if screen:
            self.sm.current = screen

    def connect_tcp(self, ip, port):
        """Connect via TCP (WiFi ТД платы OKO_XXXXXX, 192.168.4.1:1234)."""
        try:
            import socket
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.settimeout(10)
            self.transport.connect((ip, port))
            self.transport.setblocking(False)
            self.transport_kind = "tcp"

            self.connection_screen.ids.status_label.text = f"Подключено: {ip}:{port}"
            self.connection_screen.ids.status_label.text_color = get_color_from_hex(SUCCESS)

            self.sm.current = "dashboard"

            # Start receiving
            Clock.schedule_interval(self._receive_data, 0.1)
            # Автоопрос как на десктопе: версия, серийник, настройки, GPS, GSM.
            Clock.schedule_once(lambda dt: self.send_cmd("VER"), 0.3)
            Clock.schedule_once(lambda dt: self.send_cmd("serial"), 0.8)
            Clock.schedule_once(lambda dt: self.send_cmd("SET"), 1.3)
            Clock.schedule_once(lambda dt: self.send_cmd("DEBUG ONLY POS"), 1.8)
            Clock.schedule_once(lambda dt: self.send_cmd("DEBUG ONLY GSM"), 2.3)

        except Exception as e:
            self.connection_screen.ids.status_label.text = f"Ошибка: {e}"
            self.connection_screen.ids.status_label.text_color = get_color_from_hex(DANGER)

    def connect_usb_otg(self):
        """Резервный канал: USB OTG (нужен OTG-кабель; работает там, где ядро
        отдаёт /dev/ttyUSB* или /dev/ttyACM*)."""
        try:
            import serial
        except ImportError:
            self.connection_screen.ids.status_label.text = "Нет pyserial в сборке"
            self.connection_screen.ids.status_label.text_color = get_color_from_hex(DANGER)
            return
        for dev in ("/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1"):
            if not os.path.exists(dev):
                continue
            try:
                ser = serial.Serial(dev, 115200, timeout=0)
                self.transport = ser
                self.transport_kind = "serial"
                self.connection_screen.ids.status_label.text = f"Подключено: {dev}"
                self.connection_screen.ids.status_label.text_color = get_color_from_hex(SUCCESS)
                self.sm.current = "dashboard"
                Clock.schedule_interval(self._receive_data, 0.1)
                Clock.schedule_once(lambda dt: self.send_cmd("VER"), 0.3)
                Clock.schedule_once(lambda dt: self.send_cmd("serial"), 0.8)
                Clock.schedule_once(lambda dt: self.send_cmd("SET"), 1.3)
                return
            except Exception as e:
                self._show_snackbar(f"{dev}: {e}")
        self.connection_screen.ids.status_label.text = "USB-устройство не найдено"
        self.connection_screen.ids.status_label.text_color = get_color_from_hex(DANGER)
        self._show_snackbar("Подключите плату OTG-кабелем и разрешите USB")

    def send_cmd(self, cmd):
        """Send command to device (TCP-сокет или USB-serial)."""
        if not self.transport:
            self._show_snackbar("Нет подключения")
            return
        try:
            data = f"{cmd}\r\n".encode("ascii")
            if self.transport_kind == "serial":
                self.transport.write(data)
                self.transport.flush()
            else:
                self.transport.send(data)
        except Exception as e:
            self._show_snackbar(f"Ошибка отправки: {e}")

    def _receive_data(self, dt):
        """Receive data from device (non-blocking, TCP и USB)."""
        if not self.transport:
            return

        try:
            if self.transport_kind == "serial":
                n = self.transport.in_waiting
                data = self.transport.read(n) if n else b""
            else:
                data = self.transport.recv(4096)
            if data:
                text = data.decode("utf-8", errors="replace")
                self._process_response(text)
        except BlockingIOError:
            pass
        except Exception as e:
            self._show_snackbar(f"Ошибка приёма: {e}")

    def _process_response(self, text):
        """Разбор ответов платы (форматы из руководства, разд. 6).

        Примеры живых строк:
          CMD: MCU: ST Ver: 00242.SUEKKUZ [A7682E] Make: May 15 2025 ...
          SERIAL: The board serial number is 001479
          POS: -- RMC ... Lat: ... Lng: ... Vel: ...
          [GSM] Signal: 18, Errors: 0 / [MQTT] Connected to ...
          SET: GSM_APN = internet / GSM_APN=internet
          CAL_OK / CAL_ER, EYES_1..3, FACE_4, PHONE5, SMOKE6
        """
        dash = self.dashboard_screen.ids
        mon = self.monitor_screen.ids
        for raw in text.replace("\r", "\n").split("\n"):
            line = raw.strip()
            if not line or line == ">>":
                continue

            ver = re.search(r"(?:Ver|ver|Version|Firmware Version):\s*(\S+)", line)
            if ver:
                make = re.search(r"Make:\s*(.+?)(?:\s*\]|$)", line)
                v = ver.group(1)
                if make:
                    v = "{} ({})".format(v, make.group(1).strip())
                dash.ver_value.text = v
                self._term_log("< {}".format(line))
                continue

            serial_m = re.search(r"[Ss][Ee][Rr][Ii][Aa][Ll][^0-9]*([0-9]+)", line)
            if serial_m and ("serial" in line.lower() or "SERIAL" in line):
                dash.serial_value.text = serial_m.group(1)
                continue

            if re.search(r"POS:\s*--\s*RMC", line, re.IGNORECASE):
                gps = {}
                for key in ("Time", "Date", "Lat", "Lng", "Vel"):
                    m = re.search(r"{}:\s*([^|]+)".format(key), line, re.IGNORECASE)
                    if m:
                        gps[key.lower()] = m.group(1).strip()
                if gps:
                    dash.gps_value.text = "{}, {}".format(
                        gps.get("lat", "—"), gps.get("lng", "—"))
                    mon.lat_value.text = gps.get("lat", "—")
                    mon.lon_value.text = gps.get("lng", "—")
                continue

            gsm_m = re.search(r"Signal:\s*(\d+)", line, re.IGNORECASE)
            if gsm_m:
                dash.gsm_value.text = "{}/31".format(gsm_m.group(1))
                mon.signal_value.text = gsm_m.group(1)
                mqtt_m = re.search(r"MQTT[:\]]?\s*(.*)", line, re.IGNORECASE)
                if mqtt_m and mqtt_m.group(1).strip():
                    dash.mqtt_value.text = mqtt_m.group(1).strip()
                continue

            kv = re.match(r"^(?:SET:\s*)?(.+?)\s*=\s*(.+)$", line, re.IGNORECASE)
            if kv:
                key, val = kv.group(1).strip(), kv.group(2).strip()
                lk = key.lower()
                if "apn" in lk:
                    dash.apn_value.text = val
                elif "mqtt" in lk:
                    dash.mqtt_value.text = val
                elif lk in ("reg", "rec"):
                    dash.rec_value.text = val
                continue

            if "CAL_OK" in line:
                self.diagnostics_screen.ids.hw_status.text = "Калибровка: успех"
                self._show_snackbar("Калибровка успешно завершена")
                continue
            if "CAL_ER" in line:
                self.diagnostics_screen.ids.hw_status.text = "Калибровка: ошибка"
                self._show_snackbar("Ошибка калибровки — повторите")
                continue

            if re.search(r"EYES|FACE|PHONE|SMOKE|Button pressed", line, re.IGNORECASE):
                self._term_log("< {}".format(line))
                continue

            if "TEST" in line or "TST:" in line:
                self.diagnostics_screen.ids.hw_status.text = line[:120]
                continue

            self._term_log("< {}".format(line))

    def _term_log(self, text):
        try:
            out = self.terminal_screen.ids.terminal_output
            out.text = (out.text + "\n" + text)[-4000:]
        except Exception:
            pass

    def _show_snackbar(self, message):
        """Show a brief notification."""
        MDSnackbar(
            MDSnackbarText(text=message),
        ).open()

    def disconnect(self):
        """Disconnect from device."""
        if self.transport:
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None

        Clock.unschedule(self._receive_data)
        self.sm.current = "connection"
        self.connection_screen.ids.status_label.text = "Отключено"
        self.connection_screen.ids.status_label.text_color = get_color_from_hex(TEXT_SECONDARY)

    def on_stop(self):
        logging.info("Stopping application")
        self.disconnect()


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OkoMobileApp().run()
