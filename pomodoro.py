#!/usr/bin/env python3
"""
Pomodoro Timer Desktop Application for Linux (PyQt5)
Inspired by Pomotroid & pomodorotimer.online

Features:
- Frameless modern dark UI with custom titlebar and rounded corners
- Native Always on Top (Pin) toggle (works reliably on X11/Linux)
- Quick session mode tabs (Focus / Short Break / Long Break)
- Smooth circular SVG-style progress ring with tabular countdown timer
- Built-in popular presets (25/5/15 Classic, 50/10/20 Deep Work, 15/3/10 Sprint, 45/15/30 Study)
- Separate minute-by-minute custom duration settings (Work, Short Break, Long Break, Rounds)
- Auto-start Work / Auto-start Break options
- Synthesized pleasant chime sounds (Focus End & Break End) with volume/mute control
- Desktop notifications via notify-send / system tray fallback
- Persistent configuration in ~/.config/pomodoro-app/settings.json
"""

import json
import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QIcon,
     QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Theme & Presets Constants (Pomotroid + pomodorotimer.online inspired)
# ---------------------------------------------------------------------------

THEME = {
    "bg_outer": "#1E222D",
    "bg_main": "#262B38",
    "bg_card": "#2F3545",
    "bg_card_hover": "#384054",
    "bg_input": "#1E222D",
    "border": "#3B4254",
    "text_primary": "#F3F6FA",
    "text_secondary": "#9AA5B8",
    "text_muted": "#687387",
    "track_bg": "#343B4E",
    "work": "#FF4E4D",         # Pomotroid signature coral red
    "work_glow": "#FF6B6B",
    "short_break": "#05EC8C",  # Pomotroid signature mint green
    "short_glow": "#38F4A4",
    "long_break": "#0BB5FF",   # Pomotroid signature cyan blue
    "long_glow": "#47C8FF",
    "warning": "#FFB84D",
}

SESSION_MODES = {
    "work": {
        "label": "FOCUS",
        "short_label": "Focus",
        "color": THEME["work"],
        "glow": THEME["work_glow"],
    },
    "short_break": {
        "label": "SHORT BREAK",
        "short_label": "Short Break",
        "color": THEME["short_break"],
        "glow": THEME["short_glow"],
    },
    "long_break": {
        "label": "LONG BREAK",
        "short_label": "Long Break",
        "color": THEME["long_break"],
        "glow": THEME["long_glow"],
    },
}

PRESETS = [
    {
        "id": "classic",
        "name": "Classic",
        "subtitle": "25 / 5 / 15m",
        "desc": "Standard Pomodoro rhythm",
        "work": 25,
        "short_break": 5,
        "long_break": 15,
        "rounds": 4,
    },
    {
        "id": "deep_work",
        "name": "Deep Work",
        "subtitle": "50 / 10 / 20m",
        "desc": "Extended flow sessions",
        "work": 50,
        "short_break": 10,
        "long_break": 20,
        "rounds": 4,
    },
    {
        "id": "study",
        "name": "Study 45",
        "subtitle": "45 / 15 / 30m",
        "desc": "Lecture & study blocks",
        "work": 45,
        "short_break": 15,
        "long_break": 30,
        "rounds": 4,
    },
    {
        "id": "sprint",
        "name": "Quick Sprint",
        "subtitle": "15 / 3 / 10m",
        "desc": "Fast momentum starter",
        "work": 15,
        "short_break": 3,
        "long_break": 10,
        "rounds": 4,
    },
    {
        "id": "ultralight",
        "name": "52 / 17 Rule",
        "subtitle": "52 / 17 / 25m",
        "desc": "DeskTime productivity ratio",
        "work": 52,
        "short_break": 17,
        "long_break": 25,
        "rounds": 3,
    },
    {
        "id": "custom",
        "name": "Custom",
        "subtitle": "90 / 30 / 30m",
        "desc": "Your personalized minutes",
        "work": 90,
        "short_break": 30,
        "long_break": 30,
        "rounds": 2,
    },
]

DEFAULT_PRESET_CONFIGS = {
    p["id"]: {
        "work_minutes": p["work"],
        "short_break_minutes": p["short_break"],
        "long_break_minutes": p["long_break"],
        "rounds": p["rounds"],
    }
    for p in PRESETS
}

DEFAULT_SETTINGS = {
    "preset_id": "classic",
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "rounds": 4,
    "preset_configs": DEFAULT_PRESET_CONFIGS,
    "always_on_top": True,
    "sound_enabled": True,
    "sound_volume": 80,
    "notifications_enabled": True,
    "auto_start_work": False,
    "auto_start_break": False,
    "compact_mode": False,
}

BREAK_EXERCISES = {
    "short_break": [
        {
            "id": "neck_tilt",
            "title": "목·승모근 스트레칭",
            "desc": "오른손으로 머리를 잡고 오른쪽으로 지그시 당겨 15초 유지 후 반대쪽도 반복하세요.",
        },
        {
            "id": "wrist_stretch",
            "title": "손목·전완근 늘리기",
            "desc": "팔을 앞으로 뻗고 손바닥이 정면을 향하게 한 뒤, 반대 손으로 손가락을 몸쪽으로 15초 당겨주세요.",
        },
        {
            "id": "seated_twist",
            "title": "앉아서 상체 비틀기",
            "desc": "의자 등받이를 양손으로 잡고 허리를 곧게 편 채 상체를 뒤로 천천히 회전해 15초 유지하세요.",
        },
        {
            "id": "shoulder_roll",
            "title": "어깨 으쓱 & 크게 돌리기",
            "desc": "어깨를 귀까지 으쓱 올렸다 툭 떨어뜨리고, 앞뒤로 크게 원을 그리며 10회 돌려주세요.",
        },
        {
            "id": "eye_20_20_20",
            "title": "눈 피로 풀기 (20-20-20)",
            "desc": "모니터에서 눈을 떼고 6m 이상 먼 곳을 20초간 바라보며 눈을 천천히 10번 깜빡이세요.",
        },
        {
            "id": "chin_tuck",
            "title": "턱 당기기 (거북목 교정)",
            "desc": "시선은 정면을 둔 채 턱을 목 쪽으로 수평하게 당겨 뒷목이 펴지는 느낌으로 10초 유지 × 3회.",
        },
        {
            "id": "scapula_squeeze",
            "title": "앉아서 날개뼈 모으기",
            "desc": "양팔을 W자 모양으로 벌려 가슴을 활짝 펴고 등 뒤 날개뼈를 5초간 조였다 풀기를 5회 반복하세요.",
        },
        {
            "id": "ankle_pump",
            "title": "앉아서 발목 돌리기 & 펌핑",
            "desc": "책상 아래에서 두 발을 살짝 들어 발목을 크게 돌리고 발끝을 당겼다 밀기를 15회 반복하세요.",
        },
    ],
    "long_break": [
        {
            "id": "desk_chest_open",
            "title": "책상 짚고 등·가슴 펴기",
            "desc": "책상 모서리를 양손으로 짚고 한 발 물러서서 상체를 숙여 어깨와 등을 시원하게 늘려주세요 (30초).",
        },
        {
            "id": "chair_squat",
            "title": "의자 터치 스쿼트 12회",
            "desc": "의자 앞에 서서 엉덩이가 의자 시트에 살짝 닿을 때까지만 앉았다 일어서는 동작을 12회 반복하세요.",
        },
        {
            "id": "seated_glute",
            "title": "앉아서 둔근(엉덩이) 스트레칭",
            "desc": "한쪽 발목을 반대쪽 무릎 위에 올리고 허리를 편 채 상체를 앞으로 천천히 숙여 20초씩 유지하세요.",
        },
        {
            "id": "calf_raise",
            "title": "종아리 까치발 들기 20회",
            "desc": "의자 등받이를 가볍게 잡고 뒤꿈치를 최대한 높이 들었다 내리며 하체 혈액순환을 깨워주세요.",
        },
        {
            "id": "standing_backbend",
            "title": "일어서서 허리 젖히기 & 기지개",
            "desc": "자리에서 일어나 양손으로 골반 뒤를 받치고 상체를 뒤로 부드럽게 젖혀 굽은 허리를 펴주세요.",
        },
        {
            "id": "desk_pushup",
            "title": "책상 짚고 푸시업 10회",
            "desc": "책상 끝을 어깨너비보다 넓게 짚고 몸을 일직선으로 유지한 채 가볍게 팔굽혀펴기 10회를 해보세요.",
        },
        {
            "id": "hamstring_stretch",
            "title": "일어서서 허벅지 뒤쪽 늘리기",
            "desc": "한쪽 발뒤꿈치를 바닥에 두고 발끝을 당긴 채 엉덩이를 뒤로 빼며 다리 뒤쪽을 20초씩 늘려주세요.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Sound Synthesizer & Player (Zero external asset dependency)
# ---------------------------------------------------------------------------

class SoundManager:
    """Synthesizes clean harmonic bell chimes and plays them asynchronously."""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / f"pomodoro_sounds_{os.getuid()}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.work_end_wav = self.temp_dir / "work_end.wav"
        self.break_end_wav = self.temp_dir / "break_end.wav"
        self.click_wav = self.temp_dir / "click.wav"
        self._ensure_wav_files()

    def _generate_chime(self, filepath: Path, notes: list, volume: float = 0.85):
        """
        notes: list of tuples (freq_hz, start_sec, duration_sec, amp)
        """
        sample_rate = 44100
        total_duration = max(start + dur for _, start, dur, _ in notes) + 0.15
        num_samples = int(sample_rate * total_duration)
        samples = [0.0] * num_samples

        for freq, start, dur, amp in notes:
            start_idx = int(start * sample_rate)
            end_idx = min(num_samples, int((start + dur) * sample_rate))
            for i in range(start_idx, end_idx):
                t = (i - start_idx) / sample_rate
                # Soft attack (12ms) + exponential decay bell envelope
                attack = min(1.0, t / 0.012)
                decay = math.exp(-3.8 * t / dur)
                env = attack * decay
                # Fundamental + gentle 2nd and 3rd harmonics for warm Rhodes/bell tone
                val = (
                    math.sin(2.0 * math.pi * freq * t) * 0.75
                    + math.sin(2.0 * math.pi * (freq * 2.0) * t) * 0.18 * math.exp(-3.0 * t)
                    + math.sin(2.0 * math.pi * (freq * 3.0) * t) * 0.07 * math.exp(-6.0 * t)
                )
                samples[i] += val * env * amp * volume

        # Normalize / clip protection
        peak = max(abs(s) for s in samples) if samples else 1.0
        scale = 0.92 / peak if peak > 0.92 else 1.0

        with wave.open(str(filepath), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for s in samples:
                clamped = max(-1.0, min(1.0, s * scale))
                frames.extend(struct.pack("<h", int(clamped * 32767)))
            wf.writeframes(frames)

    def _ensure_wav_files(self):
        try:
            # Ascending pleasant major 7th arpeggio for Work Complete -> Break time!
            # C5 (523.25), E5 (659.25), G5 (783.99), B5 (987.77), C6 (1046.50)
            self._generate_chime(
                self.work_end_wav,
                [
                    (523.25, 0.00, 0.55, 0.65),
                    (659.25, 0.14, 0.55, 0.70),
                    (783.99, 0.28, 0.60, 0.75),
                    (1046.50, 0.44, 0.95, 0.85),
                ],
            )
            # Gentle two-tone alert for Break Complete -> Back to Focus!
            # G5 (783.99) -> E5 (659.25) -> A5 (880.00)
            self._generate_chime(
                self.break_end_wav,
                [
                    (659.25, 0.00, 0.45, 0.70),
                    (523.25, 0.18, 0.45, 0.65),
                    (880.00, 0.38, 0.85, 0.85),
                ],
            )
        except Exception:
            pass

    def play(self, kind: str = "work_end", volume_percent: int = 80):
        wav_path = self.work_end_wav if kind == "work_end" else self.break_end_wav
        if not wav_path.exists():
            self._ensure_wav_files()

        # PulseAudio paplay supports --volume (0 to 65536)
        pa_vol = int(max(0, min(100, volume_percent)) * 655.36)
        try:
            subprocess.Popen(
                ["paplay", f"--volume={pa_vol}", str(wav_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except FileNotFoundError:
            pass

        try:
            subprocess.Popen(
                ["aplay", "-q", str(wav_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            QApplication.beep()


# ---------------------------------------------------------------------------
# Custom Painted Widgets (Vector Icons, Progress Dial, Toggle Switch)
# ---------------------------------------------------------------------------

class VectorIconButton(QPushButton):
    """Crisp anti-aliased custom vector icon button."""

    def __init__(self, icon_type: str, size: int = 30, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.active = False
        self.active_color = QColor(THEME["work"])
        self.normal_color = QColor(THEME["text_secondary"])
        self.hover_color = QColor(THEME["text_primary"])
        self._hovered = False

        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet("background: transparent; border: none;")

        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(250)
        self._tooltip_timer.timeout.connect(self._show_instant_tooltip)

    def _show_instant_tooltip(self):
        if self._hovered and self.toolTip():
            QToolTip.showText(
                self.mapToGlobal(QPoint(self.width() // 2, self.height() + 4)),
                self.toolTip(),
                self,
            )

    def set_active(self, active: bool, color: str = None):
        self.active = active
        if color:
            self.active_color = QColor(color)
        self.update()

    def set_icon_type(self, icon_type: str):
        self.icon_type = icon_type
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self._tooltip_timer.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._tooltip_timer.stop()
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # Subtle hover pill background
        if self._hovered or self.active:
            bg = QColor(self.active_color if self.active else QColor("#FFFFFF"))
            bg.setAlpha(32 if self.active else 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 7, 7)

        if self.active:
            fg = self.active_color
        elif self._hovered:
            fg = self.hover_color
        else:
            fg = self.normal_color

        pen = QPen(fg, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.icon_type == "pin":
            # Pushpin / Always-on-top indicator icon
            painter.save()
            painter.translate(cx, cy)
            if self.active:
                painter.rotate(0)
            else:
                painter.rotate(35)
            # Pin head
            painter.drawLine(QPointF(-4.5, -6.5), QPointF(4.5, -6.5))
            # Pin body
            path = QPainterPath()
            path.moveTo(-3.5, -6.5)
            path.lineTo(-3.5, -1.5)
            path.lineTo(-5.5, 1.0)
            path.lineTo(5.5, 1.0)
            path.lineTo(3.5, -1.5)
            path.lineTo(3.5, -6.5)
            if self.active:
                fill = QColor(fg)
                fill.setAlpha(75)
                painter.setBrush(fill)
            painter.drawPath(path)
            # Needle
            painter.drawLine(QPointF(0, 1.2), QPointF(0, 7.0))
            painter.restore()

        elif self.icon_type == "settings":
            # Sliders / tuning icon (Pomotroid style)
            y_positions = [cy - 5, cy, cy + 5]
            knob_x = [cx - 2.5, cx + 3.0, cx - 1.5]
            for y, kx in zip(y_positions, knob_x):
                painter.drawLine(QPointF(cx - 7, y), QPointF(kx - 2.2, y))
                painter.drawLine(QPointF(kx + 2.2, y), QPointF(cx + 7, y))
                painter.setBrush(QColor(THEME["bg_main"]))
                painter.drawEllipse(QPointF(kx, y), 2.1, 2.1)

        elif self.icon_type == "volume_on":
            # Speaker + sound waves
            poly = QPolygonF([
                QPointF(cx - 6.5, cy - 2.5),
                QPointF(cx - 3.5, cy - 2.5),
                QPointF(cx + 0.5, cy - 6.0),
                QPointF(cx + 0.5, cy + 6.0),
                QPointF(cx - 3.5, cy + 2.5),
                QPointF(cx - 6.5, cy + 2.5),
            ])
            painter.drawPolygon(poly)
            arc_rect1 = QRectF(cx - 1.5, cy - 3.5, 6.0, 7.0)
            painter.drawArc(arc_rect1, -55 * 16, 110 * 16)
            arc_rect2 = QRectF(cx - 2.5, cy - 6.2, 10.5, 12.4)
            painter.drawArc(arc_rect2, -55 * 16, 110 * 16)

        elif self.icon_type == "volume_off":
            poly = QPolygonF([
                QPointF(cx - 6.5, cy - 2.5),
                QPointF(cx - 3.5, cy - 2.5),
                QPointF(cx + 0.5, cy - 6.0),
                QPointF(cx + 0.5, cy + 6.0),
                QPointF(cx - 3.5, cy + 2.5),
                QPointF(cx - 6.5, cy + 2.5),
            ])
            painter.drawPolygon(poly)
            painter.drawLine(QPointF(cx + 3.0, cy - 2.5), QPointF(cx + 7.0, cy + 2.5))
            painter.drawLine(QPointF(cx + 7.0, cy - 2.5), QPointF(cx + 3.0, cy + 2.5))

        elif self.icon_type == "minimize":
            painter.drawLine(QPointF(cx - 5, cy + 1), QPointF(cx + 5, cy + 1))

        elif self.icon_type == "close":
            if self._hovered:
                painter.setPen(QPen(QColor("#FF5C5C"), 2.0, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(cx - 4.5, cy - 4.5), QPointF(cx + 4.5, cy + 4.5))
            painter.drawLine(QPointF(cx + 4.5, cy - 4.5), QPointF(cx - 4.5, cy + 4.5))

        elif self.icon_type == "reset":
            s = min(w, h) / 38.0
            r = 6.5 * s
            rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)
            painter.drawArc(rect, 35 * 16, 290 * 16)
            # Arrowhead at top-right of arc
            rad = math.radians(35)
            ax = cx + r * math.cos(rad)
            ay = cy - r * math.sin(rad)
            painter.drawLine(QPointF(ax, ay), QPointF(ax - 4.0 * s, ay - 1.0 * s))
            painter.drawLine(QPointF(ax, ay), QPointF(ax + 0.8 * s, ay - 4.0 * s))

        elif self.icon_type == "skip":
            s = min(w, h) / 38.0
            painter.setBrush(fg)
            poly = QPolygonF([
                QPointF(cx - 5.5 * s, cy - 5.5 * s),
                QPointF(cx + 2.0 * s, cy),
                QPointF(cx - 5.5 * s, cy + 5.5 * s),
            ])
            painter.drawPolygon(poly)
            painter.setPen(QPen(fg, 2.2 * s, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(cx + 4.5 * s, cy - 5.0 * s), QPointF(cx + 4.5 * s, cy + 5.0 * s))

        elif self.icon_type == "compact":
            # Expand / Collapse mini mode icon
            if self.active:
                # Expand arrows
                painter.drawLine(QPointF(cx - 5, cy + 5), QPointF(cx + 5, cy - 5))
                painter.drawLine(QPointF(cx + 1, cy - 5), QPointF(cx + 5, cy - 5))
                painter.drawLine(QPointF(cx + 5, cy - 1), QPointF(cx + 5, cy - 5))
            else:
                # Mini pip box icon
                painter.drawRoundedRect(QRectF(cx - 6.5, cy - 5.0, 13.0, 10.0), 2.0, 2.0)
                painter.setBrush(fg)
                painter.drawRoundedRect(QRectF(cx + 0.2, cy - 0.2, 4.8, 3.8), 1.0, 1.0)


class PlayPauseButton(QPushButton):
    """Central tactile play/pause button with session accent border and hover glow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.compact_mode = False
        self.accent_color = QColor(THEME["work"])
        self._hovered = False
        self.setFixedSize(64, 64)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Start / Pause (Space)")
        self.setStyleSheet("background: transparent; border: none;")

    def set_compact(self, compact: bool):
        self.compact_mode = compact
        size = 44 if compact else 64
        self.setFixedSize(size, size)
        self.update()

    def set_state(self, is_running: bool, accent_hex: str):
        self.is_running = is_running
        self.accent_color = QColor(accent_hex)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        scale = min(w, h) / 64.0
        radius = min(w, h) / 2.0 - 4.0 * scale

        # Outer subtle glow on hover or running
        if self._hovered or self.is_running:
            glow = QColor(self.accent_color)
            glow.setAlpha(45 if self._hovered else 25)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, cy), radius + 3.0 * scale, radius + 3.0 * scale)

        # Button fill & border
        if self.is_running:
            fill = QColor(THEME["bg_card"])
            border_color = QColor(self.accent_color)
            icon_color = QColor(THEME["text_primary"])
        else:
            if self._hovered:
                fill = QColor(self.accent_color)
                border_color = QColor(self.accent_color)
                icon_color = QColor("#181C24")
            else:
                fill = QColor(THEME["bg_card"])
                border_color = QColor(self.accent_color)
                border_color.setAlpha(190)
                icon_color = QColor(THEME["text_primary"])

        painter.setBrush(fill)
        painter.setPen(QPen(border_color, 2.2 * scale))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Draw Play triangle or Pause bars
        painter.setPen(Qt.NoPen)
        painter.setBrush(icon_color)

        if self.is_running:
            bar_w = 4.2 * scale
            bar_h = 16.0 * scale
            gap = 4.5 * scale
            painter.drawRoundedRect(
                QRectF(cx - gap - bar_w, cy - bar_h / 2.0, bar_w, bar_h), 2.0 * scale, 2.0 * scale
            )
            painter.drawRoundedRect(
                QRectF(cx + gap, cy - bar_h / 2.0, bar_w, bar_h), 2.0 * scale, 2.0 * scale
            )
        else:
            # Optical center adjustment (+2px right for triangle)
            path = QPainterPath()
            path.moveTo(cx - 5.0 * scale, cy - 9.0 * scale)
            path.lineTo(cx + 9.5 * scale, cy)
            path.lineTo(cx - 5.0 * scale, cy + 9.0 * scale)
            path.closeSubpath()
            painter.drawPath(path)


class CircularTimerDial(QWidget):
    """Pomotroid-inspired sleek circular progress ring with countdown & session label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0  # 1.0 = full, 0.0 = empty
        self.time_text = "25:00"
        self.mode_label = "FOCUS"
        self.accent_color = QColor(THEME["work"])
        self.glow_color = QColor(THEME["work_glow"])
        self.is_running = False
        self.compact_mode = False
        self.setMinimumSize(230, 230)

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def set_compact(self, compact: bool):
        self.compact_mode = compact
        if compact:
            self.setMinimumSize(135, 135)
        else:
            self.setMinimumSize(230, 230)
        self.update()

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def set_dial_state(
        self,
        progress: float,
        time_text: str,
        mode_label: str,
        accent_hex: str,
        glow_hex: str,
        is_running: bool,
        animate: bool = True,
    ):
        self.time_text = time_text
        self.mode_label = mode_label
        self.accent_color = QColor(accent_hex)
        self.glow_color = QColor(glow_hex)
        self.is_running = is_running

        if animate and abs(self._progress - progress) < 0.15:
            self._anim.stop()
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(progress)
            self._anim.start()
        else:
            self._anim.stop()
            self.progress = progress
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()
        size = min(w, h)
        cx, cy = w / 2.0, h / 2.0
        margin = 10.0 if self.compact_mode else 16.0
        radius = (size / 2.0) - margin
        rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)

        # 1. Subtle inner ambient radial glow when running
        if self.is_running:
            radial = QRadialGradient(QPointF(cx, cy), radius)
            c_center = QColor(self.accent_color)
            c_center.setAlpha(22)
            c_edge = QColor(self.accent_color)
            c_edge.setAlpha(0)
            radial.setColorAt(0.0, c_center)
            radial.setColorAt(1.0, c_edge)
            painter.setPen(Qt.NoPen)
            painter.setBrush(radial)
            painter.drawEllipse(rect)

        # 2. Background track ring
        ring_w = 5.5 if self.compact_mode else 7.5
        track_pen = QPen(QColor(THEME["track_bg"]), ring_w, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)

        # 3. Active progress arc (starts at 12 o'clock = 90 deg, sweeps counter-clockwise or clockwise)
        if self._progress > 0.001:
            # Outer soft glow arc
            glow_c = QColor(self.glow_color)
            glow_c.setAlpha(45)
            glow_w = 10.0 if self.compact_mode else 13.0
            glow_pen = QPen(glow_c, glow_w, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(glow_pen)
            span_angle = int(-self._progress * 360.0 * 16)
            painter.drawArc(rect, 90 * 16, span_angle)

            # Crisp foreground progress arc
            arc_pen = QPen(self.accent_color, ring_w, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(rect, 90 * 16, span_angle)

            # Leading dot indicator at tip of arc
            angle_rad = math.radians(90.0 - self._progress * 360.0)
            tip_x = cx + radius * math.cos(angle_rad)
            tip_y = cy - radius * math.sin(angle_rad)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            dot_r = 1.9 if self.compact_mode else 2.4
            painter.drawEllipse(QPointF(tip_x, tip_y), dot_r, dot_r)

        # 4. Time countdown text (Tabular numbers)
        time_font = QFont("Inter, Ubuntu, Cantarell, Noto Sans, Sans Serif")
        # Scale font slightly if hours or 3-digit minutes are shown, and smaller in compact mode
        if self.compact_mode:
            font_px = 28 if len(self.time_text) <= 5 else 23
        else:
            font_px = 46 if len(self.time_text) <= 5 else 38
        time_font.setPixelSize(font_px)
        time_font.setWeight(QFont.Light)
        time_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.0 if self.compact_mode else 1.5)
        painter.setFont(time_font)
        painter.setPen(QColor(THEME["text_primary"]))

        if self.compact_mode:
            time_rect = QRectF(cx - radius + 8, cy - 23, (radius - 8) * 2, 34)
        else:
            time_rect = QRectF(cx - radius + 10, cy - 34, (radius - 10) * 2, 54)
        painter.drawText(time_rect, Qt.AlignCenter, self.time_text)

        # 5. Session mode subtitle label
        mode_font = QFont("Inter, Ubuntu, Cantarell, Sans Serif")
        mode_font.setPixelSize(9 if self.compact_mode else 11)
        mode_font.setWeight(QFont.DemiBold)
        mode_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.8 if self.compact_mode else 2.8)
        painter.setFont(mode_font)
        painter.setPen(QColor(THEME["text_secondary"]))

        if self.compact_mode:
            mode_rect = QRectF(cx - radius + 12, cy + 12, (radius - 12) * 2, 18)
        else:
            mode_rect = QRectF(cx - radius + 16, cy + 24, (radius - 16) * 2, 22)
        painter.drawText(mode_rect, Qt.AlignCenter, self.mode_label)


class MinuteSteppersWidget(QFrame):
    """Clean custom minute stepper widget (- / value / +) for settings."""

    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        title: str,
        unit: str,
        accent_hex: str,
        min_val: int = 1,
        max_val: int = 180,
        initial: int = 25,
        parent=None,
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self._value = initial
        self.unit = unit
        self.accent_hex = accent_hex

        self.setObjectName("MinuteCard")
        self.setStyleSheet(
            f"""
            QFrame#MinuteCard {{
                background-color: {THEME['bg_card']};
                border: 1px solid {THEME['border']};
                border-radius: 10px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(6)

        # Colored dot + label
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background-color: {accent_hex}; border-radius: 4px; border: none;"
        )
        layout.addWidget(dot)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addStretch()

        # Spinbox for direct keyboard input + buttons for quick -1 / +1
        btn_style = f"""
            QPushButton {{
                background-color: {THEME['bg_input']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
                border-color: {accent_hex};
            }}
            QPushButton:pressed {{
                background-color: {accent_hex};
                color: #181C24;
            }}
        """

        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedSize(25, 25)
        self.btn_minus.setCursor(Qt.PointingHandCursor)
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_minus.clicked.connect(lambda: self.step(-1))

        self.spin = QSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setValue(initial)
        self.spin.setSuffix(f" {unit}")
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        self.spin.setAlignment(Qt.AlignCenter)
        self.spin.setFixedWidth(68)
        self.spin.setFixedHeight(25)
        self.spin.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {THEME['bg_input']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                selection-background-color: {accent_hex};
                selection-color: #181C24;
            }}
            QSpinBox:focus {{
                border: 1px solid {accent_hex};
            }}
            """
        )
        self.spin.valueChanged.connect(self._on_spin_changed)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(25, 25)
        self.btn_plus.setCursor(Qt.PointingHandCursor)
        self.btn_plus.setStyleSheet(btn_style)
        self.btn_plus.clicked.connect(lambda: self.step(1))

        layout.addWidget(self.btn_minus)
        layout.addWidget(self.spin)
        layout.addWidget(self.btn_plus)

    def _on_spin_changed(self, val: int):
        self._value = val
        self.valueChanged.emit(val)

    def step(self, delta: int):
        new_val = max(self.min_val, min(self.max_val, self.spin.value() + delta))
        self.spin.setValue(new_val)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, val: int, block_signal: bool = False):
        if block_signal:
            self.spin.blockSignals(True)
        self.spin.setValue(max(self.min_val, min(self.max_val, val)))
        self._value = self.spin.value()
        if block_signal:
            self.spin.blockSignals(False)


class StretchIllustrationWidget(QWidget):
    """Custom vector illustration showing desk/chair stretching posture with motion cues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.exercise_id = "neck_tilt"
        self.accent_color = QColor(THEME["short_break"])
        self._phase = 0.0
        self.setFixedSize(108, 108)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(45)
        self._anim_timer.timeout.connect(self._tick_anim)

    def showEvent(self, event):
        self._anim_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._anim_timer.stop()
        super().hideEvent(event)

    def _tick_anim(self):
        self._phase = (self._phase + 0.12) % (2.0 * math.pi)
        self.update()

    def set_illustration(self, exercise_id: str, accent_hex: str):
        self.exercise_id = exercise_id or "neck_tilt"
        self.accent_color = QColor(accent_hex)
        self.update()

    def _draw_arrow(self, painter: QPainter, p1: QPointF, p2: QPointF, color: QColor, width: float = 2.0):
        painter.save()
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        head_len = 5.5
        a1 = angle + math.radians(150)
        a2 = angle - math.radians(150)
        painter.drawLine(p2, QPointF(p2.x() + head_len * math.cos(a1), p2.y() + head_len * math.sin(a1)))
        painter.drawLine(p2, QPointF(p2.x() + head_len * math.cos(a2), p2.y() + head_len * math.sin(a2)))
        painter.restore()

    def _draw_chair(self, painter: QPainter, x: float, y: float, scale: float = 1.0):
        painter.save()
        chair_pen = QPen(QColor("#5C677D"), 2.6 * scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(chair_pen)
        # Chair backrest & seat
        painter.drawLine(QPointF(x - 14 * scale, y - 22 * scale), QPointF(x - 14 * scale, y + 6 * scale))
        painter.drawLine(QPointF(x - 14 * scale, y + 6 * scale), QPointF(x + 12 * scale, y + 6 * scale))
        # Chair leg/base
        painter.drawLine(QPointF(x - 1 * scale, y + 6 * scale), QPointF(x - 1 * scale, y + 24 * scale))
        painter.drawLine(QPointF(x - 10 * scale, y + 24 * scale), QPointF(x + 8 * scale, y + 24 * scale))
        painter.restore()

    def _draw_desk(self, painter: QPainter, x: float, y: float, scale: float = 1.0):
        painter.save()
        desk_pen = QPen(QColor("#5C677D"), 2.8 * scale, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(desk_pen)
        painter.drawLine(QPointF(x - 16 * scale, y), QPointF(x + 18 * scale, y))
        painter.drawLine(QPointF(x + 12 * scale, y), QPointF(x + 12 * scale, y + 28 * scale))
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        sway = math.sin(self._phase)  # -1.0 to 1.0 smooth oscillation

        # Soft rounded card canvas with subtle radial glow
        bg_rect = QRectF(2, 2, w - 4, h - 4)
        painter.setPen(QPen(QColor(THEME["border"]), 1.0))
        painter.setBrush(QColor(THEME["bg_outer"]))
        painter.drawRoundedRect(bg_rect, 12, 12)

        glow = QRadialGradient(QPointF(cx, cy), w * 0.45)
        gc = QColor(self.accent_color)
        gc.setAlpha(38)
        gc0 = QColor(self.accent_color)
        gc0.setAlpha(0)
        glow.setColorAt(0.0, gc)
        glow.setColorAt(1.0, gc0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(cx, cy), w * 0.44, h * 0.44)

        body_pen = QPen(QColor(THEME["text_primary"]), 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        accent_pen = QPen(self.accent_color, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        prop_pen = QPen(QColor("#68758E"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        ex = self.exercise_id

        if ex == "neck_tilt":
            # Front torso + head tilting side-to-side with hand gently pulling
            painter.setPen(body_pen)
            # Shoulders & torso
            painter.drawLine(QPointF(cx - 22, cy + 16), QPointF(cx + 22, cy + 16))
            painter.drawLine(QPointF(cx, cy + 16), QPointF(cx, cy + 36))
            painter.drawLine(QPointF(cx - 22, cy + 16), QPointF(cx - 26, cy + 34))
            # Neck + tilted head
            tilt_x = 5.5 + 3.0 * sway
            head_c = QPointF(cx + tilt_x, cy - 8)
            painter.drawLine(QPointF(cx, cy + 15), head_c)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(head_c, 11, 11)
            # Right arm reaching over head
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(cx + 22, cy + 16), QPointF(cx + 30, cy - 6))
            painter.drawLine(QPointF(cx + 30, cy - 6), QPointF(head_c.x() - 3, head_c.y() - 10))
            # Stretch arc arrow
            self._draw_arrow(painter, QPointF(cx - 12, cy - 24), QPointF(cx + 14, cy - 22), self.accent_color)

        elif ex == "wrist_stretch":
            # Extended arm + upright palm being pulled back by other hand
            painter.setPen(body_pen)
            # Forearm extending horizontally
            painter.drawLine(QPointF(cx - 32, cy + 6), QPointF(cx + 6, cy + 6))
            # Upright hand / fingers
            palm_angle = -6.0 * sway
            painter.save()
            painter.translate(cx + 6, cy + 6)
            painter.rotate(palm_angle)
            painter.drawLine(QPointF(0, 0), QPointF(0, -22))
            painter.drawLine(QPointF(0, 0), QPointF(5, -19))
            painter.restore()
            # Other hand pulling fingers back toward body
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(cx - 18, cy - 18), QPointF(cx + 3, cy - 14))
            self._draw_arrow(painter, QPointF(cx + 18, cy - 14), QPointF(cx - 8, cy - 14), self.accent_color)

        elif ex == "seated_twist":
            self._draw_chair(painter, cx - 2, cy + 14, 1.0)
            painter.setPen(body_pen)
            # Seated legs
            painter.drawLine(QPointF(cx - 8, cy + 18), QPointF(cx + 12, cy + 18))
            painter.drawLine(QPointF(cx + 12, cy + 18), QPointF(cx + 12, cy + 36))
            # Torso + head
            painter.drawLine(QPointF(cx - 8, cy + 18), QPointF(cx - 8, cy - 8))
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(cx - 8, cy - 19), 9, 9)
            # Arms twisting to chair back
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(cx - 8, cy - 2), QPointF(cx - 20, cy + 4))
            # Curved rotation arrows around torso
            arc_rect = QRectF(cx - 26, cy - 8, 36, 16)
            painter.drawArc(arc_rect, -30 * 16, 210 * 16)
            self._draw_arrow(painter, QPointF(cx + 6, cy + 4), QPointF(cx + 12, cy - 1), self.accent_color)

        elif ex == "shoulder_roll":
            painter.setPen(body_pen)
            lift = -3.5 * abs(sway)
            painter.drawEllipse(QPointF(cx, cy - 18), 10, 10)
            painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 30))
            painter.drawLine(QPointF(cx - 22, cy + 8 + lift), QPointF(cx + 22, cy + 8 + lift))
            painter.drawLine(QPointF(cx - 22, cy + 8 + lift), QPointF(cx - 24, cy + 28))
            painter.drawLine(QPointF(cx + 22, cy + 8 + lift), QPointF(cx + 24, cy + 28))
            # Circular roll arrows on both shoulders
            painter.setPen(QPen(self.accent_color, 2.0, Qt.SolidLine, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(cx - 31, cy - 1, 16, 16), 30 * 16, 260 * 16)
            painter.drawArc(QPointF(cx + 23, cy + 7).x() - 8, QPointF(cx + 23, cy + 7).y() - 8, 16, 16, 30 * 16, 260 * 16)

        elif ex == "eye_20_20_20":
            # Eye looking far toward distant mountains/target
            painter.setPen(body_pen)
            eye_cx, eye_cy = cx - 18, cy + 4
            path = QPainterPath()
            path.moveTo(eye_cx - 16, eye_cy)
            path.quadTo(eye_cx, eye_cy - 13, eye_cx + 16, eye_cy)
            path.quadTo(eye_cx, eye_cy + 13, eye_cx - 16, eye_cy)
            painter.drawPath(path)
            painter.setBrush(self.accent_color)
            painter.drawEllipse(QPointF(eye_cx + 3, eye_cy - 1), 4.5, 4.5)
            # Sight rays to distant tree/sparkle
            painter.setPen(QPen(self.accent_color, 2.0, Qt.DashLine, Qt.RoundCap))
            painter.drawLine(QPointF(eye_cx + 18, eye_cy - 3), QPointF(cx + 24, cy - 14))
            painter.drawLine(QPointF(eye_cx + 18, eye_cy + 3), QPointF(cx + 24, cy + 12))
            # Distant target icon (6m+)
            painter.setPen(accent_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx + 28, cy - 1), 9, 9)
            painter.setBrush(self.accent_color)
            painter.drawEllipse(QPointF(cx + 28, cy - 1), 3, 3)

        elif ex == "chin_tuck":
            # Side profile head sliding horizontally backward
            shift = -3.5 * (0.5 + 0.5 * sway)
            painter.setPen(QPen(QColor("#525C72"), 1.8, Qt.DashLine))
            painter.drawLine(QPointF(cx + 8, cy - 28), QPointF(cx + 8, cy + 28))
            painter.setPen(body_pen)
            # Neck & shoulders side view
            painter.drawLine(QPointF(cx - 4, cy + 32), QPointF(cx - 4 + shift * 0.5, cy + 6))
            painter.setBrush(QColor(THEME["bg_main"]))
            head_pt = QPointF(cx + 2 + shift, cy - 8)
            painter.drawEllipse(head_pt, 12, 13)
            # Nose profile
            painter.drawLine(QPointF(head_pt.x() + 11, head_pt.y() - 2), QPointF(head_pt.x() + 16, head_pt.y() + 3))
            painter.drawLine(QPointF(head_pt.x() + 16, head_pt.y() + 3), QPointF(head_pt.x() + 11, head_pt.y() + 5))
            # Horizontal retraction arrow
            self._draw_arrow(painter, QPointF(cx + 28, cy - 6), QPointF(cx + 14, cy - 6), self.accent_color)

        elif ex == "scapula_squeeze":
            # W-arm posture squeezing shoulder blades
            painter.setPen(body_pen)
            painter.drawEllipse(QPointF(cx, cy - 20), 9, 9)
            painter.drawLine(QPointF(cx, cy - 11), QPointF(cx, cy + 28))
            painter.drawLine(QPointF(cx - 16, cy - 4), QPointF(cx + 16, cy - 4))
            # W-shaped arms
            spread = 2.5 * sway
            painter.setPen(accent_pen)
            # Left W arm
            painter.drawLine(QPointF(cx - 16, cy - 4), QPointF(cx - 24, cy + 12))
            painter.drawLine(QPointF(cx - 24, cy + 12), QPointF(cx - 32 - spread, cy - 6))
            # Right W arm
            painter.drawLine(QPointF(cx + 16, cy - 4), QPointF(cx + 24, cy + 12))
            painter.drawLine(QPointF(cx + 24, cy + 12), QPointF(cx + 32 + spread, cy - 6))
            # Inward squeeze arrows on back
            self._draw_arrow(painter, QPointF(cx - 18, cy + 22), QPointF(cx - 5, cy + 22), self.accent_color)
            self._draw_arrow(painter, QPointF(cx + 18, cy + 22), QPointF(cx + 5, cy + 22), self.accent_color)

        elif ex == "ankle_pump":
            self._draw_chair(painter, cx - 14, cy + 10, 1.0)
            painter.setPen(body_pen)
            # Seated torso & extended lower leg
            painter.drawEllipse(QPointF(cx - 16, cy - 20), 8, 8)
            painter.drawLine(QPointF(cx - 16, cy - 12), QPointF(cx - 16, cy + 14))
            painter.drawLine(QPointF(cx - 16, cy + 14), QPointF(cx + 4, cy + 14))
            painter.drawLine(QPointF(cx + 4, cy + 14), QPointF(cx + 22, cy + 22))
            # Pumping foot
            foot_angle = 22.0 * sway
            painter.save()
            painter.translate(cx + 22, cy + 22)
            painter.rotate(foot_angle)
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(0, 0), QPointF(11, -6))
            painter.restore()
            self._draw_arrow(painter, QPointF(cx + 28, cy + 6), QPointF(cx + 28, cy + 28), self.accent_color)

        elif ex == "desk_chest_open":
            self._draw_desk(painter, cx + 22, cy + 6, 1.0)
            painter.setPen(body_pen)
            dip = 2.5 * sway
            # Standing legs back, torso hinged forward with hands on desk
            hip = QPointF(cx - 24, cy + 8)
            shoulder = QPointF(cx - 2, cy - 4 + dip)
            painter.drawLine(hip, QPointF(cx - 24, cy + 34))
            painter.drawLine(hip, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x() + 6, shoulder.y() - 6), 7.5, 7.5)
            # Arms reaching onto desk
            painter.setPen(accent_pen)
            painter.drawLine(shoulder, QPointF(cx + 16, cy + 6))
            self._draw_arrow(painter, QPointF(cx - 2, cy - 22), QPointF(cx - 2, cy - 10), self.accent_color)

        elif ex == "chair_squat":
            self._draw_chair(painter, cx - 18, cy + 14, 1.0)
            drop = 4.0 * (0.5 + 0.5 * sway)
            painter.setPen(body_pen)
            hip = QPointF(cx - 4, cy + 12 + drop)
            knee = QPointF(cx + 12, cy + 16 + drop * 0.5)
            foot = QPointF(cx + 6, cy + 36)
            shoulder = QPointF(cx + 2, cy - 10 + drop)
            painter.drawLine(foot, knee)
            painter.drawLine(knee, hip)
            painter.drawLine(hip, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x(), shoulder.y() - 10), 8, 8)
            # Forward balance arms
            painter.setPen(accent_pen)
            painter.drawLine(shoulder, QPointF(shoulder.x() + 18, shoulder.y() + 2))
            self._draw_arrow(painter, QPointF(cx + 28, cy + 16), QPointF(cx + 28, cy - 8), self.accent_color)

        elif ex == "seated_glute":
            self._draw_chair(painter, cx - 12, cy + 12, 1.0)
            painter.setPen(body_pen)
            lean = 4.0 * (0.5 + 0.5 * sway)
            hip = QPointF(cx - 12, cy + 14)
            shoulder = QPointF(cx - 10 + lean, cy - 10 + lean * 0.5)
            painter.drawLine(hip, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x() + 2, shoulder.y() - 9), 8, 8)
            # Supporting leg + Figure-4 crossed leg (highlighted)
            painter.drawLine(hip, QPointF(cx + 10, cy + 14))
            painter.drawLine(QPointF(cx + 10, cy + 14), QPointF(cx + 10, cy + 36))
            painter.setPen(accent_pen)
            painter.drawLine(hip, QPointF(cx + 4, cy + 4))
            painter.drawLine(QPointF(cx + 4, cy + 4), QPointF(cx + 10, cy + 14))
            self._draw_arrow(painter, QPointF(cx + 8, cy - 18), QPointF(cx + 20, cy - 8), self.accent_color)

        elif ex == "calf_raise":
            # Chair backrest support + standing figure rising on tiptoes
            painter.setPen(prop_pen)
            painter.drawLine(QPointF(cx - 18, cy + 2), QPointF(cx - 18, cy + 36))
            lift = -4.5 * (0.5 + 0.5 * sway)
            painter.setPen(body_pen)
            painter.drawEllipse(QPointF(cx + 4, cy - 22 + lift), 8, 8)
            painter.drawLine(QPointF(cx + 4, cy - 14 + lift), QPointF(cx + 4, cy + 14 + lift))
            painter.drawLine(QPointF(cx + 4, cy - 6 + lift), QPointF(cx - 18, cy + 4))
            painter.drawLine(QPointF(cx + 4, cy + 14 + lift), QPointF(cx + 4, cy + 30 + lift))
            # Tiptoe foot highlighted
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(cx + 4, cy + 30 + lift), QPointF(cx + 12, cy + 36))
            self._draw_arrow(painter, QPointF(cx + 22, cy + 24), QPointF(cx + 22, cy + 2), self.accent_color)

        elif ex == "standing_backbend":
            bend = 4.0 * (0.5 + 0.5 * sway)
            painter.setPen(body_pen)
            hip = QPointF(cx, cy + 12)
            shoulder = QPointF(cx - 6 - bend, cy - 12)
            painter.drawLine(hip, QPointF(cx, cy + 36))
            painter.drawLine(hip, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x() - 3, shoulder.y() - 9), 8, 8)
            # Hands supporting lower back
            painter.setPen(accent_pen)
            painter.drawLine(shoulder, QPointF(cx - 10, cy + 2))
            painter.drawLine(QPointF(cx - 10, cy + 2), QPointF(cx - 2, cy + 10))
            self._draw_arrow(painter, QPointF(cx + 12, cy - 20), QPointF(cx - 14, cy - 22), self.accent_color)

        elif ex == "desk_pushup":
            self._draw_desk(painter, cx + 20, cy + 6, 1.0)
            dip = 3.5 * (0.5 + 0.5 * sway)
            painter.setPen(body_pen)
            foot = QPointF(cx - 28, cy + 34)
            shoulder = QPointF(cx - 2 + dip, cy - 6 + dip)
            # Diagonal plank line
            painter.drawLine(foot, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x() + 5, shoulder.y() - 7), 8, 8)
            # Pushing arms to desk edge
            painter.setPen(accent_pen)
            painter.drawLine(shoulder, QPointF(cx + 12, cy + 6))
            self._draw_arrow(painter, QPointF(cx - 14, cy - 16), QPointF(cx - 4, cy - 6), self.accent_color)

        else:  # hamstring_stretch
            painter.setPen(body_pen)
            hip = QPointF(cx - 10, cy + 10)
            shoulder = QPointF(cx + 6, cy - 8)
            painter.drawLine(hip, shoulder)
            painter.setBrush(QColor(THEME["bg_main"]))
            painter.drawEllipse(QPointF(shoulder.x() + 4, shoulder.y() - 8), 8, 8)
            # Back bent knee leg
            painter.drawLine(hip, QPointF(cx - 14, cy + 24))
            painter.drawLine(QPointF(cx - 14, cy + 24), QPointF(cx - 14, cy + 36))
            # Extended front hamstring leg with toes up
            painter.setPen(accent_pen)
            painter.drawLine(hip, QPointF(cx + 16, cy + 34))
            painter.drawLine(QPointF(cx + 16, cy + 34), QPointF(cx + 23, cy + 27))
            self._draw_arrow(painter, QPointF(cx + 22, cy + 18), QPointF(cx + 16, cy + 6), self.accent_color)


class StretchPopupWindow(QWidget):
    """Separate floating window with vector posture illustration for Break stretching."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self.accent_hex = THEME["short_break"]
        self.always_on_top = True
        self.setWindowTitle("Break Stretch Guide")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self._apply_flags(initial=True)
        self._build_ui()

    def _apply_flags(self, initial: bool = False):
        pos = self.pos() if not initial else None
        flags = Qt.Tool | Qt.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if not initial and self.isVisible():
            self.show()
            if pos is not None:
                self.move(pos)

    def set_always_on_top(self, aot: bool):
        if self.always_on_top != aot:
            self.always_on_top = aot
            was_visible = self.isVisible()
            self._apply_flags(initial=False)
            if was_visible:
                self.show()

    def _build_ui(self):
        self.setFixedSize(360, 195)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self.card = QFrame(self)
        self.card.setObjectName("StretchPopupCard")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 145))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        v_layout = QVBoxLayout(self.card)
        v_layout.setContentsMargins(12, 9, 12, 11)
        v_layout.setSpacing(7)

        # Header bar
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.badge_lbl = QLabel("BREAK STRETCH")
        self.badge_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        header.addWidget(self.badge_lbl)
        header.addStretch()

        self.btn_next = QPushButton("다른 동작 ↻")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFixedHeight(22)
        self.btn_next.setToolTip("다른 추천 스트레칭/운동 보기")
        header.addWidget(self.btn_next)

        self.btn_close = VectorIconButton("close", size=22, tooltip="스트레칭 창 닫기")
        self.btn_close.clicked.connect(self.hide)
        header.addWidget(self.btn_close)

        v_layout.addLayout(header)

        # Body: Left Illustration + Right Title & Description
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        self.illustration = StretchIllustrationWidget(self.card)
        body.addWidget(self.illustration)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 2, 0, 2)
        text_col.setSpacing(5)

        self.lbl_title = QLabel("✦ 스트레칭 추천")
        self.lbl_title.setWordWrap(True)
        text_col.addWidget(self.lbl_title)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        text_col.addWidget(self.lbl_desc, 1)

        body.addLayout(text_col, 1)
        v_layout.addLayout(body, 1)
        self._apply_style()

    def _apply_style(self):
        self.card.setStyleSheet(
            f"""
            QFrame#StretchPopupCard {{
                background-color: {THEME['bg_main']};
                border: 1.5px solid {self.accent_hex};
                border-radius: 14px;
            }}
            """
        )
        self.badge_lbl.setStyleSheet(
            f"""
            color: {self.accent_hex};
            font-size: 10px;
            font-weight: 700;
            background-color: {THEME['bg_outer']};
            border: 1px solid {THEME['border']};
            border-radius: 5px;
            padding: 2px 8px;
            """
        )
        self.lbl_title.setStyleSheet(
            f"color: {self.accent_hex}; font-size: 13px; font-weight: 700; border: none; background: transparent;"
        )
        self.lbl_desc.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;"
        )
        self.btn_next.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_primary']};
                border: 1px solid {self.accent_hex};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 1px 8px;
            }}
            QPushButton:hover {{
                background-color: {self.accent_hex};
                color: #181C24;
            }}
            """
        )

    def set_exercise(self, exercise: dict, mode: str, accent_hex: str):
        self.accent_hex = accent_hex
        mode_tag = "SHORT BREAK · 착석 스트레칭" if mode == "short_break" else "LONG BREAK · 전신 리프레시"
        self.badge_lbl.setText(mode_tag)
        if exercise:
            self.lbl_title.setText(f"✦ {exercise['title']}")
            self.lbl_desc.setText(exercise["desc"])
            self.illustration.set_illustration(exercise.get("id", "neck_tilt"), accent_hex)
        self._apply_style()

    def position_near(self, main_win: QWidget):
        screen = QApplication.screenAt(main_win.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRectF(0, 0, 1920, 1080)

        mw_geo = main_win.frameGeometry()
        pw, ph = self.width(), self.height()

        # Prefer placing to the right of main window, else left, else below, else above
        if mw_geo.right() + 8 + pw <= avail.right():
            x = mw_geo.right() + 8
            y = mw_geo.top()
        elif mw_geo.left() - 8 - pw >= avail.left():
            x = mw_geo.left() - 8 - pw
            y = mw_geo.top()
        elif mw_geo.bottom() + 8 + ph <= avail.bottom():
            x = max(int(avail.left()), min(mw_geo.left(), int(avail.right()) - pw))
            y = mw_geo.bottom() + 8
        else:
            x = max(int(avail.left()), min(mw_geo.left(), int(avail.right()) - pw))
            y = max(int(avail.top()), mw_geo.top() - 8 - ph)

        y = max(int(avail.top()), min(int(y), int(avail.bottom()) - ph))
        self.move(int(x), int(y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# Main Pomodoro Window
# ---------------------------------------------------------------------------

class PomodoroWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_path = Path.home() / ".config" / "pomodoro-app" / "settings.json"
        self.settings = self.load_settings()
        self.sound_mgr = SoundManager()

        # Timer state
        self.current_mode = "work"  # 'work', 'short_break', 'long_break'
        self.current_round = 1
        self.total_rounds = int(self.settings["rounds"])
        self.is_running = False
        self.total_seconds = int(self.settings["work_minutes"]) * 60
        self.remaining_seconds = self.total_seconds
        self.current_exercise = None

        # Drag state for frameless window
        self._drag_pos = None

        # Configure window flags (Frameless + Always on Top if enabled)
        self.setWindowTitle("Pomodoro")
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self._apply_window_flags(initial=True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Build UI
        self.stretch_popup = StretchPopupWindow()
        self.stretch_popup.btn_next.clicked.connect(
            lambda: self._pick_next_exercise(avoid_current=True)
        )
        self._build_ui()
        self._setup_shortcuts()

        # Core 1-second tick timer
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)

        # Apply initial state to UI
        self._sync_ui_from_settings()
        self._update_timer_display(animate=False)

    # -----------------------------------------------------------------------
    # Settings Persistence
    # -----------------------------------------------------------------------

    def load_settings(self) -> dict:
        data = dict(DEFAULT_SETTINGS)
        data["preset_configs"] = {
            k: dict(v) for k, v in DEFAULT_PRESET_CONFIGS.items()
        }
        try:
            if self.config_path.exists():
                loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    loaded_configs = loaded.pop("preset_configs", None)
                    data.update(loaded)
                    if isinstance(loaded_configs, dict):
                        for pid, cfg in loaded_configs.items():
                            if pid in data["preset_configs"] and isinstance(cfg, dict):
                                data["preset_configs"][pid].update(cfg)
                    else:
                        # Migrate active preset's saved values into preset_configs
                        active_pid = data.get("preset_id", "classic")
                        if active_pid in data["preset_configs"]:
                            data["preset_configs"][active_pid] = {
                                "work_minutes": int(data.get("work_minutes", 25)),
                                "short_break_minutes": int(data.get("short_break_minutes", 5)),
                                "long_break_minutes": int(data.get("long_break_minutes", 15)),
                                "rounds": int(data.get("rounds", 4)),
                            }
        except Exception:
            pass

        # Ensure top-level active durations match the active preset_id config
        active_pid = data.get("preset_id", "classic")
        if active_pid not in data["preset_configs"]:
            active_pid = "classic"
            data["preset_id"] = active_pid
        active_cfg = data["preset_configs"][active_pid]
        data["work_minutes"] = int(active_cfg["work_minutes"])
        data["short_break_minutes"] = int(active_cfg["short_break_minutes"])
        data["long_break_minutes"] = int(active_cfg["long_break_minutes"])
        data["rounds"] = int(active_cfg["rounds"])
        return data

    def save_settings(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self.settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Always on Top & Window Management
    # -----------------------------------------------------------------------

    def _apply_window_flags(self, initial: bool = False):
        pos = self.pos() if not initial else None
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.settings.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        # Also try X11 _NET_WM_STATE_ABOVE via wmctrl/xprop if available for rock-solid Linux WM pinning
        if not initial:
            self.show()
            if pos is not None:
                self.move(pos)
            self.raise_()
            self.activateWindow()
        QTimer.singleShot(50, self._enforce_x11_above)

    def _enforce_x11_above(self):
        """Ensure X11 Window Manager respects Always-on-Top state immediately."""
        keep_above = bool(self.settings.get("always_on_top", True))
        action = "add" if keep_above else "remove"
        for w in (self, getattr(self, "stretch_popup", None)):
            if w is not None and w.isVisible():
                win_id = int(w.winId())
                try:
                    subprocess.Popen(
                        ["wmctrl", "-i", "-r", hex(win_id), "-b", f"{action},above"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    pass

    def toggle_always_on_top(self):
        new_state = not bool(self.settings.get("always_on_top", True))
        self.settings["always_on_top"] = new_state
        self.save_settings()
        self.btn_pin.set_active(
            new_state, SESSION_MODES[self.current_mode]["color"]
        )
        self.btn_pin.setToolTip(
            "Always on Top: ON (Click to unpin)"
            if new_state
            else "Always on Top: OFF (Click to pin on top)"
        )
        self.stretch_popup.set_always_on_top(new_state)
        self._apply_window_flags(initial=False)
        self._update_pin_badge()

    def toggle_compact_mode(self):
        compact = not bool(self.settings.get("compact_mode", False))
        self.settings["compact_mode"] = compact
        self.save_settings()
        self._apply_compact_mode(compact)

    def _apply_compact_mode(self, compact: bool):
        self.btn_compact.set_active(
            compact, SESSION_MODES[self.current_mode]["color"]
        )
        if compact:
            # Switch to main timer page if in settings
            if self.stack.currentIndex() != 0:
                self.stack.setCurrentIndex(0)
                self.btn_settings.set_active(False)
            self.title_label.hide()
            self.mode_tabs_frame.hide()
            self.bottom_bar_widget.hide()
            self.pin_badge.hide()

            self.outer_layout.setContentsMargins(6, 6, 6, 6)
            self.container_layout.setContentsMargins(10, 8, 10, 10)
            self.container_layout.setSpacing(4)
            self.titlebar_layout.setSpacing(2)
            for btn in (self.btn_pin, self.btn_compact, self.btn_settings, self.btn_min, self.btn_close):
                btn.setFixedSize(24, 24)

            self.timer_page_layout.setContentsMargins(0, 0, 0, 0)
            self.timer_page_layout.setSpacing(4)
            self.controls_row.setContentsMargins(8, 0, 8, 0)
            self.controls_row.setSpacing(14)

            self.dial.set_compact(True)
            self.btn_play.set_compact(True)
            self.btn_reset.setFixedSize(28, 28)
            self.btn_skip.setFixedSize(28, 28)
        else:
            self.title_label.show()
            self.mode_tabs_frame.show()
            self.bottom_bar_widget.show()
            self.pin_badge.show()

            self.outer_layout.setContentsMargins(10, 10, 10, 10)
            self.container_layout.setContentsMargins(16, 12, 16, 14)
            self.container_layout.setSpacing(8)
            self.titlebar_layout.setSpacing(5)
            for btn in (self.btn_pin, self.btn_compact, self.btn_settings, self.btn_min, self.btn_close):
                btn.setFixedSize(28, 28)

            self.timer_page_layout.setContentsMargins(0, 4, 0, 0)
            self.timer_page_layout.setSpacing(8)
            self.controls_row.setContentsMargins(20, 0, 20, 2)
            self.controls_row.setSpacing(22)

            self.dial.set_compact(False)
            self.btn_play.set_compact(False)
            self.btn_reset.setFixedSize(38, 38)
            self.btn_skip.setFixedSize(38, 38)

        self._update_window_geometry()
        if self.stretch_popup.isVisible():
            QTimer.singleShot(20, lambda: self.stretch_popup.position_near(self))

    def _update_window_geometry(self):
        compact = bool(self.settings.get("compact_mode", False))
        if compact:
            self.setFixedSize(210, 236)
        else:
            self.dial.setMinimumSize(230, 230)
            self.setFixedSize(390, 500)

    # -----------------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        self.setFixedSize(390, 500)

        # Outer wrapper for rounded corners & drop shadow
        outer = QWidget(self)
        self.setCentralWidget(outer)
        self.outer_layout = QVBoxLayout(outer)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)

        self.main_container = QFrame(outer)
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet(
            f"""
            QFrame#MainContainer {{
                background-color: {THEME['bg_main']};
                border: 1px solid {THEME['border']};
                border-radius: 16px;
            }}
            QToolTip {{
                background-color: {THEME['bg_outer']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.main_container.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(self.main_container)

        self.container_layout = QVBoxLayout(self.main_container)
        self.container_layout.setContentsMargins(16, 12, 16, 14)
        self.container_layout.setSpacing(8)

        # --- 1. Custom Frameless Titlebar ---
        self.titlebar_layout = QHBoxLayout()
        self.titlebar_layout.setContentsMargins(2, 0, 2, 0)
        self.titlebar_layout.setSpacing(5)

        self.title_dot = QLabel()
        self.title_dot.setFixedSize(9, 9)
        self.title_dot.setStyleSheet(
            f"background-color: {THEME['work']}; border-radius: 4px;"
        )
        self.titlebar_layout.addWidget(self.title_dot)

        self.title_label = QLabel("Pomodoro")
        self.title_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.title_label.setStyleSheet(
            f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.3px;
            background: transparent;
            padding-right: 2px;
            """
        )
        self.title_label.setMinimumWidth(self.title_label.sizeHint().width() + 8)
        self.titlebar_layout.addWidget(self.title_label)

        # Always-on-top status badge pill
        self.pin_badge = QPushButton("ON TOP")
        self.pin_badge.setCursor(Qt.PointingHandCursor)
        self.pin_badge.setFixedHeight(19)
        self.pin_badge.setToolTip("Always on Top status (Click to toggle)")
        self.pin_badge.clicked.connect(self.toggle_always_on_top)
        self.titlebar_layout.addWidget(self.pin_badge)

        self.titlebar_layout.addStretch()

        self.btn_pin = VectorIconButton("pin", size=28, tooltip="Toggle Always on Top (Ctrl+T)")
        self.btn_pin.clicked.connect(self.toggle_always_on_top)

        self.btn_compact = VectorIconButton("compact", size=28, tooltip="Toggle Mini Mode (Ctrl+M)")
        self.btn_compact.clicked.connect(self.toggle_compact_mode)

        self.btn_settings = VectorIconButton("settings", size=28, tooltip="Timer Settings & Presets (Ctrl+,)")
        self.btn_settings.clicked.connect(self.toggle_settings_view)

        self.btn_min = VectorIconButton("minimize", size=28, tooltip="Minimize")
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_close = VectorIconButton("close", size=28, tooltip="Quit (Ctrl+Q)")
        self.btn_close.clicked.connect(self.close)

        self.titlebar_layout.addWidget(self.btn_pin)
        self.titlebar_layout.addWidget(self.btn_compact)
        self.titlebar_layout.addWidget(self.btn_settings)
        self.titlebar_layout.addWidget(self.btn_min)
        self.titlebar_layout.addWidget(self.btn_close)

        self.container_layout.addLayout(self.titlebar_layout)

        # --- 2. Stacked Views: Page 0 = Timer, Page 1 = Settings ---
        self.stack = QStackedWidget()
        self.container_layout.addWidget(self.stack, 1)

        self.timer_page = self._build_timer_page()
        self.settings_page = self._build_settings_page()

        self.stack.addWidget(self.timer_page)
        self.stack.addWidget(self.settings_page)

    def _build_timer_page(self) -> QWidget:
        page = QWidget()
        self.timer_page_layout = QVBoxLayout(page)
        self.timer_page_layout.setContentsMargins(0, 4, 0, 0)
        self.timer_page_layout.setSpacing(8)

        # Quick session mode selector tabs (pomodorotimer.online style)
        self.mode_tabs_frame = QFrame()
        self.mode_tabs_frame.setObjectName("ModeTabsFrame")
        self.mode_tabs_frame.setStyleSheet(
            f"""
            QFrame#ModeTabsFrame {{
                background-color: {THEME['bg_outer']};
                border-radius: 10px;
                border: 1px solid {THEME['border']};
            }}
            """
        )
        tabs_layout = QHBoxLayout(self.mode_tabs_frame)
        tabs_layout.setContentsMargins(3, 3, 3, 3)
        tabs_layout.setSpacing(3)

        self.mode_buttons = {}
        for mode_key, meta in SESSION_MODES.items():
            btn = QPushButton(meta["short_label"])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(27)
            btn.clicked.connect(lambda checked, m=mode_key: self.switch_mode(m, manual=True))
            tabs_layout.addWidget(btn)
            self.mode_buttons[mode_key] = btn

        self.timer_page_layout.addWidget(self.mode_tabs_frame)

        # Center Circular Progress Dial
        self.dial = CircularTimerDial()
        self.timer_page_layout.addWidget(self.dial, 1)

        # Main Transport Controls Row: Reset | Play/Pause | Skip
        self.controls_row = QHBoxLayout()
        self.controls_row.setContentsMargins(20, 0, 20, 2)
        self.controls_row.setSpacing(22)
        self.controls_row.addStretch()

        self.btn_reset = VectorIconButton("reset", size=38, tooltip="Reset Current Session (R)")
        self.btn_reset.clicked.connect(self.reset_current_session)

        self.btn_play = PlayPauseButton()
        self.btn_play.clicked.connect(self.toggle_start_pause)

        self.btn_skip = VectorIconButton("skip", size=38, tooltip="Skip to Next Session (S)")
        self.btn_skip.clicked.connect(self.skip_session)

        self.controls_row.addWidget(self.btn_reset)
        self.controls_row.addWidget(self.btn_play)
        self.controls_row.addWidget(self.btn_skip)
        self.controls_row.addStretch()

        self.timer_page_layout.addLayout(self.controls_row)

        # Bottom Status Bar (Round counter + active preset pill + mute toggle)
        self.bottom_bar_widget = QWidget()
        bottom_bar = QHBoxLayout(self.bottom_bar_widget)
        bottom_bar.setContentsMargins(4, 4, 4, 0)
        bottom_bar.setSpacing(6)

        # Round info + reset rounds button
        round_box = QVBoxLayout()
        round_box.setSpacing(1)
        self.lbl_rounds = QLabel("1 / 4")
        self.lbl_rounds.setStyleSheet(
            f"color: {THEME['text_primary']}; font-size: 13px; font-weight: 700;"
        )
        btn_reset_rounds = QPushButton("ROUND · RESET")
        btn_reset_rounds.setCursor(Qt.PointingHandCursor)
        btn_reset_rounds.setToolTip("Click to reset round counter to 1")
        btn_reset_rounds.setStyleSheet(
            f"""
            QPushButton {{
                color: {THEME['text_muted']};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
                border: none;
                background: transparent;
                text-align: left;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {THEME['text_primary']};
            }}
            """
        )
        btn_reset_rounds.clicked.connect(self.reset_all_rounds)
        round_box.addWidget(self.lbl_rounds)
        round_box.addWidget(btn_reset_rounds)
        bottom_bar.addLayout(round_box)

        bottom_bar.addStretch()

        # Quick current preset / durations badge (click opens settings)
        self.btn_preset_badge = QPushButton("Classic · 25/5/15m")
        self.btn_preset_badge.setCursor(Qt.PointingHandCursor)
        self.btn_preset_badge.setToolTip("Click to change preset or custom minutes")
        self.btn_preset_badge.clicked.connect(self.toggle_settings_view)
        self.btn_preset_badge.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 11px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
            }}
            """
        )
        bottom_bar.addWidget(self.btn_preset_badge)

        bottom_bar.addStretch()

        # Mute / Sound toggle button
        self.btn_mute = VectorIconButton("volume_on", size=30, tooltip="Toggle Sound (M)")
        self.btn_mute.clicked.connect(self.toggle_mute)
        bottom_bar.addWidget(self.btn_mute)

        self.timer_page_layout.addWidget(self.bottom_bar_widget)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        outer_v = QVBoxLayout(page)
        outer_v.setContentsMargins(0, 2, 0, 0)
        outer_v.setSpacing(8)

        # Scrollable settings container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget#ScrollContent {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {THEME['bg_outer']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        content = QWidget()
        content.setObjectName("ScrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 6, 8)
        layout.setSpacing(10)

        # --- Section 1: Popular Presets ---
        sec1_lbl = QLabel("POPULAR PRESETS")
        sec1_lbl.setStyleSheet(
            f"color: {THEME['text_muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1.4px;"
        )
        layout.addWidget(sec1_lbl)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        self.preset_buttons = {}

        for idx, preset in enumerate(PRESETS):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(48)
            btn.setText(f"{preset['name']}\n{preset['subtitle']}")
            btn.setToolTip(preset["desc"])
            btn.clicked.connect(lambda checked, pid=preset["id"]: self.select_preset(pid))
            row, col = divmod(idx, 2)
            preset_grid.addWidget(btn, row, col)
            self.preset_buttons[preset["id"]] = btn

        layout.addLayout(preset_grid)

        # --- Section 2: Custom Minute Settings ---
        sec2_header = QHBoxLayout()
        sec2_header.setContentsMargins(0, 4, 0, 0)
        sec2_lbl = QLabel("PRESET DURATION & ROUNDS")
        sec2_lbl.setStyleSheet(
            f"color: {THEME['text_muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1.4px;"
        )
        sec2_header.addWidget(sec2_lbl)
        sec2_header.addStretch()

        self.btn_reset_preset = QPushButton("Reset to Default")
        self.btn_reset_preset.setCursor(Qt.PointingHandCursor)
        self.btn_reset_preset.setToolTip("Restore the selected preset to its original default values")
        self.btn_reset_preset.setStyleSheet(
            f"""
            QPushButton {{
                color: {THEME['text_secondary']};
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: 1px solid {THEME['border']};
                border-radius: 5px;
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                color: {THEME['text_primary']};
                background-color: {THEME['bg_card_hover']};
            }}
            """
        )
        self.btn_reset_preset.clicked.connect(self.reset_active_preset_to_default)
        sec2_header.addWidget(self.btn_reset_preset)
        layout.addLayout(sec2_header)

        self.step_work = MinuteSteppersWidget(
            "Focus Session",
            "min",
            THEME["work"],
            min_val=1,
            max_val=180,
            initial=int(self.settings["work_minutes"]),
        )
        self.step_short = MinuteSteppersWidget(
            "Short Break",
            "min",
            THEME["short_break"],
            min_val=1,
            max_val=60,
            initial=int(self.settings["short_break_minutes"]),
        )
        self.step_long = MinuteSteppersWidget(
            "Long Break",
            "min",
            THEME["long_break"],
            min_val=1,
            max_val=90,
            initial=int(self.settings["long_break_minutes"]),
        )
        self.step_rounds = MinuteSteppersWidget(
            "Rounds / Cycle",
            "rnd",
            "#A37AFC",
            min_val=1,
            max_val=12,
            initial=int(self.settings["rounds"]),
        )

        self.step_work.valueChanged.connect(lambda v: self._on_custom_duration_changed("work_minutes", v))
        self.step_short.valueChanged.connect(lambda v: self._on_custom_duration_changed("short_break_minutes", v))
        self.step_long.valueChanged.connect(lambda v: self._on_custom_duration_changed("long_break_minutes", v))
        self.step_rounds.valueChanged.connect(lambda v: self._on_custom_duration_changed("rounds", v))

        layout.addWidget(self.step_work)
        layout.addWidget(self.step_short)
        layout.addWidget(self.step_long)
        layout.addWidget(self.step_rounds)

        # --- Section 3: Preferences & Behavior ---
        sec3_lbl = QLabel("PREFERENCES")
        sec3_lbl.setStyleSheet(
            f"color: {THEME['text_muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1.4px; margin-top: 4px;"
        )
        layout.addWidget(sec3_lbl)

        chk_style = f"""
            QCheckBox {{
                color: {THEME['text_primary']};
                font-size: 12px;
                font-weight: 500;
                spacing: 8px;
                padding: 3px 2px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {THEME['border']};
                background-color: {THEME['bg_input']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {THEME['work']};
                border-color: {THEME['work']};
            }}
        """

        self.chk_always_top = QCheckBox("Always on Top (Pin window)")
        self.chk_always_top.setStyleSheet(chk_style)
        self.chk_always_top.toggled.connect(self._on_chk_always_top)

        self.chk_auto_break = QCheckBox("Auto-start Breaks when Focus ends")
        self.chk_auto_break.setStyleSheet(chk_style)
        self.chk_auto_break.toggled.connect(
            lambda v: self._update_bool_setting("auto_start_break", v)
        )

        self.chk_auto_work = QCheckBox("Auto-start Focus when Break ends")
        self.chk_auto_work.setStyleSheet(chk_style)
        self.chk_auto_work.toggled.connect(
            lambda v: self._update_bool_setting("auto_start_work", v)
        )

        self.chk_notify = QCheckBox("Desktop notification on session end")
        self.chk_notify.setStyleSheet(chk_style)
        self.chk_notify.toggled.connect(
            lambda v: self._update_bool_setting("notifications_enabled", v)
        )

        self.chk_sound = QCheckBox("Play chime sound on session end")
        self.chk_sound.setStyleSheet(chk_style)
        self.chk_sound.toggled.connect(self._on_chk_sound)

        layout.addWidget(self.chk_always_top)
        layout.addWidget(self.chk_auto_break)
        layout.addWidget(self.chk_auto_work)
        layout.addWidget(self.chk_notify)
        layout.addWidget(self.chk_sound)

        # Test sound button
        test_sound_btn = QPushButton("Test Notification Chime")
        test_sound_btn.setCursor(Qt.PointingHandCursor)
        test_sound_btn.setFixedHeight(30)
        test_sound_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {THEME['bg_card']};
                color: {THEME['text_secondary']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {THEME['bg_card_hover']};
                color: {THEME['text_primary']};
            }}
            """
        )
        test_sound_btn.clicked.connect(
            lambda: self.sound_mgr.play("work_end", int(self.settings.get("sound_volume", 80)))
        )
        layout.addWidget(test_sound_btn)

        layout.addStretch()
        scroll.setWidget(content)
        outer_v.addWidget(scroll, 1)

        # Done button to return to Timer view
        btn_done = QPushButton("Back to Timer")
        btn_done.setCursor(Qt.PointingHandCursor)
        btn_done.setFixedHeight(36)
        btn_done.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {THEME['work']};
                color: #181C24;
                border: none;
                border-radius: 9px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {THEME['work_glow']};
            }}
            """
        )
        btn_done.clicked.connect(self.toggle_settings_view)
        outer_v.addWidget(btn_done)

        return page

    # -----------------------------------------------------------------------
    # Keyboard Shortcuts
    # -----------------------------------------------------------------------

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.toggle_start_pause)
        QShortcut(QKeySequence("R"), self, activated=self.reset_current_session)
        QShortcut(QKeySequence("S"), self, activated=self.skip_session)
        QShortcut(QKeySequence("M"), self, activated=self.toggle_mute)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.toggle_always_on_top)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.toggle_compact_mode)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.toggle_settings_view)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)

    # -----------------------------------------------------------------------
    # UI State Synchronization
    # -----------------------------------------------------------------------

    def _sync_ui_from_settings(self):
        # Always on top button & badge
        aot = bool(self.settings.get("always_on_top", True))
        accent = SESSION_MODES[self.current_mode]["color"]
        self.btn_pin.set_active(aot, accent)
        self._update_pin_badge()

        # Checkboxes
        self.chk_always_top.blockSignals(True)
        self.chk_always_top.setChecked(aot)
        self.chk_always_top.blockSignals(False)

        self.chk_auto_break.blockSignals(True)
        self.chk_auto_break.setChecked(bool(self.settings.get("auto_start_break", False)))
        self.chk_auto_break.blockSignals(False)

        self.chk_auto_work.blockSignals(True)
        self.chk_auto_work.setChecked(bool(self.settings.get("auto_start_work", False)))
        self.chk_auto_work.blockSignals(False)

        self.chk_notify.blockSignals(True)
        self.chk_notify.setChecked(bool(self.settings.get("notifications_enabled", True)))
        self.chk_notify.blockSignals(False)

        snd = bool(self.settings.get("sound_enabled", True))
        self.chk_sound.blockSignals(True)
        self.chk_sound.setChecked(snd)
        self.chk_sound.blockSignals(False)
        self.btn_mute.set_icon_type("volume_on" if snd else "volume_off")

        # Steppers
        self.step_work.setValue(int(self.settings["work_minutes"]), block_signal=True)
        self.step_short.setValue(int(self.settings["short_break_minutes"]), block_signal=True)
        self.step_long.setValue(int(self.settings["long_break_minutes"]), block_signal=True)
        self.step_rounds.setValue(int(self.settings["rounds"]), block_signal=True)

        self._style_preset_buttons()
        self._style_mode_tabs()
        self._update_preset_badge()

        if bool(self.settings.get("compact_mode", False)):
            self._apply_compact_mode(True)

    def _update_pin_badge(self):
        aot = bool(self.settings.get("always_on_top", True))
        accent = SESSION_MODES[self.current_mode]["color"]
        if aot:
            self.pin_badge.setText("ON TOP")
            self.pin_badge.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 16);
                    color: {accent};
                    border: 1px solid {accent};
                    border-radius: 8px;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 0.8px;
                    padding: 1px 6px;
                }}
                """
            )
        else:
            self.pin_badge.setText("UNPINNED")
            self.pin_badge.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {THEME['text_muted']};
                    border: 1px solid {THEME['border']};
                    border-radius: 8px;
                    font-size: 9px;
                    font-weight: 600;
                    letter-spacing: 0.8px;
                    padding: 1px 6px;
                }}
                QPushButton:hover {{
                    color: {THEME['text_secondary']};
                }}
                """
            )

    def _style_mode_tabs(self):
        for mode_key, btn in self.mode_buttons.items():
            meta = SESSION_MODES[mode_key]
            if mode_key == self.current_mode:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {THEME['bg_card']};
                        color: {meta['color']};
                        border: 1px solid {meta['color']};
                        border-radius: 7px;
                        font-size: 11px;
                        font-weight: 700;
                    }}
                    """
                )
            else:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {THEME['text_secondary']};
                        border: none;
                        border-radius: 7px;
                        font-size: 11px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        color: {THEME['text_primary']};
                        background-color: rgba(255, 255, 255, 10);
                    }}
                    """
                )

    def _style_preset_buttons(self):
        active_id = self.settings.get("preset_id", "classic")
        accent = SESSION_MODES[self.current_mode]["color"]
        configs = self.settings.get("preset_configs", DEFAULT_PRESET_CONFIGS)
        for p in PRESETS:
            pid = p["id"]
            btn = self.preset_buttons.get(pid)
            if not btn:
                continue
            cfg = configs.get(pid, DEFAULT_PRESET_CONFIGS[pid])
            w = int(cfg["work_minutes"])
            s = int(cfg["short_break_minutes"])
            l = int(cfg["long_break_minutes"])
            r = int(cfg["rounds"])
            btn.setText(f"{p['name']}\n{w} / {s} / {l}m · {r}r")
            if pid == active_id:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {THEME['bg_card_hover']};
                        color: {THEME['text_primary']};
                        border: 1.5px solid {accent};
                        border-radius: 9px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px;
                    }}
                    """
                )
            else:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {THEME['bg_card']};
                        color: {THEME['text_secondary']};
                        border: 1px solid {THEME['border']};
                        border-radius: 9px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {THEME['bg_card_hover']};
                        color: {THEME['text_primary']};
                    }}
                    """
                )

    def _update_preset_badge(self):
        pid = self.settings.get("preset_id", "classic")
        preset_name = "Custom"
        for p in PRESETS:
            if p["id"] == pid:
                preset_name = p["name"]
                break
        w = int(self.settings["work_minutes"])
        s = int(self.settings["short_break_minutes"])
        l = int(self.settings["long_break_minutes"])
        self.btn_preset_badge.setText(f"{preset_name} · {w}/{s}/{l}m")

    # -----------------------------------------------------------------------
    # Presets & Custom Minute Handlers
    # -----------------------------------------------------------------------

    def select_preset(self, preset_id: str):
        self.settings["preset_id"] = preset_id
        configs = self.settings.setdefault(
            "preset_configs",
            {k: dict(v) for k, v in DEFAULT_PRESET_CONFIGS.items()},
        )
        cfg = configs.get(preset_id, DEFAULT_PRESET_CONFIGS.get(preset_id, DEFAULT_PRESET_CONFIGS["classic"]))
        self.settings["work_minutes"] = int(cfg["work_minutes"])
        self.settings["short_break_minutes"] = int(cfg["short_break_minutes"])
        self.settings["long_break_minutes"] = int(cfg["long_break_minutes"])
        self.settings["rounds"] = int(cfg["rounds"])

        self.step_work.setValue(int(self.settings["work_minutes"]), block_signal=True)
        self.step_short.setValue(int(self.settings["short_break_minutes"]), block_signal=True)
        self.step_long.setValue(int(self.settings["long_break_minutes"]), block_signal=True)
        self.step_rounds.setValue(int(self.settings["rounds"]), block_signal=True)

        self.total_rounds = int(self.settings["rounds"])
        if self.current_round > self.total_rounds:
            self.current_round = 1

        self.save_settings()
        self._style_preset_buttons()
        self._update_preset_badge()
        self._apply_duration_Change_to_active_timer()

    def reset_active_preset_to_default(self):
        active_id = self.settings.get("preset_id", "classic")
        default_cfg = DEFAULT_PRESET_CONFIGS.get(active_id, DEFAULT_PRESET_CONFIGS["classic"])
        configs = self.settings.setdefault(
            "preset_configs",
            {k: dict(v) for k, v in DEFAULT_PRESET_CONFIGS.items()},
        )
        configs[active_id] = dict(default_cfg)
        self.select_preset(active_id)

    def _on_custom_duration_changed(self, key: str, value: int):
        val = int(value)
        self.settings[key] = val
        active_id = self.settings.get("preset_id", "classic")
        configs = self.settings.setdefault(
            "preset_configs",
            {k: dict(v) for k, v in DEFAULT_PRESET_CONFIGS.items()},
        )
        if active_id not in configs:
            configs[active_id] = dict(DEFAULT_PRESET_CONFIGS.get(active_id, DEFAULT_PRESET_CONFIGS["classic"]))
        configs[active_id][key] = val

        self.total_rounds = int(self.settings["rounds"])
        if self.current_round > self.total_rounds:
            self.current_round = self.total_rounds

        self.save_settings()
        self._style_preset_buttons()
        self._update_preset_badge()
        self._apply_duration_Change_to_active_timer()

    def _apply_duration_Change_to_active_timer(self):
        new_total = self._get_mode_duration_seconds(self.current_mode)
        self.total_seconds = new_total
        if not self.is_running:
            self.remaining_seconds = new_total
        else:
            self.remaining_seconds = min(self.remaining_seconds, new_total)
        self._update_timer_display(animate=False)

    def _update_bool_setting(self, key: str, value: bool):
        self.settings[key] = bool(value)
        self.save_settings()

    def _on_chk_always_top(self, checked: bool):
        if bool(self.settings.get("always_on_top", True)) != checked:
            self.toggle_always_on_top()

    def _on_chk_sound(self, checked: bool):
        self.settings["sound_enabled"] = bool(checked)
        self.btn_mute.set_icon_type("volume_on" if checked else "volume_off")
        self.save_settings()

    def toggle_mute(self):
        new_val = not bool(self.settings.get("sound_enabled", True))
        self.settings["sound_enabled"] = new_val
        self.chk_sound.blockSignals(True)
        self.chk_sound.setChecked(new_val)
        self.chk_sound.blockSignals(False)
        self.btn_mute.set_icon_type("volume_on" if new_val else "volume_off")
        self.save_settings()

    def toggle_settings_view(self):
        # If in compact mode, expand first so settings are visible
        if bool(self.settings.get("compact_mode", False)) and self.stack.currentIndex() == 0:
            self.toggle_compact_mode()

        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)
            self.btn_settings.set_active(
                True, SESSION_MODES[self.current_mode]["color"]
            )
        else:
            self.stack.setCurrentIndex(0)
            self.btn_settings.set_active(False)

    # -----------------------------------------------------------------------
    # Core Timer Logic
    # -----------------------------------------------------------------------

    def _get_mode_duration_seconds(self, mode: str) -> int:
        if mode == "work":
            return int(self.settings["work_minutes"]) * 60
        elif mode == "short_break":
            return int(self.settings["short_break_minutes"]) * 60
        else:
            return int(self.settings["long_break_minutes"]) * 60

    def toggle_start_pause(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.remaining_seconds <= 0:
            self.remaining_seconds = self.total_seconds
        self.is_running = True
        self.tick_timer.start()
        self._update_timer_display(animate=False)

    def pause_timer(self):
        self.is_running = False
        self.tick_timer.stop()
        self._update_timer_display(animate=False)

    def reset_current_session(self):
        self.pause_timer()
        self.total_seconds = self._get_mode_duration_seconds(self.current_mode)
        self.remaining_seconds = self.total_seconds
        self._update_timer_display(animate=True)

    def reset_all_rounds(self):
        self.current_round = 1
        self.switch_mode("work", manual=True)

    def _pick_next_exercise(self, mode: str = None, avoid_current: bool = True):
        target_mode = mode or self.current_mode
        pool = BREAK_EXERCISES.get(target_mode, BREAK_EXERCISES["short_break"])
        if not pool:
            return None
        candidates = pool
        if avoid_current and self.current_exercise in pool and len(pool) > 1:
            candidates = [ex for ex in pool if ex != self.current_exercise]
        self.current_exercise = random.choice(candidates)
        if target_mode in ("short_break", "long_break"):
            self.stretch_popup.set_exercise(
                self.current_exercise,
                target_mode,
                SESSION_MODES[target_mode]["color"],
            )
        return self.current_exercise

    def switch_mode(self, mode: str, manual: bool = False):
        self.pause_timer()
        self.current_mode = mode
        self.total_seconds = self._get_mode_duration_seconds(mode)
        self.remaining_seconds = self.total_seconds

        accent = SESSION_MODES[mode]["color"]
        self.title_dot.setStyleSheet(
            f"background-color: {accent}; border-radius: 4px;"
        )
        aot = bool(self.settings.get("always_on_top", True))
        self.btn_pin.set_active(aot, accent)
        self.btn_compact.set_active(bool(self.settings.get("compact_mode", False)), accent)

        self._update_window_geometry()
        self._update_pin_badge()
        self._style_mode_tabs()
        self._style_preset_buttons()
        self._update_timer_display(animate=False)

        if mode in ("short_break", "long_break"):
            if self.current_exercise is None or manual:
                self._pick_next_exercise(mode=mode, avoid_current=True)
            else:
                self.stretch_popup.set_exercise(self.current_exercise, mode, accent)
            self.stretch_popup.set_always_on_top(aot)
            self.stretch_popup.position_near(self)
            self.stretch_popup.show()
            self.stretch_popup.raise_()
            QTimer.singleShot(50, self._enforce_x11_above)
        else:
            self.stretch_popup.hide()

    def skip_session(self):
        self._advance_session(completed_naturally=False)

    def _on_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_timer_display(animate=True)

        if self.remaining_seconds <= 0:
            self._advance_session(completed_naturally=True)

    def _advance_session(self, completed_naturally: bool = True):
        self.pause_timer()
        prev_mode = self.current_mode

        if prev_mode == "work":
            if self.current_round >= self.total_rounds:
                next_mode = "long_break"
            else:
                next_mode = "short_break"
            # Pick a fresh break exercise before alerts and mode switch
            self._pick_next_exercise(mode=next_mode, avoid_current=True)
        else:
            # Finishing a break moves to work
            if prev_mode == "long_break":
                self.current_round = 1
            else:
                self.current_round = min(self.total_rounds, self.current_round + 1)
            next_mode = "work"

        if completed_naturally:
            self._trigger_session_alerts(prev_mode, next_mode)

        self.switch_mode(next_mode, manual=False)

        # Auto-start next session if configured
        if completed_naturally:
            if next_mode in ("short_break", "long_break") and self.settings.get("auto_start_break", False):
                self.start_timer()
            elif next_mode == "work" and self.settings.get("auto_start_work", False):
                self.start_timer()

    def _trigger_session_alerts(self, prev_mode: str, next_mode: str):
        # 1. Chime Sound
        if self.settings.get("sound_enabled", True):
            sound_kind = "work_end" if prev_mode == "work" else "break_end"
            vol = int(self.settings.get("sound_volume", 80))
            self.sound_mgr.play(sound_kind, vol)

        # 2. Desktop OS Notification
        if self.settings.get("notifications_enabled", True):
            if prev_mode == "work":
                brk_min = (
                    self.settings["long_break_minutes"]
                    if next_mode == "long_break"
                    else self.settings["short_break_minutes"]
                )
                title = "Focus Session Complete!"
                body = f"Time for a {brk_min}-minute {SESSION_MODES[next_mode]['short_label'].lower()}."
                if self.current_exercise:
                    body += f"\n✦ {self.current_exercise['title']}: {self.current_exercise['desc']}"
            else:
                title = "Break Finished!"
                body = f"Ready for Focus Round {self.current_round}/{self.total_rounds} ({self.settings['work_minutes']} min)."

            try:
                subprocess.Popen(
                    [
                        "notify-send",
                        "--app-name=Pomodoro",
                        "-i",
                        "alarm-symbolic",
                        title,
                        body,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    def _format_seconds(self, secs: int) -> str:
        mins, s = divmod(max(0, secs), 60)
        return f"{mins:02d}:{s:02d}"

    def _update_timer_display(self, animate: bool = True):
        mins, secs = divmod(max(0, self.remaining_seconds), 60)
        time_str = f"{mins:02d}:{secs:02d}"
        meta = SESSION_MODES[self.current_mode]

        progress = (
            self.remaining_seconds / float(self.total_seconds)
            if self.total_seconds > 0
            else 0.0
        )

        self.dial.set_dial_state(
            progress=progress,
            time_text=time_str,
            mode_label=meta["label"],
            accent_hex=meta["color"],
            glow_hex=meta["glow"],
            is_running=self.is_running,
            animate=animate,
        )

        self.btn_play.set_state(self.is_running, meta["color"])
        self.lbl_rounds.setText(f"{self.current_round} / {self.total_rounds}")
        self.setWindowTitle(f"{time_str} — {meta['short_label']} · Pomodoro")

    # -----------------------------------------------------------------------
    # Frameless Window Dragging
    # -----------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "stretch_popup") and self.stretch_popup is not None:
            self.stretch_popup.close()
        super().closeEvent(event)


def create_app_icon() -> QIcon:
    """Loads theme alarm icon with a crisp custom-rendered vector fallback for Dock/Taskbar."""
    icon = QIcon.fromTheme("alarm-symbolic")
    if not icon.isNull():
        return icon

    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128):
        pix = QPixmap(sz, sz)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        s = sz / 64.0
        # Rounded dark badge background
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(THEME["bg_main"]))
        p.drawRoundedRect(QRectF(4 * s, 4 * s, 56 * s, 56 * s), 14 * s, 14 * s)
        # Coral progress ring
        pen = QPen(QColor(THEME["work"]), 5.5 * s, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(14 * s, 14 * s, 36 * s, 36 * s))
        # Clock hands
        p.setPen(QPen(QColor(THEME["text_primary"]), 4.0 * s, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(32 * s, 32 * s), QPointF(32 * s, 21 * s))
        p.drawLine(QPointF(32 * s, 32 * s), QPointF(40 * s, 32 * s))
        p.end()
        icon.addPixmap(pix)
    return icon


def main():
    # Enable High-DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro")
    app.setDesktopFileName("pomotroid-timer")
    app_icon = create_app_icon()
    app.setWindowIcon(app_icon)
    app.setStyleSheet(
        f"""
        QToolTip {{
            background-color: {THEME['bg_outer']};
            color: {THEME['text_primary']};
            border: 1px solid {THEME['border']};
            border-radius: 5px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        """
    )

    window = PomodoroWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
