# SPDX-FileCopyrightText: Copyright (c) 2024 Bradley Robert Carlile
#
# SPDX-License-Identifier: MIT
# MIT License
# 
# Copyright (c) 2024 Bradley Robert Carlile
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

"""
`bmpxxx`
================================================================================

MicroPython Driver for the Bosch BMP585, BMP581, BMP390, BMP280 pressure sensors

* Author: Brad Carlile

Based on

* micropython-bmp581/bmp581py. Author(s): Jose D. Montoya

"""
import time
from micropython import const
from micropython_bmpxxx.i2c_helpers import CBits, RegisterStruct

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/bradcar/MicroPython_BMP58x.git"


WORLD_AVERAGE_SEA_LEVEL_PRESSURE = 1013.25  # International average standard

class BMP581:
    """Driver for the BMP585 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the BMP581 is connected to.
    :param int address: The I2C device address. Default :const:`0x47`, Secondary :const:`0x46`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`BMP581` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_bmp58x import bmp58x

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        bmp = bmp58x.BMP581(i2c)

    Now you have access to the attributes

    .. code-block:: python

        press = bmp.pressure
        temp = bmp.temperature

        # altitude in meters based on sea level pressure of 1013.25 hPA
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # set sea level pressure to a known sea level pressure in hPa at nearest airport
        # https://www.weather.gov/wrh/timeseries?site=KPDX
        bmp.sea_level_pressure = 1010.80
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # Highest resolution for bmp581
        bmp.pressure_oversample_rate = bmp.OSR128
        bmp.temperature_oversample_rate = bmp.OSR8
        meters = bmp.altitude

    """

    # Power Modes for BMP581
    # in the BMP390 there is only SLEEP(aka STANDBY), FORCED, NORMAL
    STANDBY = const(0x00)
    NORMAL = const(0x01)
    FORCED = const(0x02)
    NON_STOP = const(0x03)
    power_mode_values = (STANDBY, NORMAL, FORCED, NON_STOP)

    # Oversample Rate
    OSR1 = const(0x00)
    OSR2 = const(0x01)
    OSR4 = const(0x02)
    OSR8 = const(0x03)
    OSR16 = const(0x04)
    OSR32 = const(0x05)
    OSR64 = const(0x06)
    OSR128 = const(0x07)

    # oversampling rates
    pressure_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16, OSR32, OSR64, OSR128)
    temperature_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16, OSR32, OSR64, OSR128)

    # IIR Filters Coefficients
    COEF_0 = const(0x00)
    COEF_1 = const(0x01)
    COEF_3 = const(0x02)
    COEF_7 = const(0x03)
    COEF_15 = const(0x04)
    COEF_31 = const(0x05)
    COEF_63 = const(0x06)
    COEF_127 = const(0x07)
    iir_coefficient_values = (COEF_0, COEF_1, COEF_3, COEF_7, COEF_15, COEF_31, COEF_63, COEF_127)
    
    BMP581_I2C_ADDRESS_DEFAULT = 0x47
    BMP581_I2C_ADDRESS_SECONDARY = 0x46

    _REG_WHOAMI = const(0x01)
    _INT_STATUS = const(0x27)
    _DSP_CONFIG = const(0x30)
    _DSP_IIR = const(0x31)
    _OSR_CONF = const(0x36)
    _ODR_CONFIG = const(0x37)

    _device_id = RegisterStruct(_REG_WHOAMI, "B")
    _drdy_status = CBits(1, _INT_STATUS, 0)
    _power_mode = CBits(2, _ODR_CONFIG, 0)
    _temperature_oversample_rate = CBits(3, _OSR_CONF, 0)
    _pressure_oversample_rate = CBits(3, _OSR_CONF, 3)
    _output_data_rate = CBits(5, _ODR_CONFIG, 2)
    _pressure_enabled = CBits(1, _OSR_CONF, 6)
    _iir_coefficient = CBits(3, _DSP_IIR, 3)       # Pressure IIR coefficient
    _iir_temp_coefficient = CBits(3, _DSP_IIR, 0)  # Temp IIR coefficient
    _iir_control = CBits(8, _DSP_CONFIG, 0)
    _temperature = CBits(24, 0x1D, 0, 3)
    _pressure = CBits(24, 0x20, 0, 3)

    def __init__(self, i2c, address: int = None) -> None:
        time.sleep_ms(3)    # t_powup 2ms
        # If no address is provided, try the default, then secondary
        if address is None:
            if self._check_address(i2c, self.BMP581_I2C_ADDRESS_DEFAULT):
                address = self.BMP581_I2C_ADDRESS_DEFAULT
            elif self._check_address(i2c, self.BMP581_I2C_ADDRESS_SECONDARY):
                address = self.BMP581_I2C_ADDRESS_SECONDARY
            else:
                raise RuntimeError("BMP581 sensor not found at I2C expected address (0x47,0x46).")
        else:
        # Check if the specified address is valid
            if not self._check_address(i2c, address):
                raise RuntimeError("BMP581 sensor not found at I2C expected address (0x47,0x46).")

        self._i2c = i2c
        self._address = address
        if self._read_device_id() != 0x50:  #check _device_id after i2c established
            raise RuntimeError("Failed to find the BMP581 sensor")
        
        # Must be in STANDBY to initialize _iir_coefficient    
        self._power_mode = STANDBY
        time.sleep_ms(5)   # mode change takes 4ms
        self._iir_coefficient = COEF_0
        self._iir_temp_coefficient = COEF_0
        self._power_mode = NORMAL
        time.sleep_ms(5)   # mode change takes 4ms
        self._pressure_enabled = True
        self.sea_level_pressure = WORLD_AVERAGE_SEA_LEVEL_PRESSURE

    def _check_address(self, i2c, address: int) -> bool:
        """Helper function to check if a device responds at the given I2C address."""
        try:
            i2c.writeto(address, b"")  # Attempt a write operation
            return True
        except OSError:
            return False

    def _read_device_id(self) -> int:
        return self._device_id

    @property
    def config(self):
        print(f"{hex(self._address)=}")
        print(f"{hex(self._device_id)=}")
        print(f"{self.power_mode=}")
        print(f"{self.pressure_oversample_rate=}")
        print(f"{self.temperature_oversample_rate=}")
        print(f"{self.iir_coefficient=}")
        print(f"{self.sea_level_pressure=}")
        print(f"{self.pressure=} hPa")      
        print(f"{self.temperature=} C")
        print(f"{self.altitude=} m\n")

    @property
    def power_mode(self) -> str:
        """
        Sensor power_mode
        +-----------------------------+------------------+
        | Mode                        | Value            |
        +=============================+==================+
        | :py:const:`bmp581.STANDBY`  | :py:const:`0x00` |
        | :py:const:`bmp581.NORMAL`   | :py:const:`0x01` |
        | :py:const:`bmp581.FORCED`   | :py:const:`0x02` |
        | :py:const:`bmp581.NON_STOP` | :py:const:`0X03` |
        +-----------------------------+------------------+
        """
        values = ("STANDBY","NORMAL","FORCED","NON_STOP",)
        return values[self._power_mode]

    @power_mode.setter
    def power_mode(self, value: int) -> None:
        debug = False
        if debug:
            print(f"{self.power_mode_values}")
            print(f"power mode: {value=}")
        if value not in self.power_mode_values:
            raise ValueError("Value must be a valid power_mode setting: STANDBY,NORMAL,FORCED,NON_STOP")
        self._power_mode = value

    @property
    def pressure_oversample_rate(self) -> str:
        """
        Sensor pressure_oversample_rate
        Oversampling extends the measurement time per measurement by the oversampling
        factor. Higher oversampling factors offer decreased noise at the cost of
        higher power consumption.
        +---------------------------+------------------+
        | Mode                      | Value            |
        +===========================+==================+
        | :py:const:`bmp58x.OSR1`   | :py:const:`0x00` |
        | :py:const:`bmp58x.OSR2`   | :py:const:`0x01` |
        | :py:const:`bmp58x.OSR4`   | :py:const:`0x02` |
        | :py:const:`bmp58x.OSR8`   | :py:const:`0x03` |
        | :py:const:`bmp58x.OSR16`  | :py:const:`0x04` |
        | :py:const:`bmp58x.OSR32`  | :py:const:`0x05` |
        | :py:const:`bmp58x.OSR64`  | :py:const:`0x06` |
        | :py:const:`bmp58x.OSR128` | :py:const:`0x07` |
        +---------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("OSR1", "OSR2", "OSR4", "OSR8", "OSR16", "OSR32", "OSR64", "OSR128",)
        return string_name[self._pressure_oversample_rate]

    @pressure_oversample_rate.setter
    def pressure_oversample_rate(self, value: int) -> None:
        if value not in self.pressure_oversample_rate_values:
            raise ValueError(
                "Value must be a valid pressure_oversample_rate: OSR1,OSR2,OSR4,OSR8,OSR16,OSR32,OSR64,OSR128")
        self._pressure_oversample_rate = value

    @property
    def temperature_oversample_rate(self) -> str:
        """
        Sensor temperature_oversample_rate
        +---------------------------+------------------+
        | Mode                      | Value            |
        +===========================+==================+
        | :py:const:`bmp58x.OSR1`   | :py:const:`0x00` |
        | :py:const:`bmp58x.OSR2`   | :py:const:`0x01` |
        | :py:const:`bmp58x.OSR4`   | :py:const:`0x02` |
        | :py:const:`bmp58x.OSR8`   | :py:const:`0x03` |
        | :py:const:`bmp58x.OSR16`  | :py:const:`0x04` |
        | :py:const:`bmp58x.OSR32`  | :py:const:`0x05` |
        | :py:const:`bmp58x.OSR64`  | :py:const:`0x06` |
        | :py:const:`bmp58x.OSR128` | :py:const:`0x07` |
        +---------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("OSR1", "OSR2", "OSR4", "OSR8", "OSR16", "OSR32", "OSR64", "OSR128",)
        return string_name[self._temperature_oversample_rate]

    @temperature_oversample_rate.setter
    def temperature_oversample_rate(self, value: int) -> None:
        if value not in self.temperature_oversample_rate_values:
            raise ValueError(
                "Value must be a valid temperature_oversample_rate: OSR1,OSR2,OSR4,OSR8,OSR16,OSR32,OSR64,OSR128")
        self._temperature_oversample_rate = value
        
    @property
    def temperature(self) -> float:
        """
        The temperature sensor in Celsius
        :return: Temperature in Celsius
        """
        raw_temp = self._temperature
        return self._twos_comp(raw_temp, 24) / 65536.0

    @property
    def pressure(self) -> float:
        """
        The sensor pressure in hPa
        :return: Pressure in hPa
        """
        raw_pressure = self._pressure
        return self._twos_comp(raw_pressure, 24) / 64.0 / 100.0

    @property
    def altitude(self) -> float:
        """
        Using the sensor's measured pressure and the pressure at sea level (e.g., 1013.25 hPa),
        the altitude in meters is calculated with the international barometric formula
        https://ncar.github.io/aircraft_ProcessingAlgorithms/www/PressureAltitude.pdf
        """
        altitude = 44330.77 * (
                1.0 - ((self.pressure / self.sea_level_pressure) ** 0.1902632)
        )
        return altitude

    @altitude.setter
    def altitude(self, value: float) -> None:
        self.sea_level_pressure = self.pressure / (1.0 - value / 44330.77) ** (1/0.1902632)

    @property
    def sea_level_pressure(self) -> float:
        """
        Returns the current sea-level pressure set for the sensor in hPa.
        :return: Sea-level pressure in hPa
        """
        return self._sea_level_pressure

    @sea_level_pressure.setter
    def sea_level_pressure(self, value: float) -> None:
        self._sea_level_pressure = value

    @staticmethod
    def _twos_comp(val: int, bits: int) -> int:
        if val & (1 << (bits - 1)) != 0:
            return val - (1 << bits)
        return val

    @property
    def iir_coefficient(self) -> str:
        """
        Sensor iir_coefficient
        +----------------------------+------------------+
        | Mode                       | Value            |
        +============================+==================+
        | :py:const:`bmp58x.COEF_0`  | :py:const:`0x00` |
        | :py:const:`bmp58x.COEF_1`  | :py:const:`0x01` |
        | :py:const:`bmp58x.COEF_3`  | :py:const:`0x02` |
        | :py:const:`bmp58x.COEF_7`  | :py:const:`0x03` |
        | :py:const:`bmp58x.COEF_15` | :py:const:`0x04` |
        | :py:const:`bmp58x.COEF_31` | :py:const:`0x05` |
        | :py:const:`bmp58x.COEF_63` | :py:const:`0x06` |
        | :py:const:`bmp58x.COEF_127`| :py:const:`0x07` |
        +----------------------------+------------------+
        :return: coefficients as string
        """
        values = ("COEF_0", "COEF_1", "COEF_3", "COEF_7", "COEF_15", "COEF_31", "COEF_63", "COEF_127",)
        return values[self._iir_coefficient]

    @iir_coefficient.setter
    def iir_coefficient(self, value: int) -> None:
        debug = False
        if value not in self.iir_coefficient_values:
            raise ValueError("Value must be a valid iir_coefficients: COEF_0,COEF_1,COEF_3,COEF_7,COEF_15,COEF_31,COEF_63,COEF_127")

        # Ensure the sensor is in STANDBY mode before updating
        original_mode = self._power_mode  # Save the current mode
        if debug:
            print(f"{type(original_mode)=}")
            print(f"{original_mode=}")
        if original_mode != STANDBY:
            self.power_mode = STANDBY  # Set to STANDBY if not already
        if debug:
            print(f"updated power mode = {self.power_mode=}")
            print(f"IIR value: {value=}")
        self._iir_coefficient = value
        self._iir_temp_coefficient = value

        # Restore the original power mode
        self.power_mode = original_mode

    @property
    def output_data_rate(self) -> int:
        """
        Sensor output_data_rate. for a complete list of values please see the datasheet
        """
        return self._output_data_rate

    @output_data_rate.setter
    def output_data_rate(self, value: int) -> None:
        if value not in range(0, 32, 1):
            raise ValueError("Value must be a valid output_data_rate setting: 0 to 32")
        self._output_data_rate = value


class BMP585(BMP581):
    """Driver for the BMP585 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the BMP585 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x47`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`BMP585` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_bmp58x import bmp58x

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        bmp = bmp58x.BMP585(i2c)

    Now you have access to the attributes

    .. code-block:: python

        press = bmp.pressure
        temp = bmp.temperature

        # altitude in meters based on sea level pressure of 1013.25 hPA
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # set sea level pressure to a known sea level pressure in hPa at nearest airport
        # https://www.weather.gov/wrh/timeseries?site=KPDX
        bmp.sea_level_pressure = 1010.80
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # Highest resolution for bmp585
        bmp.pressure_oversample_rate = bmp.OSR128
        bmp.temperature_oversample_rate = bmp.OSR8
        meters = bmp.altitude
    """
    BMP585_I2C_ADDRESS_DEFAULT = 0x47
    BMP585_I2C_ADDRESS_SECONDARY = 0x46

    def __init__(self, i2c, address: int = None) -> None:
        time.sleep_ms(3)   # t_powup 2ms
        # If no address is provided, try the default, then secondary
        if address is None:
            if self._check_address(i2c, self.BMP585_I2C_ADDRESS_DEFAULT):
                address = self.BMP585_I2C_ADDRESS_DEFAULT
            elif self._check_address(i2c, self.BMP585_I2C_ADDRESS_SECONDARY):
                address = self.BMP585_I2C_ADDRESS_SECONDARY
            else:
                raise RuntimeError("BMP585 sensor not found at I2C expected address (0x47,0x46).")
        else:
        # Check if the specified address is valid
            if not self._check_address(i2c, address):
                raise RuntimeError("BMP585 sensor not found at I2C expected address (0x47,0x46).")
  
        self._i2c = i2c
        self._address = address
        if self._read_device_id() != 0x51:  # check _device_id after i2c established
            raise RuntimeError("Failed to find the BMP585 sensor")
        
        # Must be in STANDBY to initialize _iir_coefficient    
        self._power_mode = STANDBY
        time.sleep_ms(5)   # mode change takes 4ms
        self._iir_coefficient = COEF_0
        self._iir_temp_coefficient = COEF_0
        self._power_mode = NORMAL
        time.sleep_ms(5)   # mode change takes 4ms
 
#         self._write_reg(0x18, 0x01)  # Enable data ready interrupts
#         val = self._read_reg(0x27, 1)[0]  # Read Interrupt Status Register
#         drdy_data_reg = (val & 0x01) != 0  # Check Data Ready bit
# 
#         print(f"{drdy_data_reg=}")
        self._pressure_enabled = True
        self.sea_level_pressure = WORLD_AVERAGE_SEA_LEVEL_PRESSURE

        
    def _read_device_id(self) -> int:
        return self._device_id


class BMP390(BMP581):
    """Driver for the BMP390 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the BMP390 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x7F`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`BMP390` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_bmp58x import bmp58x

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        bmp = bmp58x.BMP390(i2c)

    Now you have access to the attributes

    .. code-block:: python

        press = bmp.pressure
        temp = bmp.temperature

        # altitude in meters based on sea level pressure of 1013.25 hPA
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # set sea level pressure to a known sea level pressure in hPa at nearest airport
        # https://www.weather.gov/wrh/timeseries?site=KPDX
        bmp.sea_level_pressure = 1010.80
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # Highest resolution for bmp390
        bmp.pressure_oversample_rate = bmp.OSR32
        bmp.temperature_oversample_rate = bmp.OSR2
        bmp.iir_coefficient = bmp.COEF_3
        meters = bmp.altitude

    """
    # Power Modes for BMP390
    power_mode_values = (STANDBY, FORCED, NORMAL)

    # oversampling rates
    pressure_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16, OSR32)
    temperature_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16, OSR32)
    
    BMP390_I2C_ADDRESS_DEFAULT = 0x7f
    BMP390_I2C_ADDRESS_SECONDARY = 0x7e

    ###  BMP390 Constants - notice very different than bmp581
    _REG_WHOAMI_BMP390 = const(0x00)
    _CONFIG_BMP390 = const(0x1f)
    _ODR_CONFIG_BMP390 = const(0x1d)
    _OSR_CONF_BMP390 = const(0x1c)
    _PWR_CTRL_BMP390 = const(0x1b)
    _TEMP_DATA_BMP390 = const(0x07)
    _PRESS_DATA_BMP390 = const(0x04)

    _device_id = RegisterStruct(_REG_WHOAMI_BMP390, "B")

    _power_mode = CBits(2, _PWR_CTRL_BMP390, 4)
    _temperature_oversample_rate = CBits(3, _OSR_CONF_BMP390, 3)
    _pressure_oversample_rate = CBits(3, _OSR_CONF_BMP390, 0)
    _iir_coefficient = CBits(3, _CONFIG_BMP390, 1)
    _output_data_rate = CBits(5, _ODR_CONFIG_BMP390, 0)
    _pressure_enabled = CBits(1, _PWR_CTRL_BMP390, 0)

    _temperature = CBits(24, _TEMP_DATA_BMP390, 0, 3)
    _pressure = CBits(24, _PRESS_DATA_BMP390, 0, 3)

    _par_t1_msb = CBits(8, 0x32, 0)  # Most significant byte of par_t1
    _par_t1_lsb = CBits(8, 0x31, 0)  # Least significant byte of par_t1
    _par_t2_msb = CBits(8, 0x34, 0)  # Most significant byte of par_t2
    _par_t2_lsb = CBits(8, 0x33, 0)  # Least significant byte of par_t2
    _par_t3 = CBits(8, 0x35, 0)  # Only byte for par_t3

    _par_p1_msb = CBits(8, 0x37, 0)  # Most significant byte of par_p1
    _par_p1_lsb = CBits(8, 0x36, 0)  # Least significant byte of par_p1
    _par_p2_msb = CBits(8, 0x39, 0)  # Most significant byte of par_p2
    _par_p2_lsb = CBits(8, 0x38, 0)  # Least significant byte of par_p2
    _par_p3 = CBits(8, 0x3A, 0)  # Only byte for par_p3
    _par_p4 = CBits(8, 0x3B, 0)  # Only byte for par_p4
    _par_p5_msb = CBits(8, 0x3D, 0)  # Most significant byte of par_p5
    _par_p5_lsb = CBits(8, 0x3C, 0)  # Least significant byte of par_p5
    _par_p6_msb = CBits(8, 0x3F, 0)  # Most significant byte of par_p6
    _par_p6_lsb = CBits(8, 0x3E, 0)  # Least significant byte of par_p6
    _par_p7 = CBits(8, 0x40, 0)  # Only byte for par_p7
    _par_p8 = CBits(8, 0x41, 0)  # Only byte for par_p8
    _par_p9_msb = CBits(8, 0x43, 0)  # Most significant byte of par_p9
    _par_p9_lsb = CBits(8, 0x42, 0)  # Least significant byte of par_p9
    _par_p10 = CBits(8, 0x44, 0)  # Only byte for par_p10
    _par_p11 = CBits(8, 0x45, 0)  # Only byte for par_p11

    def __init__(self, i2c, address: int = None) -> None:
        time.sleep_ms(3)        # t_powup 2ms
        # If no address is provided, try the default, then secondary
        if address is None:
            if self._check_address(i2c, self.BMP390_I2C_ADDRESS_DEFAULT):
                address = self.BMP390_I2C_ADDRESS_DEFAULT
            elif self._check_address(i2c, self.BMP390_I2C_ADDRESS_SECONDARY):
                address = self.BMP390_I2C_ADDRESS_SECONDARY
            else:
                raise RuntimeError("BMP390 sensor not found at I2C expected address (0x7f,0x7e).")    
        else:
        # Check if the specified address is valid
            if not self._check_address(i2c, address):
                raise RuntimeError(f"BMP390 sensor not found at specified I2C address (0x{address:02x}).")
    
        self._i2c = i2c
        self._address = address
        if self._read_device_id() != 0x60:  # check _device_id after i2c established
            raise RuntimeError("Failed to find the BMP390 sensor with id=0x60")
        self._power_mode = NORMAL
        time.sleep_ms(4)   # mode change takes 3ms      
        self._pressure_enabled = True
        self.sea_level_pressure = WORLD_AVERAGE_SEA_LEVEL_PRESSURE
        
    @property
    def par_t1(self) -> int:
        """Combine _par_t1_msb and _par_t1_lsb into a unsigned 16-bit integer."""
        msb_value = self._par_t1_msb  # Reads CBits value
        lsb_value = self._par_t1_lsb  # Reads CBits value
        return ((msb_value << 8) | lsb_value) & 0xFFFF

    @property
    def par_t2(self) -> int:
        """Combine _par_t2_msb and _par_t2_lsb into a unsigned 16-bit integer."""
        msb_value = self._par_t2_msb  # Reads CBits value
        lsb_value = self._par_t2_lsb  # Reads CBits value
        return ((msb_value << 8) | lsb_value) & 0xFFFF

    @property
    def par_t3(self) -> int:
        """Read the single-byte _par_t3 signed 8-bit value."""
        return self._par_t3 if self._par_t3 <= 127 else self._par_t3 - 256

    @property
    def par_p1(self) -> int:
        """Combine _par_p1_msb and _par_p1_lsb into a signed 16-bit integer."""
        msb_value = self._par_p1_msb  # Reads CBits value
        lsb_value = self._par_p1_lsb  # Reads CBits value
        combined_value = (msb_value << 8) | lsb_value

        # Convert to signed 16-bit value (two's complement)
        if combined_value >= 0x8000:  # If the value is greater than or equal to 32768
            return combined_value - 0x10000  # Convert to signed by subtracting 65536
        return combined_value

    @property
    def par_p2(self) -> int:
        """Combine _par_p2_msb and _p_par_tp_lsb into a signed 16-bit integer."""
        msb_value = self._par_p2_msb  # Reads CBits value
        lsb_value = self._par_p2_lsb  # Reads CBits value
        combined_value = (msb_value << 8) | lsb_value
        # Convert to signed 16-bit value (two's complement)
        if combined_value >= 0x8000:  # If the value is greater than or equal to 32768
            return combined_value - 0x10000  # Convert to signed by subtracting 65536
        return combined_value

    @property
    def par_p3(self) -> int:
        """Read the single-byte _par_p3 signed 8-bit value."""
        return self._par_p3 if self._par_p3 <= 127 else self._par_p3 - 256

    @property
    def par_p4(self) -> int:
        """Read the single-byte _par_p4 signed 8-bit value."""
        return self._par_p4 if self._par_p4 <= 127 else self._par_p4 - 256

    @property
    def par_p5(self) -> int:
        """Combine _par_p5_msb and _par_p5_lsb into a unsigned 16-bit integer."""
        msb_value = self._par_p5_msb  # Reads CBits value
        lsb_value = self._par_p5_lsb  # Reads CBits value
        return (msb_value << 8) | lsb_value

    @property
    def par_p6(self) -> int:
        """Combine _par_p6_msb and _par_p6_lsb into a unsigned 16-bit integer."""
        msb_value = self._par_p6_msb  # Reads CBits value
        lsb_value = self._par_p6_lsb  # Reads CBits value
        return (msb_value << 8) | lsb_value

    @property
    def par_p7(self) -> int:
        """Read the single-byte _par_p7 signed 8-bit value."""
        return self._par_p7 if self._par_p7 <= 127 else self._par_p7 - 256

    @property
    def par_p8(self) -> int:
        """Read the single-byte _par_p8 signed 8-bit value."""
        return self._par_p8 if self._par_p8 <= 127 else self._par_p8 - 256

    @property
    def par_p9(self) -> int:
        """Combine _par_p9_msb and _par_p9_lsb into a signed 16-bit integer."""
        msb_value = self._par_p9_msb  # Reads CBits value
        lsb_value = self._par_p9_lsb  # Reads CBits value
        combined_value = (msb_value << 8) | lsb_value
        # Convert to signed 16-bit value (two's complement)
        if combined_value >= 0x8000:  # If the value is greater than or equal to 32768
            return combined_value - 0x10000  # Convert to signed by subtracting 65536
        return combined_value

    @property
    def par_p10(self) -> int:
        """Read the single-byte _par_p10 signed 8-bit value."""
        return self._par_p10 if self._par_p10 <= 127 else self._par_p10 - 256

    @property
    def par_p11(self) -> int:
        """Read the single-byte _par_p11 signed 8-bit value."""
        return self._par_p11 if self._par_p11 <= 127 else self._par_p11 - 256

    @property
    def power_mode(self) -> str:
        """
        Sensor power_mode
        +-----------------------------+------------------+
        | Mode                        | Value            |
        +=============================+==================+
        | :py:const:`bmp390.STANDBY`  | :py:const:`0x00` |
        | :py:const:`bmp390.FORCED`   | :py:const:`0x01` |
        | :py:const:`bmp390.FORCED`   | :py:const:`0x02` |
        | :py:const:`bmp390.NORMAL`   | :py:const:`0X03` |
        +-----------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("STANDBY", "FORCED", "NORMAL",)
        return string_name[self._power_mode]

    @power_mode.setter
    def power_mode(self, value: int) -> None:
        if value not in self.power_mode_values:
            raise ValueError("Value must be a valid power_mode setting: STANDBY,FORCED,NORMAL")
        self._power_mode = value

    @property
    def pressure_oversample_rate(self) -> str:
        """
        Sensor pressure_oversample_rate
        Oversampling extends the measurement time per measurement by the oversampling
        factor. Higher oversampling factors offer decreased noise at the cost of
        higher power consumption.
        +---------------------------+------------------+
        | Mode                      | Value            |
        +===========================+==================+
        | :py:const:`bmp390.OSR1`   | :py:const:`0x00` |
        | :py:const:`bmp390.OSR2`   | :py:const:`0x01` |
        | :py:const:`bmp390.OSR4`   | :py:const:`0x02` |
        | :py:const:`bmp390.OSR8`   | :py:const:`0x03` |
        | :py:const:`bmp390.OSR16`  | :py:const:`0x04` |
        | :py:const:`bmp390.OSR32`  | :py:const:`0x05` |
        +---------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("OSR1", "OSR2", "OSR4", "OSR8", "OSR16", "OSR32",)
        return string_name[self._pressure_oversample_rate]

    @pressure_oversample_rate.setter
    def pressure_oversample_rate(self, value: int) -> None:
        if value not in self.pressure_oversample_rate_values:
            raise ValueError("Value must be a valid pressure_oversample_rate: OSR1,OSR2,OSR4,OSR8,OSR16,OSR32")
        self._pressure_oversample_rate = value

    @property
    def temperature_oversample_rate(self) -> str:
        """
        Sensor temperature_oversample_rate
        +---------------------------+------------------+
        | Mode                      | Value            |
        +===========================+==================+
        | :py:const:`bmp390.OSR1`   | :py:const:`0x00` |
        | :py:const:`bmp390.OSR2`   | :py:const:`0x01` |
        | :py:const:`bmp390.OSR4`   | :py:const:`0x02` |
        | :py:const:`bmp390.OSR8`   | :py:const:`0x03` |
        | :py:const:`bmp390.OSR16`  | :py:const:`0x04` |
        | :py:const:`bmp390.OSR32`  | :py:const:`0x05` |
        +---------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("OSR1", "OSR2", "OSR4", "OSR8", "OSR16", "OSR32",)
        return string_name[self._temperature_oversample_rate]

    @temperature_oversample_rate.setter
    def temperature_oversample_rate(self, value: int) -> None:
        if value not in self.temperature_oversample_rate_values:
            raise ValueError(
                "Value must be a valid temperature_oversample_rate: OSR1,OSR2,OSR4,OSR8,OSR16,OSR32")
        self._temperature_oversample_rate = value
        
    @property
    def iir_coefficient(self) -> str:
        """
        Sensor iir_coefficient
        +----------------------------+------------------+
        | Mode                       | Value            |
        +============================+==================+
        | :py:const:`bmp58x.COEF_0`  | :py:const:`0x00` |
        | :py:const:`bmp58x.COEF_1`  | :py:const:`0x01` |
        | :py:const:`bmp58x.COEF_3`  | :py:const:`0x02` |
        | :py:const:`bmp58x.COEF_7`  | :py:const:`0x03` |
        | :py:const:`bmp58x.COEF_15` | :py:const:`0x04` |
        | :py:const:`bmp58x.COEF_31` | :py:const:`0x05` |
        | :py:const:`bmp58x.COEF_63` | :py:const:`0x06` |
        | :py:const:`bmp58x.COEF_127`| :py:const:`0x07` |
        +----------------------------+------------------+
        :return: coefficients as string
        """
        values = ("COEF_0", "COEF_1", "COEF_3", "COEF_7", "COEF_15", "COEF_31", "COEF_63", "COEF_127",)
        return values[self._iir_coefficient]

    @iir_coefficient.setter
    def iir_coefficient(self, value: int) -> None:
        debug = False
        if value not in self.iir_coefficient_values:
            raise ValueError("Value must be a valid iir_coefficients: COEF_0,COEF_1,COEF_3,COEF_7,COEF_15,COEF_31,COEF_63,COEF_127")
        self._iir_coefficient = value

    # Helper method for temperature compensation
    def _calculate_temperature_compensation(self, raw_temp: float) -> float:
        partial_data1 = float(raw_temp - (self.par_t1 * 256.0))
        partial_data2 = partial_data1 * (self.par_t2 / 2.0 ** 30)
        tempc = partial_data2 + (partial_data1 * partial_data1) * (self.par_t3 / 2.0 ** 48)
        return tempc

    # Helper method for pressure compensation
    def _calculate_pressure_compensation(self, raw_pressure: float, tempc: float) -> float:
        # First part
        partial_data1 = (self.par_p6 / 64.0) * tempc
        partial_data2 = (self.par_p7 / 256.0) * (tempc * tempc)
        partial_data3 = (self.par_p8 / 2.0 ** 15) * (tempc * tempc * tempc)
        partial_out1 = (self.par_p5 * 8.0) + partial_data1 + partial_data2 + partial_data3

        # Second part
        partial_data1 = ((self.par_p2 - 16384.0) / 2.0 ** 29) * tempc
        partial_data2 = (self.par_p3 / 2.0 ** 32) * (tempc * tempc)
        partial_data3 = (self.par_p4 / 2.0 ** 37) * (tempc * tempc * tempc)
        partial_out2 = raw_pressure * (
                ((self.par_p1 - 16384.0) / 2.0 ** 20) + partial_data1 + partial_data2 + partial_data3)

        # Third part
        partial_data1 = raw_pressure * raw_pressure
        partial_data2 = (self.par_p9 / 2.0 ** 48) + (self.par_p10 / 2.0 ** 48) * tempc
        partial_data3 = partial_data1 * partial_data2
        partial_data4 = partial_data3 + (raw_pressure * raw_pressure * raw_pressure) * (self.par_p11 / 2.0 ** 65)

        # Final compensated pressure
        return partial_out1 + partial_out2 + partial_data4

    @property
    def temperature(self) -> float:
        """
        The temperature sensor in Celsius
        :return: Temperature in Celsius
        """
        raw_temp = self._temperature
        return self._calculate_temperature_compensation(raw_temp)

    @property
    def pressure(self) -> float:
        """
        The sensor pressure in hPa
        :return: Pressure in hPa
        """
        raw_pressure = float(self._pressure)
        raw_temp = float(self._temperature)

        tempc = self._calculate_temperature_compensation(raw_temp)
        comp_press = self._calculate_pressure_compensation(raw_pressure, tempc)
        return comp_press / 100.0  # Convert to hPa

class BMP280(BMP581):
    """Driver for the BMP390 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the BMP280 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x7F`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`BMP280` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_bmp58x import bmp58x

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        bmp = bmp58x.BMP280(i2c)

    Now you have access to the attributes

    .. code-block:: python

        press = bmp.pressure
        temp = bmp.temperature

        # altitude in meters based on sea level pressure of 1013.25 hPA
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # set sea level pressure to a known sea level pressure in hPa at nearest airport
        # https://www.weather.gov/wrh/timeseries?site=KPDX
        bmp.sea_level_pressure = 1010.80
        meters = bmp.altitude
        print(f"alt = {meters:.2f} meters")

        # Highest resolution for bmp280
        bmp.pressure_oversample_rate = bmp.OSR32
        bmp.temperature_oversample_rate = bmp.OSR2
        bmp.iir_coefficient = bmp.COEF_3
        meters = bmp.altitude

    """
    # Power Modes for BMP280
    power_mode_values = (STANDBY, FORCED, NORMAL)
    BMP280_NORMAL_POWER = const(0x03)
    BMP280_FORCED_POWER = const(0x01)

    # oversampling rates
    # Here we give OSR_SKIP a unique value 0x05, but will remap it to bmp280 values
    # When we get       OSR1=0, OSR2=1, OSR4=2, OSR8=3, OSR16=4, OSR_SKIP=5
    # input to BMP280,  OSR1=1, OSR2=2, OSR4=3, OSR8=4, OSR16=5, OSR_SKIP=0
    # this will be translated in _translate_osr_bmp280
    OSR_SKIP = const(0x05) 

    # OSR_SKIP turns off sampling and we do not present it as setable from outside the driver
    pressure_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16)
    temperature_oversample_rate_values = (OSR1, OSR2, OSR4, OSR8, OSR16)
    
    BMP280_I2C_ADDRESS_DEFAULT = 0x77
    BMP280_I2C_ADDRESS_SECONDARY = 0x76

    ###  BMP390 Constants - notice very different than bmp581
    _REG_WHOAMI_BMP280 = const(0xd0)
    _PWR_CTRL_BMP280 = const(0x1b)
    _CONTROL_REGISTER_BMP280 = const(0xF4)
    _CONFIG_BMP280 = const(0xf5)

    _device_id = RegisterStruct(_REG_WHOAMI_BMP280, "B")

    _power_mode = CBits(2,_CONTROL_REGISTER_BMP280, 0)
    _pressure_oversample_rate = CBits(3, _CONTROL_REGISTER_BMP280, 2)
    _temperature_oversample_rate = CBits(3, _CONTROL_REGISTER_BMP280, 5)
    _control_register = CBits(8, _CONTROL_REGISTER_BMP280, 0)
    _config_register = CBits(8, _CONFIG_BMP280, 0)
    _iir_coefficient = CBits(3, _CONFIG_BMP280, 0)

    # read pressure 0xf7 and temp 0xfa
    _d = CBits(48, 0xf7, 0, 6)

    # Temp & pressure calibrations are all are 16-bits
    _dig_t1_msb = CBits(8, 0x89, 0)  # Most significant byte of dig_t1
    _dig_t1_lsb = CBits(8, 0x88, 0)  # Least significant byte of dig_t1
    _dig_t2_msb = CBits(8, 0x8b, 0)  # Most significant byte of dig_t2
    _dig_t2_lsb = CBits(8, 0x8a, 0)  # Least significant byte of dig_t2
    _dig_t3_msb = CBits(8, 0x8d, 0)  # Most significant byte of dig_t3
    _dig_t3_lsb = CBits(8, 0x8c, 0)  # Least significant byte of dig_t3
    
    _dig_p1_msb = CBits(8, 0x8f, 0)  # Most significant byte of dig_p1
    _dig_p1_lsb = CBits(8, 0x8e, 0)  # Least significant byte of dig_p1
    _dig_p2_msb = CBits(8, 0x91, 0)  # Most significant byte of dig_p2
    _dig_p2_lsb = CBits(8, 0x90, 0)  # Least significant byte of dig_p2
    _dig_p3_msb = CBits(8, 0x93, 0)  # Most significant byte of dig_p3
    _dig_p3_lsb = CBits(8, 0x92, 0)  # Least significant byte of dig_p3
    _dig_p4_msb = CBits(8, 0x95, 0)  # Most significant byte of dig_p4
    _dig_p4_lsb = CBits(8, 0x94, 0)  # Least significant byte of dig_p4
    _dig_p5_msb = CBits(8, 0x97, 0)  # Most significant byte of dig_p5
    _dig_p5_lsb = CBits(8, 0x96, 0)  # Least significant byte of dig_p5
    _dig_p6_msb = CBits(8, 0x99, 0)  # Most significant byte of dig_p6
    _dig_p6_lsb = CBits(8, 0x98, 0)  # Least significant byte of dig_p6
    _dig_p7_msb = CBits(8, 0x9b, 0)  # Most significant byte of dig_p7
    _dig_p7_lsb = CBits(8, 0x9a, 0)  # Least significant byte of dig_p7
    _dig_p8_msb = CBits(8, 0x9d, 0)  # Most significant byte of dig_p8
    _dig_p8_lsb = CBits(8, 0x9c, 0)  # Least significant byte of dig_p8
    _dig_p9_msb = CBits(8, 0x9f, 0)  # Most significant byte of dig_p9
    _dig_p9_lsb = CBits(8, 0x9e, 0)  # Least significant byte of dig_p9

    def __init__(self, i2c, address: int = None) -> None:
        time.sleep_ms(3)        # t_powup 2ms        
        # If no address is provided, try the default, then secondary
        if address is None:
            if self._check_address(i2c, self.BMP280_I2C_ADDRESS_DEFAULT):
                address = self.BMP280_I2C_ADDRESS_DEFAULT
            elif self._check_address(i2c, self.BMP280_I2C_ADDRESS_SECONDARY):
                address = self.BMP280_I2C_ADDRESS_SECONDARY
            else:
                raise RuntimeError("BMP280 sensor not found at I2C expected address (0x77,0x76).")
        else:
        # Check if the specified address is valid
            if not self._check_address(i2c, address):
                raise RuntimeError("BMP280 sensor not found at I2C expected address (0x77,0x76).")
        self._i2c = i2c
        self._address = address
        if self._read_device_id() != 0x58:  # check _device_id after i2c established
            raise RuntimeError("Failed to find the BMP280 sensor with id 0x58")
        
        # To start measurements: temp OSR1, pressure OSR1 must be init with Normal power mode
        # set all values at once
#         self._pressure_oversample_rate = self._translate_osr_bmp280(OSR1)
#         self._temperature_oversample_rate = self._translate_osr_bmp280(OSR1)
#         self._power_mode = BMP280_NORMAL_POWER
#         self._control_register = 0x27
        self._config_register = 0x00 
        self._control_register = (self._translate_osr_bmp280(OSR1) << 5) + (self._translate_osr_bmp280(OSR1) << 2) +  BMP280_NORMAL_POWER
        _ = self.pressure

        time.sleep_ms(4)     # mode change takes 3ms
        time.sleep_ms(63)    # OSR can be take up to 62.5ms standby
        
        self.sea_level_pressure = WORLD_AVERAGE_SEA_LEVEL_PRESSURE
        self.t_fine = 0
        
    def _translate_osr_bmp280(self, osr_value):
    # Map the constants to their corresponding values
        osr_map = {
            OSR1: 1,  # OSR1=0 for other sensors, but 1 for bmp280
            OSR2: 2,  # OSR2=1 for other sensors, but 2 for bmp280
            OSR4: 3,  # OSR4=2 for other sensors, but 3 for bmp280
            OSR8: 4,  # OSR8=3 for other sensors, but 4 for bmp280
            OSR16: 5,  # OSR16=4 for other sensors, but 5 for bmp280
            OSR_SKIP: 0   # OSR_SKIP=0 for bmp280, no other sensor has OSR_SKIP, above we assigned it to 0x05
        }
        # Return the translated value
        return osr_map.get(osr_value, 0)
        
    def _combine_unsigned(self, msb, lsb):
        """Combine msb and lsb into a unsigned 16-bit integer."""
        return ((msb << 8) | lsb) & 0xFFFF
    
    def _combine_signed(self, msb, lsb):
        combined = (msb << 8) | lsb
        # Check if the sign bit is set (MSB of 16-bit value), Subtract 2^16 to sign-extend
        return combined - 0x10000 if combined & 0x8000 else combined
        
    @property
    def dig_t1(self) -> int:
        return self._combine_unsigned(self._dig_t1_msb, self._dig_t1_lsb)

    @property
    def dig_t2(self) -> int:
        return self._combine_signed(self._dig_t2_msb, self._dig_t2_lsb)

    @property
    def dig_t3(self) -> int:
        return self._combine_signed(self._dig_t3_msb, self._dig_t3_lsb)

    @property
    def dig_p1(self) -> int:
        return self._combine_unsigned(self._dig_p1_msb, self._dig_p1_lsb)
    
    @property
    def dig_p2(self) -> int:
        return self._combine_signed(self._dig_p2_msb, self._dig_p2_lsb)

    @property
    def dig_p3(self) -> int:
        return self._combine_signed(self._dig_p3_msb, self._dig_p3_lsb)
    
    @property
    def dig_p4(self) -> int:
        return self._combine_signed(self._dig_p4_msb, self._dig_p4_lsb)

    @property
    def dig_p5(self) -> int:
        return self._combine_signed(self._dig_p5_msb, self._dig_p5_lsb)

    @property
    def dig_p6(self) -> int:
        return self._combine_signed(self._dig_p6_msb, self._dig_p6_lsb)
    
    @property
    def dig_p7(self) -> int:
        return self._combine_signed(self._dig_p7_msb, self._dig_p7_lsb)

    @property
    def dig_p8(self) -> int:
        return self._combine_signed(self._dig_p8_msb, self._dig_p8_lsb)

    @property
    def dig_p9(self) -> int:
        return self._combine_signed(self._dig_p9_msb, self._dig_p9_lsb)

    @property
    def power_mode(self) -> str:
        """
        Sensor power_mode
        notice: Bosch changed the numbers assigned to power modes
        +-----------------------------+------------------+-----------------------------+------------------+
        | Mode   rest of classes      | Value            | BMP 280 Mode                | Value            |
        +=============================+==================+=============================+==================+
        | :py:const:`bmp58x.STANDBY`  | :py:const:`0x00` | :py:const:`bmp280.STANDBY`  | :py:const:`0x00` |
        | :py:const:`bmp581.NORMAL`   | :py:const:`0x01` | :py:const:`bmp280.FORCED`   | :py:const:`0x01` |
        | :py:const:`bmp58x.FORCED`   | :py:const:`0x02` | :py:const:`bmp280.FORCED`   | :py:const:`0x02` |
        | :py:const:`bmp58x.NON_STOP` | :py:const:`0X03` | :py:const:`bmp280.NORMAL`   | :py:const:`0X03` |
        +-----------------------------+------------------+-----------------------------+------------------+
        :return: power_mode as string
        """
        # Notice ordering is different only for BMP280
        string_name = ("STANDBY", "FORCED", "FORCED", "NORMAL",)
        return string_name[self._power_mode]

    @power_mode.setter
    def power_mode(self, value: int) -> None:
        if value not in self.power_mode_values:
            raise ValueError("Value must be a valid power_mode setting: STANDBY,FORCED,NORMAL")
        print(f"mode setter {value=}")
        # remap NORMAL and FORCED for other sensors to the values for bmp280
        # 0x02 = FORCED is ok for bmp280 which has two values for FORCED
        if value == 0x01:  # appropriate for all other classes
            value = BMP280_NORMAL_POWER   # change value to 0x03 for bmp280
        if value == 0x03:  # appropriate for all other classes
            value = BMP280_FORCED_POWER   # change value to 0x03 for bmp280    
        self._power_mode = value

    @property
    def pressure_oversample_rate(self) -> str:
        """
        Sensor pressure_oversample_rate
        Oversampling extends the measurement time per measurement by the oversampling
        factor. Higher oversampling factors offer decreased noise at the cost of
        higher power consumption.
        +---------------------------+------------------+---------------------------+------------------+
        | Mode-for all other classes| Value            | BMP280 Mode                | Value            |
        +===========================+==================+===========================+==================+
        | :py:const:`bmp58x.OSR1`   | :py:const:`0x00` | :py:const:`OSR_SKIP'      | :py:const:`0x00` |
        | :py:const:`bmp58x.OSR2`   | :py:const:`0x01` | :py:const:`bmp280.OSR1`   | :py:const:`0x01` |
        | :py:const:`bmp58x.OSR4`   | :py:const:`0x02` | :py:const:`bmp280.OSR2`   | :py:const:`0x02` |
        | :py:const:`bmp58x.OSR8`   | :py:const:`0x03` | :py:const:`bmp280.OSR4`   | :py:const:`0x03` |
        | :py:const:`bmp58x.OSR16`  | :py:const:`0x04` | :py:const:`bmp280.OSR8``  | :py:const:`0x04` |
        |                           |                  | :py:const:`bmp280.OSR16`  | :py:const:`0x05` |
        +---------------------------+------------------+---------------------------+------------------+
        :return: sampling rate as string
        """
        # Notice these are in the order and numbering that is appropriate for bmp280, which is different
        # than the other sensors
        string_name = ("OSR_SKIP", "OSR1", "OSR2", "OSR4", "OSR8", "OSR16",)
        return string_name[self._pressure_oversample_rate]

    @pressure_oversample_rate.setter
    def pressure_oversample_rate(self, value: int) -> None:
        if value not in self.pressure_oversample_rate_values:
            raise ValueError("Value must be a valid pressure_oversample_rate: OSR_SKIP,OSR1,OSR2,OSR4,OSR8,OSR16")
        # Get whole control register for temp Oversample (3-bits), pressure Oversample (3-bits), powermode
        current_control_register = self._control_register
        # only update pressure oversample
        current_control_register = (current_control_register & 0xe3) + (self._translate_osr_bmp280(value) << 2)
        # Write whole control register at once
        self._config_register = 0x00 
        self._control_register = current_control_register

    @property
    def temperature_oversample_rate(self) -> str:
        """
        Sensor temperature_oversample_rate
        +---------------------------+------------------+---------------------------+------------------+
        | Mode-for all other classes| Value            | BMP280 Mode                | Value            |
        +===========================+==================+===========================+==================+
        | :py:const:`bmp58x.OSR1`   | :py:const:`0x00` | :py:const:`OSR_SKIP'      | :py:const:`0x00` |
        | :py:const:`bmp58x.OSR2`   | :py:const:`0x01` | :py:const:`bmp280.OSR1`   | :py:const:`0x01` |
        | :py:const:`bmp58x.OSR4`   | :py:const:`0x02` | :py:const:`bmp280.OSR2`   | :py:const:`0x02` |
        | :py:const:`bmp58x.OSR8`   | :py:const:`0x03` | :py:const:`bmp280.OSR4`   | :py:const:`0x03` |
        | :py:const:`bmp58x.OSR16`  | :py:const:`0x04` | :py:const:`bmp280.OSR8``  | :py:const:`0x04` |
        |                           |                  | :py:const:`bmp280.OSR16`  | :py:const:`0x05` |
        +---------------------------+------------------+---------------------------+------------------+
        :return: sampling rate as string
        """
        string_name = ("OSR_SKIP", "OSR1", "OSR2", "OSR4", "OSR8", "OSR16", )
        return string_name[self._temperature_oversample_rate]

    @temperature_oversample_rate.setter
    def temperature_oversample_rate(self, value: int) -> None:
        if value not in self.temperature_oversample_rate_values:
            raise ValueError("Value must be a valid pressure_oversample_rate: OSR_SKIP,OSR1,OSR2,OSR4,OSR8,OSR16")
        # Get current control register for temp Oversample (3-bits), pressure Oversample (3-bits), powermode
        current_control_register = self._control_register
        # only update temperature oversample
        current_control_register = (current_control_register & 0x1f) + (self._translate_osr_bmp280(value) << 5)
        # Write whole control register at once
        self._config_register = 0x00 
        self._control_register = current_control_register
        
    # helper function for getting temp & pressure
    def _get_raw_temp_pressure(self):
        raw_data = self._d 
        t_xlsb = (raw_data >> 40) & 0xFF
        t_lsb = (raw_data >> 32) & 0xFF
        t_msb = (raw_data >> 24) & 0xFF
        p_xlsb = (raw_data >> 16) & 0xFF 
        p_lsb = (raw_data >> 8) & 0xFF
        p_msb = raw_data & 0xFF
        self._p_raw = (p_msb << 12) | (p_lsb << 4) | (p_xlsb >> 4)
        self._t_raw = (t_msb << 12) | (t_lsb << 4) | (t_xlsb >> 4)
        return self._t_raw, self._p_raw

    # Helper method for temperature compensation
    def _calculate_temperature_compensation_bmp280(self, raw_temp: float) -> float:
        var1 = (((raw_temp / 16384.0) - (self.dig_t1 / 1024.0)) * self.dig_t2)
        var2 = ((((raw_temp / 131072.0) - (self.dig_t1 / 8192.0)) *
                 ((raw_temp / 131072.0) - (self.dig_t1 / 8192.0))) * self.dig_t3)
        self.t_fine = int(var1 + var2)  # Store t_fine as an instance variable
        tempc = (var1 + var2) / 5120.0
        return tempc

    # Helper method for pressure compensation
    def _calculate_pressure_compensation_bmp280(self, raw_pressure: float, tempc: float) -> float:
        var1 = (self.t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.dig_p6 / 32768.0
        var2 += var1 * self.dig_p5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_p4 * 65536.0)
        var1 = ((self.dig_p3 * var1 * var1 / 524288.0) + (self.dig_p2 * var1)) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_p1

        if var1 == 0.0:
            return 0  # Avoid division by zero

        p = 1048576.0 - raw_pressure
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.dig_p9 * p * p / 2147483648.0
        var2 = p * self.dig_p8 / 32768.0
 
        return p + (var1 + var2 + self.dig_p7) / 16.0

    @property
    def temperature(self) -> float:
        """
        The temperature sensor in Celsius
        :return: Temperature in Celsius
        """
        raw_temp, raw_pressure = self._get_raw_temp_pressure()
        return self._calculate_temperature_compensation_bmp280(raw_temp)

    @property
    def pressure(self) -> float:
        """
        The sensor pressure in hPa
        :return: Pressure in hPa
        """
        raw_temp, raw_pressure = self._get_raw_temp_pressure()

        tempc = self._calculate_temperature_compensation_bmp280(raw_temp)
        comp_press = self._calculate_pressure_compensation_bmp280(raw_pressure, tempc)
        return comp_press / 100.0  # Convert to hPa

