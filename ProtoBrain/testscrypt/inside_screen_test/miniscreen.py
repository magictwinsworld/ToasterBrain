#!/usr/bin/env python3
import smbus2
import time

I2C_ADDR = 0x27  # your LCD address
LCD_WIDTH = 16   # max characters per line
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0

LCD_BACKLIGHT = 0x08
ENABLE = 0b00000100

bus = smbus2.SMBus(1)

def lcd_toggle_enable(bits):
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_byte(bits, mode):
    high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    low  = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT
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
        lcd_byte(ord(char), LCD_CHR)

lcd_init()
lcd_message("Hello World!", LCD_LINE_1)
lcd_message("LCD OK @ 0x27", LCD_LINE_2)

time.sleep(5)
lcd_message(" ", LCD_LINE_1)
lcd_message(" ", LCD_LINE_2)
