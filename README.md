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

## The Face format

The system loads the face in three parts. Eyes, Mouth, and Nose.
It does this so it can modify each individually without the need of making multiple faces.
(For example, for blinking or speaking)

The parts are stored in a JSON format. I made a simple web editor. For this.
https://magictwin.net/proto/FaceMaker



## Hardware Setup

The project relies on the following I2C addresses and connections:

* **RGB Matrix**: Connected via standard GPIO (Hzeller driver).
* **16x02 LCD**: I2C Address 0x27.
* **VL53L0X Sensor**: I2C Address 0x29.
* **USB Microphone**: Automatically detected by name.

---

## Installation

   git clone [https://github.com/magictwinsworld/ToasterBrain.git](https://github.com/magictwinsworld/ToasterBrain.git)
   cd ToasterBrain

   sudo raspi-config nonint do_i2c 0
   sudo raspi-config nonint do_serial_hw 0

   sudo apt-get update
   sudo apt-get install -y git python3-dev python3-pip python3-numpy \
   libasound2-dev libjack-jackd2-dev portaudio19-dev \
   libgraphicsmagick++-dev libwebp-dev htop

   git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
   cd rpi-rgb-led-matrix

   Build the core library
   make -C lib

   Build and install Python bindings
   cd bindings/python
   make install
   sudo python3 setup.py install
   cd ../../../

   sudo pip3 install requests smbus2 pyserial pyaudio numpy --break-system-packages

   Edit the bluetooth service to run in compatibility mode
   sudo sed -i 's|^ExecStart=.*|ExecStart=/usr/lib/bluetooth/bluetoothd -C|' /lib/systemd/system/bluetooth.service
   sudo systemctl daemon-reload
   sudo systemctl restart bluetooth

   Set up the Serial Port Profile (run this or add to rc.local)
   sudo sdptool add SP

   sudo usermod -a -G audio $USER
   sudo python3 my_app.py --led-rows=32 --led-cols=64 --led-slowdown-gpio=4


   sudo python3 ProtoBrain/mainscrypt/ProtoBrain.py --led-rows=32 --led-cols=128 --led-slowdown-gpio=3 --led-chain=1 --led-gpio-mapping=adafruit-hat
