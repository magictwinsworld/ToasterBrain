# ToasterBrain

ToasterBrain is a Python-based control system for Raspberry Pi-powered protogen fursuit. It features a reactive facial system with eyes, mouth, and nose components, real-time audio reactivity, I2C secondary displays, and remote command execution via Bluetooth and Web APIs.

This system uses this libary.
https://github.com/hzeller/rpi-rgb-led-matrix

Heavely inspired by the WafflesDoesArt series
https://www.youtube.com/playlist?list=PLguU2gUSfI7ns94YH2fXrQyaipfVsL3ai
---

## Features

* **Dynamic Facial Expressions**: Modular loading of JSON-based grid files for eyes, mouths, and noses.
* **Audio Reactivity**: 
    * **Lip Sync**: Real-time mouth movement based on microphone input.
    * **AudioLink**: Reactive brightness and hue shifting synced to volume levels.
* **Hardware Integration**:
    * **RGB LED Matrix**: Primary facial display (supports various sizes via samplebase).
    * **I2C LCD (16x02)**: Secondary "Internal Screen" for status monitoring and debugging.
    * **VL53L0X ToF Sensor**: Supports "Boop" detection—touching the nose triggers "Love Eyes."
* **Connectivity**: 
    * **Bluetooth Serial**: Remote control via mobile app or serial terminal.
    * **Web Queue**: Synchronized command polling from a remote API.

---

## Hardware Setup

The project relies on the following I2C addresses and connections:

* **RGB Matrix**: Connected via standard GPIO (Hzeller driver).
* **16x02 LCD**: I2C Address 0x27.
* **VL53L0X Sensor**: I2C Address 0x29.
* **USB Microphone**: Automatically detected by name.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/magictwinsworld/ToasterBrain.git](https://github.com/magictwinsworld/ToasterBrain.git)
   cd ToasterBrain
