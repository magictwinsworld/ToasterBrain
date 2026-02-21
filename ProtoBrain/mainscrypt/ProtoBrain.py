#!/usr/bin/env python3
# my_app.py
import os
import collections
import sys
import threading
import json
from operator import truediv

import requests
import time
import traceback
import random
import sys

#bluetooth
import serial
import subprocess

from typing import List, Dict, Any, Tuple
from samplebase import SampleBase
# noinspection PyUnresolvedReferences
from rgbmatrix import RGBMatrixOptions, RGBMatrixOptions, graphics

# AutoControll
import pyaudio
import numpy as np

# InsideScreen
import smbus2
import time

import colorsys

import contextlib

@contextlib.contextmanager
def ignore_stderr():
    """Context manager to suppress console noise from ALSA/PyAudio."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


# Booptriger

# --- THREAD LOCK DEFINITION ---
# We use RLock (Reentrant Lock) so the same thread can acquire it multiple times without blocking itself
lcd_lock = threading.RLock()

# InsideScreen
I2C_ADDR = 0x27  # your LCD address
LCD_WIDTH = 16  # max characters per line
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0

LCD_BACKLIGHT = 0x08
ENABLE = 0b00000100

last_lcd_init_time = 0
lcd_needs_init = False

# Audio Config
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

with ignore_stderr():
    audio = pyaudio.PyAudio()

bus = smbus2.SMBus(1)


# --- BLUETOOTH CONFIG ---
BT_SERIAL_PORT = "/dev/rfcomm0"  # Default for paired BT serial devices
BT_BAUD_RATE = 9600


def lcd_toggle_enable(bits):
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)


def lcd_byte(bits, mode):
    high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    low = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, high)
    lcd_toggle_enable(high)
    bus.write_byte(I2C_ADDR, low)
    lcd_toggle_enable(low)


def lcd_init():
    lcd_byte(0x33, LCD_CMD)
    lcd_byte(0x32, LCD_CMD)
    lcd_byte(0x06, LCD_CMD)
    lcd_byte(0x0C, LCD_CMD)
    lcd_byte(0x28, LCD_CMD)
    lcd_byte(0x01, LCD_CMD)
    time.sleep(0.005)


def lcd_message(message, line):
    lcd_byte(line, LCD_CMD)
    for char in message.ljust(LCD_WIDTH, " "):
        try:
            lcd_byte(ord(char), LCD_CHR)
        except:
            continue


def lcd_display_string(message):
    for c in message:
        try:
            lcd_byte(ord(c), LCD_CHR)
        except:
            continue


try:
    with lcd_lock:
        lcd_init()
except:
    print("Screen Init Failed")


def lcd_set_cursor(line, col):
    if line == 1:
        lcd_byte(0x80 + col, LCD_CMD)
    elif line == 2:
        lcd_byte(0xC0 + col, LCD_CMD)


# --- UPDATED FUNCTION WITH LOCK AND ERROR HANDLING ---
def lcd_insidescreen_controll(message, typelcdupdate):
    # This lock prevents the Timer thread and Main thread from hitting the I2C bus simultaneously
    global lcd_needs_init, last_lcd_init_time
    with lcd_lock:
        try:
            if lcd_needs_init and (time.time() - last_lcd_init_time > 5):
                print("Attempting LCD Recovery...")
                lcd_init()
                lcd_insidescreen_controller_INT()  # Restore your B90FU... layout
                lcd_needs_init = False
            if typelcdupdate != "Blink":
                if message == "":
                    app.send_bluetooth_message(typelcdupdate)
                else:
                    app.send_bluetooth_message(typelcdupdate + " " + message)



        except Exception as BE:
            print(f"General SendBluetooth Error: {BE}")
        try:
            if typelcdupdate == "CommandOver":
                lcd_message(message, LCD_LINE_2)
                # Safe split check
                if ":" in message:
                    parts = message.split(":", 1)
                    messageType = parts[0]
                    messageValue = parts[1]
                else:
                    messageType = message
                    messageValue = ""

                print(messageType)
                if messageType == "SB":
                    lcd_set_cursor(1, 0)
                    # Safe number conversion
                    try:
                        val = int(messageValue)
                        if val >= 100:
                            messageValue = "99"
                        else:
                            messageValue = str(val)
                    except ValueError:
                        pass  # keep original string if not int

                    lcd_display_string("B" + messageValue)
                    print("B" + messageValue)

                if messageType == "SE":
                    lcd_set_cursor(1, 3)
                    # Safe slice in case string is short
                    disp_val = messageValue[:2] if len(messageValue) >= 2 else messageValue
                    lcd_display_string("F" + disp_val)
                    lcd_set_cursor(1, 15)
                    lcd_display_string("X")

            elif typelcdupdate == "Blink":
                lcd_set_cursor(1, 15)
                if message == "BlinkON":
                    lcd_display_string("B")
                else:
                    lcd_display_string("b")

            elif typelcdupdate == "Mic":
                lcd_set_cursor(1, 14)
                if message == "MicON":
                    lcd_display_string("M")
                else:
                    lcd_display_string("m")

            elif typelcdupdate == "Boop":
                lcd_set_cursor(1, 13)
                if message == "BoopOn":
                    lcd_display_string("3")
                elif message == "BoopDisabled":
                    lcd_display_string("X")
                else:
                    lcd_display_string("-")
        except OSError as BE:
            if not lcd_needs_init:
                print("LCD Disconnected/I2C Error. Waiting for reconnection...")
                lcd_needs_init = True
                last_lcd_init_time = time.time()

        except Exception as BE:
            print(f"General LCD Error: {BE}")


def lcd_insidescreen_controller_INT():
    print("LCD_INT")
    with lcd_lock:
        try:
            lcd_set_cursor(1, 0)
            lcd_display_string("B90FU_        mX")
        except Exception as e:
            print(f"LCD Init Text Failed: {e}")


# Automatically pick USB mic by name
device_index = None
for i in range(audio.get_device_count()):
    dev = audio.get_device_info_by_index(i)
    if "usb" in dev["name"].lower():
        device_index = i
        break

if device_index is None:
    print("USB microphone not found!")
else:
    print("Using device:", audio.get_device_info_by_index(device_index)["name"])

try:
    with ignore_stderr():  # Wrap the stream opening too
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
except:
    stream = None
    print("USB microphone not found!")

print("Listening...")


def shift_hue(hex_color, shift_amount=0.01):
    """
    Shifts the hue of a HEX color string in a circle.
    :param hex_color: String like "#00FFFF"
    :param shift_amount: Float between 0.0 and 1.0 (0.01 is a 'tiny bit')
    :return: Updated HEX string
    """
    # 1. Clean the HEX string and convert to RGB (0-1 scale)
    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    # 2. Convert RGB to HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # 3. Apply the shift and use modulo (%) to keep it in a 0.0-1.0 circle
    new_h = (h + shift_amount) % 1.0

    # 4. Convert back to RGB
    new_r, new_g, new_b = colorsys.hls_to_rgb(new_h, l, s)

    # 5. Format back into a HEX string
    return "#{:02X}{:02X}{:02X}".format(
        int(round(new_r * 255)),
        int(round(new_g * 255)),
        int(round(new_b * 255))
    )



# --- CONFIGURATION ---
QUEUE_URL = "https://magictwin.net/proto/Data/Public-Queue?key=ToasterControl_LockedData30590325246954"
QUEUE_URL = QUEUE_URL + "&istwinpi=1"

MarkeAllisDOne = 1
if MarkeAllisDOne:
    QUEUE_URL = QUEUE_URL + "&MarkeAllAsDone=1"

FETCH_INTERVAL_SECONDS = 7
FALLBACK_COLOR_HEX = "#00FFFF"
MainColorHex = "#00FFFF"
DefaultBrightness = 90
BLINK_DURATION = 0.2  # Duration the blink eye is displayed (seconds)
# Renamed for clarity, default animation duration
DEFAULT_ANIMATION_DURATION = 6.0


def is_positive_number_string(input_string):
    try:
        # 1. Convert the string to a floating-point number (handles integers and decimals)
        number = float(input_string)

        # 2. Check if the resulting number is greater than 0
        if number > 0:
            return True
        else:
            return False

    except ValueError:
        # If float(input_string) fails, it means the string is not a valid number
        return False


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    # This function runs perfectly Dont change a thing
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return 0, 0, 0
    try:
        r = int(hex_color[0:2], 16)
        b = int(hex_color[2:4], 16)
        g = int(hex_color[4:6], 16)
        return r, g, b
    except ValueError:
        return 0, 0, 0


class MyMatrixApp(SampleBase):
    def __init__(self, *args, **kwargs):
        super(MyMatrixApp, self).__init__(*args, **kwargs)

        base_dir = os.path.abspath(os.path.dirname(__file__))
        self.state_file = os.path.join(base_dir, "last_state.json")


        self.stop_event = threading.Event()
        self.timer = None

        self.command_queue = collections.deque()
        self.queue_lock = threading.Lock()
        self.next_fetch_time = time.time()

        # color + brightness
        self.current_color = MainColorHex
        self.current_brightness = DefaultBrightness

        # text mode
        self.text_mode_active = False
        self.text_to_display = ""
        self.scroll_offset = 0
        self.scroll_speed = 1

        # grid mode
        self.grid_mode_active = False
        self.custom_grid = []
        self.grid_end_time = 0

        # Target position the eyes WANT to be at
        self.target_offset_x = 0
        self.target_offset_y = 0
        # Current actual position (float for smooth math)
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        # How fast they move (0.05 = slow, 0.2 = fast)
        self.lerp_speed = 0.1


        # Animation mode - Start Wipe Animation (Type 3) on boot
        self.animation_mode_active = True
        self.animation_start_time = time.time()
        self.current_animation_type = "3"
        # Use a dynamic end time instead of fixed constant
        self.animation_end_time = time.time() + DEFAULT_ANIMATION_DURATION

        # New DVD Logo State (Type 4)
        self.dvd_initialized = False  # Flag to set initial position based on matrix size
        self.dvd_x = 0
        self.dvd_y = 0
        self.dvd_dx = random.choice([-1, 1])
        self.dvd_dy = random.choice([-1, 1])
        self.dvd_color_index = 0
        self.dvd_colors = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (0, 255, 255),  # Cyan
            (255, 0, 255),  # Magenta
        ]
        self.last_dvd_update = time.time()
        self.dvd_update_interval = 0.1  # Move every 100ms
        self.dvd_grid = []  # Stores the loaded pixel grid for the logo

        # New variables to handle animation activation after asset load
        self.animation_pending_type = None
        self.animation_pending_duration = 0.0

        # Blinking mode
        self.blinkingtoggle = True
        self.mouthtoggle = True
        self.ismouthopen = False
        self.booptoggle = True
        self.mouthVolume = 10
        self.voicethreshhold = 4

        self.audiolinkmode = False
        self.audiolinkmaxvoulme = 5

        self.blink_map = {
            "Tired_Eyes.json": "Tired_Blink.json",
            "Angry_Eyes.json": "Angry_Blink.json",
            "Happy_Eyes.json": "Happy_Blink.json",
            "Sad_Eyes.json": "Sad_Blink.json",
            "Love_Eyes.json": "Love_Blink.json",
            "Love_Eyes_Blink.json": "NoBlink",
            "O_Eyes.json": "NoBlink",
            "U_Eyes.json": "NoBlink",
            "X_Eyes.json": "NoBlink",
        }
        self.current_blink_grid = []
        self.is_blinking = False
        self.blink_end_time = 0
        self.next_blink_time = time.time() + self._get_random_blink_interval()

        # face directories
        base_dir = os.path.abspath(os.path.dirname(__file__))
        self.eyes_dir = os.path.normpath(os.path.join(base_dir, "..", "Faces", "Eyes"))
        self.mouth_dir = os.path.normpath(os.path.join(base_dir, "..", "Faces", "Mouth"))
        self.blink_dir = os.path.normpath(os.path.join(base_dir, "..", "Faces", "Blink"))
        self.nose_dir = os.path.normpath(os.path.join(base_dir, "..", "Faces", "Nose"))

        # Initial load


        # New animation directory for DVD.json
        self.animation_dir = os.path.normpath(os.path.join(base_dir, "..", "Faces", "Animation"))

        self.current_nose_grid = []
        self.current_eyes_grid = []
        self.current_mouth_grid = []
        self.current_nose_name = "Nose.json"
        self.current_eyes_name = self.load_saved_eyes_name()
        self.current_mouth_name = "Mouth_Close.json"
        self.current_mouth_open_name = "Mouth_Open.json"  # Storing the open mouth file name

        # initial loads (safe)
        self.load_face_component("eyes", self.current_eyes_name)
        self.load_face_component("mouth", self.current_mouth_name)
        self.load_face_component("nose", self.current_nose_name)

        #Offset
        self.face_offset_x = 0
        self.face_offset_y = 0


        # font
        self.font = graphics.Font()
        try:
            self.font.LoadFont("../../rpi-rgb-led-matrix/fonts/10x20.bdf")
        except:
            print("Font failed to load, text mode disabled.")
            self.font = None

        try:
            lcd_insidescreen_controller_INT()
        except:
            print("LCD INIT failed.")

        # Bluetooth Thread Setup
        self.bt_thread = threading.Thread(target=self.listen_bluetooth, daemon=True)
        self.bt_thread.start()

        # Boop Logic Variables
        self.boop_lockout_time = 0  # Timestamp for when we can boop again
        self.boop_duration = 1.0  # How long heart eyes stay (seconds)
        self.boop_cooldown = 2.0  # Cooldown before next boop (seconds)
        self.boop_active_until = 0  # Timestamp for when heart eyes revert
        self.is_booped = False
        self.pending_boop_trigger = False # Flag to signal main loop
        self.pre_boop_eyes = "U_Eyes.json" # Memory of eye state before boop
        self.sensor_is_currently_booped = False


        # Start Boop Thread
        self.boop_thread = threading.Thread(target=self.monitor_boop_sensor, daemon=True)
        self.boop_thread.start()

    def monitor_boop_sensor(self):
        """Background thread to monitor the VL53L0X sensor."""
        VL_ADDR = 0x29
        consecutive_hits = 0

        print("Boop Thread: VL53L0X Monitoring started.")

        while not self.stop_event.is_set():
            if not self.booptoggle:
                time.sleep(0.5)
                continue

            try:
                # Use the existing LCD lock to prevent I2C collisions
                with lcd_lock:
                    # Trigger measurement
                    bus.write_byte_data(VL_ADDR, 0x00, 0x01)
                    time.sleep(0.05)
                    hi = bus.read_byte_data(VL_ADDR, 0x1E)
                    lo = bus.read_byte_data(VL_ADDR, 0x1F)
                    distance = (hi << 8) | lo

                current_time = time.time()
                # Logic: Check if distance is close, not the '20' error, and we aren't in cooldown
                if 10 < distance <= 125 and distance != 20:
                    consecutive_hits += 1
                else:
                    consecutive_hits = 0

                self.sensor_is_currently_booped = (consecutive_hits >= 2)

                if consecutive_hits >= 2 and current_time > self.boop_lockout_time:
                    with self.queue_lock:
                        # Only trigger if no animation is playing
                        if not self.animation_mode_active and not self.is_booped:
                            print("BOOP DETECTED!")
                            self.pending_boop_trigger = True
                    consecutive_hits = 0
                time.sleep(0.1)

            except Exception as e:
                time.sleep(1)

    def _get_random_blink_interval(self) -> float:
        return random.uniform(4, 8)

    def listen_bluetooth(self):
        """Listens for incoming JSON commands and sends a confirmation back"""
        print(f"Bluetooth Thread: Waiting for {BT_SERIAL_PORT}...")

        while not self.stop_event.is_set():
            if not os.path.exists(BT_SERIAL_PORT):
                time.sleep(2)
                continue

            try:
                os.system(f"sudo chmod 666 {BT_SERIAL_PORT}")

                with serial.Serial(BT_SERIAL_PORT, BT_BAUD_RATE, timeout=1) as ser:
                    print(">>> BLUETOOTH DEVICE CONNECTED <<<")

                    while not self.stop_event.is_set():
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8').strip()
                            if not line:
                                continue

                            try:
                                new_commands = json.loads(line)
                                if isinstance(new_commands, dict):
                                    new_commands = [new_commands]

                                with self.queue_lock:
                                    self.command_queue.extendleft(reversed(new_commands))

                                # --- NEW: SEND CONFIRMATION BACK ---
                                response = {"status": "accepted", "count": len(new_commands)}
                                ser.write((json.dumps(response) + "\n").encode('utf-8'))
                                # -----------------------------------

                                if self.timer:
                                    self.timer.cancel()
                                    self.process_command()

                            except json.JSONDecodeError:
                                # Send error message back if JSON is bad
                                ser.write(b'{"status": "error", "message": "Invalid JSON"}\n')

                        time.sleep(0.1)

            except Exception as e:
                print(f"Bluetooth connection lost or error: {e}")
                time.sleep(2)



    # ------------------------------------------------------
    # SAFE FACE LOADER (file I/O OUTSIDE LOCK ONLY)
    # ------------------------------------------------------
    def load_face_component(self, component_type: str, name: str) -> bool:
        if component_type == "eyes":
            directory = self.eyes_dir
        elif component_type == "mouth":
            directory = self.mouth_dir
        elif component_type == "nose":
            directory = self.nose_dir
        else:
            return False

        file_path = os.path.join(directory, name)
        blink_file_name = self.blink_map.get(name)

        try:
            # load file with NO LOCK
            with open(file_path, 'r') as f:
                grid_data = json.load(f)

            blink_grid_data = []
            # Load associated blink file if one is mapped and it's not "NoBlink"
            if blink_file_name and blink_file_name != "NoBlink" and component_type == "eyes":
                blink_path = os.path.join(self.blink_dir, blink_file_name)
                with open(blink_path, 'r') as f_blink:
                    blink_grid_data = json.load(f_blink)
                print(f"Loaded blink file: {blink_file_name}")

            # update shared state WITH LOCK
            with self.queue_lock:
                if component_type == "eyes":
                    self.current_eyes_grid = grid_data
                    self.current_eyes_name = name
                    # Update blink-related state
                    self.current_blink_grid = blink_grid_data

                    # Reset the next blink timer whenever new eyes are loaded
                    if self.current_blink_grid:
                        self.next_blink_time = time.time() + self._get_random_blink_interval()
                    else:
                        self.next_blink_time = float('inf')  # Never blink if no blink file is set

                    if name != "Love_Eyes_Blink.json":
                        self.save_eyes_name(name)

                elif component_type == "nose":  # Add this
                    self.current_nose_grid = grid_data

                elif component_type == "mouth":
                    self.current_mouth_grid = grid_data
                    self.current_mouth_name = name  # Keep track of the currently loaded mouth name
                else:
                    print(f"Unknown Component Type: {component_type}")
                    return False

            print(f"Loaded {component_type}: {name}")
            return True

        except Exception as File_e:
            print(f"Failed loading {file_path} or associated blink file: {File_e}")
            return False

    # ------------------------------------------------------
    # SAFE ANIMATION LOADER (file I/O OUTSIDE LOCK ONLY)
    # ------------------------------------------------------
    def load_animation_component(self, name: str) -> bool:
        file_path = os.path.join(self.animation_dir, name)

        # Pull pending animation details from state
        pending_type = None
        pending_duration = 0.0

        with self.queue_lock:
            pending_type = self.animation_pending_type
            pending_duration = self.animation_pending_duration
            # Immediately clear pending state to prevent double-activation
            self.animation_pending_type = None
            self.animation_pending_duration = 0.0

        if not pending_type:
            # If no animation was pending, this load was unrequested or old
            return False

        try:
            # load file with NO LOCK
            with open(file_path, 'r') as f:
                grid_data = json.load(f)

            # Check if grid data is valid (list of lists)
            if not isinstance(grid_data, list) or not grid_data or not isinstance(grid_data[0], list):
                print(f"Error: Loaded data from {name} is not a valid 2D grid.")
                return False

            # update shared state and activate animation WITH LOCK
            with self.queue_lock:
                self.dvd_grid = grid_data

                # Activate animation now that the asset is ready
                if pending_type == "4":
                    self.current_animation_type = "4"
                    self.animation_start_time = time.time()
                    self.animation_end_time = time.time() + pending_duration
                    self.animation_mode_active = True  # ACTIVATE HERE, after load

            print(f"Loaded animation component: {name} ({len(self.dvd_grid[0])}x{len(self.dvd_grid)})")
            return True

        except Exception as e:
            print(f"Failed loading {file_path}: {e}")
            # Clear the grid on failure
            with self.queue_lock:
                self.dvd_grid = []
            return False


    # ------------------------------------------------------
    # PROCESS COMMANDS
    # ------------------------------------------------------
    def process_command(self):
        next_delay = 20
        must_fetch = False
        load_new_eye_file = None
        load_new_animation_file = None  # New variable to signal animation file load

        with self.queue_lock:

            if not self.command_queue:
                print(f"[{time.strftime('%H:%M:%S')}] Queue empty.")
                if time.time() >= self.next_fetch_time:
                    must_fetch = True
                    next_delay = 5

            else:
                command = self.command_queue.popleft()
                command_type = command.get("CommandType", "0")
                command_value = command.get("CommandValue", "")

                print(f"[{time.strftime('%H:%M:%S')}] Processing: {command_type} -> {command_value}")

                if command_type == "4":
                    next_delay = 3
                    self.current_color = command_value
                    lcd_insidescreen_controll("CS:" + command_value, "CommandOver")
                    # Set Custom Color
                elif command_type == "10":
                    next_delay = 3
                    try:
                        self.current_brightness = max(0, min(100, int(command_value)))
                        lcd_insidescreen_controll("SB:" + command_value, "CommandOver")
                    except:
                        pass

                elif command_type == "3":
                    #Restart
                    if command_value == "1":
                        print("Restarting System")
                        try:
                            lcd_insidescreen_controll("REBOOTING...", "CommandOver")
                        except:
                            pass

                            # This triggers the Linux reboot command immediately
                        os.system('sudo reboot')



                elif command_type == "11":
                    # Run Animation
                    next_delay = 5
                    # Disable other modes for animation
                    self.text_mode_active = False
                    self.grid_mode_active = False

                    self.current_animation_type = command_value  # Set type, but don't activate yet

                    duration = DEFAULT_ANIMATION_DURATION

                    if command_value == "4":
                        # Set duration to 30 seconds as requested
                        duration = 30.0
                        lcd_insidescreen_controll("RA:DVD", "CommandOver")
                        # Signal to load the new JSON file
                        load_new_animation_file = "DVD.json"
                        # Store pending animation details
                        self.animation_pending_type = command_value
                        self.animation_pending_duration = duration

                        # Reset initialization flag for the DVD logo position
                        self.dvd_initialized = False
                        # Set a random starting direction and color index
                        self.dvd_dx = random.choice([-1, 1])
                        self.dvd_dy = random.choice([-1, 1])
                        self.dvd_color_index = random.randint(0, len(self.dvd_colors) - 1)

                    elif command_value == "3":
                        lcd_insidescreen_controll("RA:Boot", "CommandOver")
                        # Default wipe animation loads instantly, so we can activate it here
                        self.animation_mode_active = True
                        self.animation_start_time = time.time()
                        self.animation_end_time = time.time() + duration

                    print(f"Starting animation: {command_value} for {duration} seconds (Pending asset load if type 4).")


                elif command_type == "13":
                    next_delay = 30
                    lcd_insidescreen_controll("RT:" + command_value, "CommandOver")
                    if self.font:
                        self.grid_mode_active = False
                        self.animation_mode_active = False  # Disable animation
                        self.text_to_display = command_value
                        self.scroll_offset = self.matrix.width
                        self.text_mode_active = True

                elif command_type == "14":
                    next_delay = 30
                    try:
                        self.custom_grid = json.loads(command_value)
                        self.text_mode_active = False
                        self.animation_mode_active = False  # Disable animation
                        self.grid_mode_active = True
                        self.grid_end_time = time.time() + 30
                    except:
                        print("Bad JSON for grid.")

                elif command_type == "5":
                    next_delay = 5
                    eye_map = {
                        "1": "Happy_Eyes.json",
                        "2": "Sad_Eyes.json",
                        "3": "Angry_Eyes.json",
                        "7": "Love_Eyes.json",
                        "12": "O_Eyes.json",
                        "13": "U_Eyes.json",
                        "14": "X_Eyes.json",
                        "15": "Tired_Eyes.json",
                    }
                    new_eye_file = eye_map.get(command_value)
                    if new_eye_file:
                        load_new_eye_file = new_eye_file
                        lcd_insidescreen_controll("SE:" + new_eye_file, "CommandOver")
                    else:
                        print("Unknown eye cmd")
                        lcd_insidescreen_controll("SE:ERROR", "CommandOver")

                elif command_type == "8":
                    next_delay = 2

                    if command_value == "2":
                        self.blinkingtoggle = not self.blinkingtoggle
                        if self.blinkingtoggle:
                            lcd_insidescreen_controll("TB:ON", "CommandOver")
                            print("Toggle blinking | On")
                        else:
                            lcd_insidescreen_controll("TB:OFF", "CommandOver")
                            print("Toggle blinking | Off")
                    elif command_value == "1":
                        self.blinkingtoggle = True
                        lcd_insidescreen_controll("TB:ON", "CommandOver")
                        print("Set blinking | On")
                    else:
                        self.blinkingtoggle = False
                        lcd_insidescreen_controll("TB:OFF", "CommandOver")
                        print("Set blinking | Off")

                elif command_type == "16":
                    next_delay = 2

                    if command_value == "2":
                        self.mouthtoggle = not self.mouthtoggle
                        if self.mouthtoggle:
                            lcd_insidescreen_controll("TM:ON", "CommandOver")
                            print("Toggle Mouthmovment | On")
                        else:
                            lcd_insidescreen_controll("TM:OFF", "CommandOver")
                            print("Toggle Mouthmovment | Off")
                    elif command_value == "1":
                        self.mouthtoggle = True
                        lcd_insidescreen_controll("TM:ON", "CommandOver")
                        print("Set Mouthmovment | On")
                    else:
                        self.mouthtoggle = False
                        lcd_insidescreen_controll("TM:OFF", "CommandOver")
                        print("Set Mouthmovment | Off")


                elif command_type == "17":
                    next_delay = 2
                    if is_positive_number_string(command_value):
                        print(f"Set VoiceThreshhold: {command_value}")
                        lcd_insidescreen_controll("SVT:" + command_value, "CommandOver")
                        self.voicethreshhold = int(command_value)
                    else:
                        lcd_insidescreen_controll("SVT:ERROR", "CommandOver")
                        print(f"Unknown VoiceThreshold")

                elif command_type == "7":
                    next_delay = 3
                    self.blinkingtoggle = True
                    lcd_insidescreen_controll("TB:ON", "CommandOver")
                    print("Start Blinking")
                elif command_type == "6":
                    next_delay = 5
                    lcd_insidescreen_controll("TB:OFF", "CommandOver")
                    self.blinkingtoggle = False
                    print("Stop Blinking")

                elif command_type == "21":
                    IP = "00:00:00:00"

                    try:
                        # This command grabs the IP address assigned to the Wi-Fi interface
                        IP = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
                        if not IP:
                            IP = "No Connection"
                    except Exception:
                        IP = "Error"


                    lcd_insidescreen_controll(IP, "CommandOver")
                    print(IP)
                elif command_type == "22":
                    self.audiolinkmode = not self.audiolinkmode
                    if self.audiolinkmode:
                        lcd_insidescreen_controll("AD Active", "CommandOver")
                    else:
                        lcd_insidescreen_controll("AD Off", "CommandOver")

                elif command_type == "23":
                    self.audiolinkmaxvoulme = int(command_value)
                    lcd_insidescreen_controll("Set Maxvolume", "CommandOver")




                elif command_type == "19":
                    next_delay = 5
                    if command_value == "1":
                        self.booptoggle = not self.booptoggle
                        if self.booptoggle:
                            lcd_insidescreen_controll("BoopGo", "Boop")
                            print("T-Activate Booping")
                        else:
                            lcd_insidescreen_controll("BoopDisabled", "Boop")
                            print("T-Deactivate Booping")
                    elif command_value == "2":
                        lcd_insidescreen_controll("BoopGo", "Boop")
                        print("Activate Booping")
                        self.booptoggle = True
                    else:
                        lcd_insidescreen_controll("BoopDisabled", "Boop")
                        print("Deactivate Booping")
                        self.booptoggle = False

                else:
                    next_delay = 5
                # update fetch time when queue ends
                if not self.command_queue:
                    self.next_fetch_time = time.time() + next_delay

        # -----------------------------------------------------
        # DO THE FACE/ANIMATION LOAD OUTSIDE THE LOCK (no freezing)
        # -----------------------------------------------------
        if load_new_eye_file:
            self.load_face_component("eyes", load_new_eye_file)

        if load_new_animation_file:
            # load the asset, and the asset loader will activate animation_mode if successful
            self.load_animation_component(load_new_animation_file)

        # fetch outside lock
        if must_fetch:
            self.fetch_data()

        # reschedule
        if not self.stop_event.is_set():
            self.timer = threading.Timer(next_delay, self.process_command)
            self.timer.start()

    # ------------------------------------------------------
    # FETCH DATA
    # ------------------------------------------------------
    def fetch_data(self):
        try:
            r = requests.get(QUEUE_URL, timeout=10)
            r.raise_for_status()
            data = r.json()

            with self.queue_lock:
                self.command_queue.clear()
                self.command_queue.extend(data)

            print(f"Fetched {len(data)} commands.")

        except Exception as e:
            print(f"Fetch error: {e}")
            self.next_fetch_time = time.time() + FETCH_INTERVAL_SECONDS

    # ------------------------------------------------------
    # MAIN MATRIX LOOP
    # ------------------------------------------------------
    def run(self):
        # Start command processing loop
        self.process_command()
        print("Command processor started.")

        canvas = self.matrix.CreateFrameCanvas()

        # Variable to hold the mouth/eye file names to load outside the lock
        mouth_file_to_load = None
        eye_file_to_load = None

        while not self.stop_event.is_set():
            canvas.Clear()  # <-- Ensures a black background every frame
            current_time = time.time()
            eye_file_to_load = None

            with self.queue_lock:
                self.matrix.brightness = self.current_brightness
                r_full, g_full, b_full = hex_to_rgb(self.current_color)

                W = self.matrix.width
                H = self.matrix.height

                # -------------------------
                # 1. ANIMATION MODE
                # -------------------------

                if self.animation_mode_active:

                    # Check if animation is finished (works for all types now)
                    if current_time >= self.animation_end_time:
                        self.animation_mode_active = False
                        # Fall through to default face drawing to ensure final state is shown

                    elapsed = current_time - self.animation_start_time

                    if self.current_animation_type == "4":

                        # --- DVD Logo Animation ---
                        if not self.dvd_grid:
                            # This check should ideally not be hit anymore if activation is delayed
                            print("DVD logo grid not loaded. Stopping animation.")
                            self.animation_mode_active = False
                            continue

                            # Dynamically determine size
                        DVD_LOGO_H = len(self.dvd_grid)
                        DVD_LOGO_W = len(self.dvd_grid[0]) if DVD_LOGO_H > 0 else 0

                        if DVD_LOGO_W == 0 or DVD_LOGO_H == 0:
                            print("DVD logo grid has zero dimensions. Stopping animation.")
                            self.animation_mode_active = False
                            continue

                        # 1. Initialize position on first run of this animation instance
                        if not self.dvd_initialized:

                            # Calculate the maximum safe coordinate for top-left corner
                            # Ensures the logo fits fully inside the screen
                            max_x = W - DVD_LOGO_W
                            max_y = H - DVD_LOGO_H

                            # We must check if the logo fits on the screen at all
                            if max_x < 0 or max_y < 0:
                                print("DVD logo is too large for the screen. Stopping animation.")
                                self.animation_mode_active = False
                                continue

                            # Random start position within safe bounds [0, max_x] and [0, max_y]
                            self.dvd_x = random.randint(0, max_x)
                            self.dvd_y = random.randint(0, max_y)

                            self.dvd_initialized = True
                            self.last_dvd_update = current_time

                        # 2. Update Physics
                        if current_time - self.last_dvd_update >= self.dvd_update_interval:

                            # Move
                            new_x = self.dvd_x + self.dvd_dx
                            new_y = self.dvd_y + self.dvd_dy

                            bounced = False

                            # Boundary check X
                            if new_x < 0:
                                self.dvd_dx = 1
                                self.dvd_x = 0
                                bounced = True
                            elif new_x > W - DVD_LOGO_W:
                                self.dvd_dx = -1
                                self.dvd_x = W - DVD_LOGO_W
                                bounced = True
                            else:
                                self.dvd_x = new_x

                            # Boundary check Y
                            if new_y < 0:
                                self.dvd_dy = 1
                                self.dvd_y = 0
                                bounced = True
                            elif new_y > H - DVD_LOGO_H:
                                self.dvd_dy = -1
                                self.dvd_y = H - DVD_LOGO_H
                                bounced = True
                            else:
                                self.dvd_y = new_y

                            # Change color on bounce
                            if bounced:
                                self.dvd_color_index = (self.dvd_color_index + 1) % len(self.dvd_colors)

                            self.last_dvd_update = current_time

                        # 3. Draw Logo
                        r_dvd, g_dvd, b_dvd = self.dvd_colors[self.dvd_color_index]

                        for y_offset in range(DVD_LOGO_H):  # Row index
                            for x_offset in range(DVD_LOGO_W):  # Column index

                                # Only draw pixel if the grid indicates a pixel (value == 1)
                                if self.dvd_grid[y_offset][x_offset] == 1:

                                    draw_x = self.dvd_x + x_offset
                                    draw_y = self.dvd_y + y_offset

                                    if 0 <= draw_x < W and 0 <= draw_y < H:
                                        canvas.SetPixel(draw_x, draw_y, r_dvd, g_dvd, b_dvd)


                    elif self.current_animation_type == "3":

                        animation_duration = self.animation_end_time - self.animation_start_time
                        if animation_duration > 0:
                            progress = elapsed / animation_duration
                        else:
                            progress = 1.0  # Should not happen, but prevents division by zero

                        current_eyes_grid = self.current_eyes_grid
                        current_mouth_grid = self.current_mouth_grid
                        current_nose_grid = self.current_nose_grid

                        # Phase 1: Wipe In (0.0 <= progress <= 0.5) - Lines move to center (1-pixel thick)
                        if progress <= 0.5:
                            # t ranges from 0 to 1 in this phase
                            t = progress * 2.0

                            # Left line moves from 0 to center_left
                            center_left = W // 2 - 1
                            x_left = int(t * center_left)
                            # Right line moves from W-1 to center_right
                            center_right = W // 2
                            x_right = (W - 1) - int(t * (W - 1 - center_right))

                            # Draw the moving vertical 1-pixel lines (Wipe In)
                            for y in range(H):
                                # Clamp to valid x coordinates
                                if 0 <= x_left < W:
                                    canvas.SetPixel(x_left, y, r_full, g_full, b_full)
                                if 0 <= x_right < W:
                                    canvas.SetPixel(x_right, y, r_full, g_full, b_full)

                        # Phase 2: Wipe Out / Reveal (0.5 < progress < 1.0) - Lines move outwards, revealing face
                        else:
                            t = (progress - 0.5) * 2.0
                            center_left = W // 2 - 1
                            center_right = W // 2

                            x_left = int(center_left * (1.0 - t))
                            x_right = int(center_right + t * (W - 1 - center_right))

                            # 1) Draw the two 1-pixel-thick wipe lines
                            for y in range(H):
                                if 0 <= x_left < W:
                                    canvas.SetPixel(x_left, y, r_full, g_full, b_full)
                                if 0 <= x_right < W:
                                    canvas.SetPixel(x_right, y, r_full, g_full, b_full)

                            # 2) Reveal face components BETWEEN the two lines
                            # We draw Eyes, Mouth, and Nose if they fall within the revealed area

                            # Draw Eyes (with offset if you want them offset during animation)
                            if current_eyes_grid:
                                for r_i, row in enumerate(current_eyes_grid):
                                    for c_i, val in enumerate(row):
                                        draw_x = c_i + self.face_offset_x
                                        draw_y = r_i + self.face_offset_y
                                        if val and x_left < draw_x < x_right:
                                            if 0 <= draw_x < W and 0 <= draw_y < H:
                                                canvas.SetPixel(draw_x, draw_y, r_full, g_full, b_full)

                            # Draw Mouth (stationary)
                            if self.current_mouth_grid:
                                for r_i, row in enumerate(self.current_mouth_grid):
                                    for c_i, val in enumerate(row):
                                        if val and x_left < c_i < x_right:
                                            if 0 <= c_i < W and 0 <= r_i < H:
                                                canvas.SetPixel(c_i, r_i, r_full, g_full, b_full)

                            # Draw Nose (stationary) - ADDED THIS
                            if self.current_nose_grid:
                                for r_i, row in enumerate(self.current_nose_grid):
                                    for c_i, val in enumerate(row):
                                        if val and x_left < c_i < x_right:
                                            if 0 <= c_i < W and 0 <= r_i < H:
                                                canvas.SetPixel(c_i, r_i, r_full, g_full, b_full)
                    else:
                        # other animation types can be implemented here; for unknown types do nothing
                        pass
                # -------------------------
                # 2. TEXT / GRID / FACE MODES (Only run if NO animation is active)
                # -------------------------

                if not self.animation_mode_active:
                    fg = graphics.Color(r_full, g_full, b_full)  # Define color using full RGB

                    # text mode
                    if self.text_mode_active and self.font:
                        text_width = graphics.DrawText(canvas, self.font, 0, 0, fg, self.text_to_display)
                        y = (canvas.height + self.font.height) // 2
                        graphics.DrawText(canvas, self.font, self.scroll_offset, y, fg, self.text_to_display)
                        self.scroll_offset -= self.scroll_speed

                        if self.scroll_offset < -text_width:
                            self.text_mode_active = False

                    # grid mode
                    elif self.grid_mode_active:
                        if time.time() >= self.grid_end_time:
                            self.grid_mode_active = False
                        else:
                            for r_i, row in enumerate(self.custom_grid):
                                for c_i, val in enumerate(row):
                                    if val == 1:
                                        # fixed: provide both x and y to SetPixel
                                        canvas.SetPixel(c_i, r_i, r_full, g_full, b_full)

                    # default face
                    else:

                        # --- BOOP LOGIC (Sticky with Cooldown) ---
                        if self.booptoggle:
                            current_time = time.time()

                            # 1. TRIGGER: Hand detected and we aren't in cooldown
                            if self.sensor_is_currently_booped and current_time > self.boop_lockout_time:
                                if not self.is_booped:
                                    self.is_booped = True
                                    self.pre_boop_eyes = self.current_eyes_name
                                    eye_file_to_load = "Love_Eyes_Blink.json"
                                    lcd_insidescreen_controll("BoopOn", "Boop")

                                # While hand is present, constantly push the end time forward
                                self.boop_active_until = current_time + self.boop_duration

                            # 2. RELEASE: Hand is gone, and the sticky timer has finally run out
                            elif self.is_booped and current_time > self.boop_active_until:
                                self.is_booped = False
                                # Set the lockout starting NOW for the cooldown period
                                self.boop_lockout_time = current_time + self.boop_cooldown
                                eye_file_to_load = self.pre_boop_eyes
                                lcd_insidescreen_controll("BoopOff", "Boop")


                        # --- MOUTH LOGIC ---
                        new_mouth_name = self.current_mouth_name
                        mouth_file_to_load = None  # Reset for this frame

                        if self.mouthtoggle:

                            volume = 0

                            try:

                                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
                                volume = np.linalg.norm(data) / len(data)
                            except Exception as e:
                                print(f"Error Mouth: {e}")

                            micebeforeVolume = self.mouthVolume

                            self.mouthVolume = volume
                            if self.audiolinkmode:
                                # Audiolink Logic
                                CallCulatedBrightniss = 100 / self.audiolinkmaxvoulme * volume

                                if CallCulatedBrightniss > 100:
                                    CallCulatedBrightniss = 100
                                if CallCulatedBrightniss < 20:
                                    CallCulatedBrightniss = 20

                                self.current_brightness = CallCulatedBrightniss

                                StartColor = "#0000ff"
                                HueshiftCOlor = self.current_color
                                HueshiftCOlor = shift_hue(HueshiftCOlor, 0.05)
                                self.current_color = HueshiftCOlor

                                #print(f"Volume: {volume:.4f}")
                                #print(f"Brightness: {self.current_brightness:.4f}")
                                #print(f"Color: {self.current_color}")
                            if volume >= self.voicethreshhold and volume > 0:
                                if not self.audiolinkmode:
                                    lcd_insidescreen_controll("MicON", "Mic")
                                    print(f"Volume: {volume:.4f}")
                            else:
                                self.mouthVolume = 0
                                if micebeforeVolume > 0:
                                    lcd_insidescreen_controll("MicOff", "Mic")

                        if self.mouthtoggle and self.mouthVolume >= self.voicethreshhold:
                            new_mouth_name = self.current_mouth_open_name  # "Mouth_Open.json"
                            self.ismouthopen = True
                        else:
                            new_mouth_name = "Mouth_Close.json"
                            self.ismouthopen = False




                        # Check if the desired mouth file is different from the currently loaded one
                        if self.current_mouth_name != new_mouth_name:
                            mouth_file_to_load = new_mouth_name  # Signal to load outside the lock

                        # --- BLINKING LOGIC ---
                        eyes_grid_to_draw = self.current_eyes_grid

                        if self.blinkingtoggle and self.current_blink_grid:

                            if current_time >= self.blink_end_time and self.is_blinking:
                                # 1. End of a blink, return to normal
                                self.is_blinking = False
                                lcd_insidescreen_controll("BlinkOFF", "Blink")
                                # Schedule the next blink
                                self.next_blink_time = current_time + self._get_random_blink_interval()

                            elif current_time >= self.next_blink_time and not self.is_blinking:
                                # 2. Time for a new blink
                                self.is_blinking = True
                                lcd_insidescreen_controll("BlinkON", "Blink")
                                self.blink_end_time = current_time + BLINK_DURATION

                        # --- DETERMINE WHICH GRID TO DRAW ---
                        if self.is_blinking:
                            eyes_grid_to_draw = self.current_blink_grid

                        # --- DRAW THE SELECTED FACE ---
                        # 1. Draw Eyes (ONLY these use the offset)
                        if eyes_grid_to_draw:
                            for r_i, row in enumerate(eyes_grid_to_draw):
                                for c_i, val in enumerate(row):
                                    if val:
                                        draw_x = c_i + self.face_offset_x
                                        draw_y = r_i + self.face_offset_y
                                        if 0 <= draw_x < W and 0 <= draw_y < H:
                                            canvas.SetPixel(draw_x, draw_y, r_full, g_full, b_full)

                        # 2. Draw Mouth (Stationary)
                        if self.current_mouth_grid:
                            for r_i, row in enumerate(self.current_mouth_grid):
                                for c_i, val in enumerate(row):
                                    if val:
                                        if 0 <= c_i < W and 0 <= r_i < H:
                                            canvas.SetPixel(c_i, r_i, r_full, g_full, b_full)

                        # 3. Draw Nose (Stationary)
                        if self.current_nose_grid:
                            for r_i, row in enumerate(self.current_nose_grid):
                                for c_i, val in enumerate(row):
                                    if val:
                                        if 0 <= c_i < W and 0 <= r_i < H:
                                            canvas.SetPixel(c_i, r_i, r_full, g_full, b_full)

                        else:
                            canvas.Fill(r_full, g_full, b_full)

            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.025)

            # -----------------------------------------------------
            # DO THE MOUTH/EYE LOAD OUTSIDE THE LOCK
            # -----------------------------------------------------
            if eye_file_to_load:
                self.load_face_component("eyes", eye_file_to_load)

            if mouth_file_to_load:
                self.load_face_component("mouth", mouth_file_to_load)

            # --- RANDOM FACE SHIFT ---
            # Only shift occasionally to look like natural micro-movements

            # 1. Occasionally pick a new target (keep this inside the while loop)
            if random.random() < 0.1:  # Lower frequency so they "linger" at a look point
                self.target_offset_x = random.choice([-2, -1, 0, 1, 2])
                self.target_offset_y = random.choice([-1, 0, 1])  # Eyes usually move less vertically

            # 2. Smoothly slide toward target (Linear Interpolation)
            # Run this every frame regardless of the random check
            dx = self.target_offset_x - self.current_offset_x
            dy = self.target_offset_y - self.current_offset_y

            self.current_offset_x += dx * self.lerp_speed
            self.current_offset_y += dy * self.lerp_speed

            # 3. For the actual SetPixel calls, use the rounded integer versions
            self.face_offset_x = int(round(self.current_offset_x))
            self.face_offset_y = int(round(self.current_offset_y))

    def __del__(self):
        self.stop_event.set()
        if self.timer:
            self.timer.cancel()

    def load_saved_eyes_name(self):
        """Tries to load the last eye name from disk, defaults to U_Eyes."""
        default_eye = "U_Eyes.json"
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Check if data is actually a dictionary before calling .get()
                    if isinstance(data, dict):
                        return data.get("last_eyes", default_eye)
                    else:
                        print("State file format invalid, resetting to default.")
        except Exception as e:
            print(f"Error loading state: {e}")
        return default_eye

    def save_eyes_name(self, name):
        """Saves the current eye name to disk and ensures file permissions."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({"last_eyes": name}, f)

            # This fixes the [Errno 13] for future runs
            # by making the file readable/writable by everyone
            os.chmod(self.state_file, 0o666)
        except Exception as e:
            print(f"Error saving state: {e}")

    def send_bluetooth_message(self, message: str):
        """
        Sends a string to the connected Bluetooth device.
        Includes safety checks for port existence and write stability.
        """
        # 1. Check if the device is even plugged in/bound
        if not os.path.exists(BT_SERIAL_PORT):
            # We don't print here to avoid flooding the console during every frame
            return False

        try:
            # 2. Open with a short timeout so we don't hang the main loop
            with serial.Serial(BT_SERIAL_PORT, BT_BAUD_RATE, timeout=0.5) as ser:
                if ser.is_open:
                    # 3. Ensure the message ends with a newline (standard for serial)
                    if not message.endswith('\n'):
                        message += '\n'

                    # 4. Write data encoded as UTF-8
                    ser.write(message.encode('utf-8'))
                    ser.flush()  # Force the buffer to empty
                    return True
        except (serial.SerialException, OSError) as e:
            # This catches "Device not configured" or "Permission denied"
            print(f"BT Send Failed: {e}")
        except Exception as e:
            print(f"Unexpected BT Error: {e}")

        return False


# MAIN
if __name__ == "__main__":
    app = MyMatrixApp()
    try:
        if not app.process():
            app.print_help()
    except Exception as e:
        print("FATAL ERROR:")
        traceback.print_exc()
    finally:
        app.__del__()