# SPDX-FileCopyrightText: Copyright (c) 2024 Bradley Robert Carlile
#
# SPDX-License-Identifier: MIT

import time
from machine import Pin, I2C
from micropython_bmp58x import bmp58x

#i2c = I2C(1, sda=Pin(2), scl=Pin(3))  # Correct I2C pins for RP2040
i2c = I2C(id=1, scl=Pin(27), sda=Pin(26), freq=400_000)

i2c1_devices = i2c.scan()
if i2c1_devices:
    for d in i2c1_devices: print(f"i2c1 device at address: {hex(d)}")
else:
    print("ERROR: No i2c1 devices")
    
bmp = bmp58x.BMP581(i2c=i2c, address=0x47)

sea_level_pressure = bmp.sea_level_pressure
print(f"initial sea_level_pressure = {sea_level_pressure:.2f} hPa\n")

bmp.sea_level_pressure = 1007.10

# Highest resolution for bmp585 & bmp581
bmp.pressure_oversample_rate = bmp.OSR128
bmp.temperature_oversample_rate = bmp.OSR8

print(f"Oversample rate setting: \n{bmp.pressure_oversample_rate=}\n{bmp.temperature_oversample_rate=}\n")

while True:
    print(f"Pressure = {bmp.pressure:.2f} hPa")
    temp = bmp.temperature
    print(f"temp = {temp:.2f} C")
  
    # meters based on sea level pressure of 1013.25 hPA
    meters = bmp.altitude
    print(f"alt = {meters:.2f} meters")
    feet = meters * 3.28084
    feet_only = int(feet)
    inches = (feet - feet_only) * 12
    print(f"alt = {feet_only} feet {inches:.1f} inches")

        
    # altitude in meters based on initial sea level pressure of 1013.25 hPA
    sea_level_pressure = bmp.sea_level_pressure
    print(f"sea level pressure = {sea_level_pressure:.2f} hPa\n")

    time.sleep(2.5)

# while True:
#     for iir_coefficient in bmp.iir_coefficient_values:
#         print(f"Current IIR Coefficient setting: {bmp.iir_coefficient}")
#         for _ in range(10):
#             print(f"Pressure: {bmp.pressure:.2f} hPa")
#             print()
#             time.sleep(0.5)
#         bmp.iir_coefficient = iir_coefficient

 
 