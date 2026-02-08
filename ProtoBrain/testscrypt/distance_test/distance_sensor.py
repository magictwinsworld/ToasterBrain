#!/usr/bin/env python3

import time
import smbus2

# I2C address of the VL53L0X
ADDR = 0x29

bus = smbus2.SMBus(1)

def write_reg(address, value):
    bus.write_byte_data(ADDR, address, value)

def read_reg(address):
    return bus.read_byte_data(ADDR, address)

def read_range():
    # Trigger a ranging measurement
    write_reg(0x00, 0x01)
    time.sleep(0.05)

    # High and low bytes of the distance
    hi = read_reg(0x1E)
    lo = read_reg(0x1F)
    return (hi << 8) | lo

def main():
    print("VL53L0X starting (smbus mode)...")
    while True:
        try:
            distance = read_range()

            if distance != 20 and distance <= 500:
                print(f"Distance: {distance} mm")
            time.sleep(0.2)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print("Error:", e)
            time.sleep(0.5)

if __name__ == "__main__":
    main()
