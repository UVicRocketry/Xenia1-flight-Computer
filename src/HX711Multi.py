from typing import List
import RPi.GPIO as GPIO
import numpy as np

"""

HX711_Multi: This class provides a simple way to interface with multiple
HX711 digital to analog converters connected on a single clock line.
It's intended use is for the strain gauge PCB in Xenia-1

Based on Shmulike's Arduino version https://github.com/shmulike/HX711-multi


Attributes
----------

__PD_SCK_pin [int]: GPIO pin connected to all the clocks of each HX711
(Pin 11 labeled PD_SCK in datasheet)

__DOUT_pins List[int]: GPIO pins connected to data pins of each HX711
(Pin 11 labeled DOUT in datasheet)

__gain [int]: HX711 features programmable gain settings of 64 or 128 for
channel A which is used on the strain gauge pcb. 128 is used by default. NOTE: __gain stores
the number of cycles of the PD_SCK pin needed to set the gain for the HX711. For
128, __gain = 3, for 64, __gain = 2. This is outlined in the datasheet for the
HX711.

__debug_enabled [bool]: Print debug messages to the console when True.

__offsets List[int]: Store the offsets generated by the tare(). This is
the same as tare a scale so that it reads 0 with nothing on it.

__timeout_ms [int]: Max time in milliseconds to wait for HX711s to become
ready while tare()ing and read_raw()ing.

__num_of_HX711s [int]: Total number of HX711s based on the number of DOUT
pins passed to __init__.


Methods
-------

isReady()
    Checks if the HX711 is ready to send data. From data sheet:
        When output data is not ready for retrieval:
        - Digital output pin (DOUT) is high (5V)
        - Serial clock input (PD_SCK) should be low. 
        When ready for retrieval:
        -  DOUT goes to low (0V):

    Returns True if HX711 is ready, False otherwise.

__setGain()
    Channel A of the HX711 can be set to either 64 or 128 gain.

    Returns nothing.

__powerUp()
    Turn on the HX711s
    
    Returns nothing.
    
tare()
    Sets __offsets[] for each chip. This checks for excessive deviations
    in readings and fails if more than 20% of readings lie outside the std dev.

    Returns True if offsets are calculated, False if high deviation occurs.
    
    Params:
    
    num_of_samples [int]
        Total number of readings to take from read_raw() before calculating
        their standard deviation

    max_std_dev [float]
        Maximum allowable standard deviation of a value from the mean before
        tare() will reject it.

read()
    Gets a reading from all HX711s. NOTE: isReady() must return True before
    calling read() or it will fail.

    Returns a list of integer readings with offsets applied from the HX711s
    if isReady(), otherwise returns False.

read_raw()
    Gets raw integer readings from all HX711s. NOTE: isReady() must return True
    before calling read_raw() or it will fail.

    Returns a list of integer readings from the HX711s if isReady(),
    otherwise returns False.

"""

class HX711_Multi:

    __PD_SCK_pin = None
    __DOUT_pins = []
    __gain = None
    __debug_enabled = None
    __offsets = [] 
    __timeout = 300
    __num_of_HX711s = None

    def __init__(self, 
                data_pins: List[int],
                clock_pin: int,
                gain: int = 128,
                debug: bool = False):

        self.__PD_SCK_pin = clock_pin
        self.__DOUT_pins = data_pins
        self.__debug_enabled = debug
        self.__num_of_HX711s = len(self.__DOUT_pins)

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Set the pins as outputs
        GPIO.setup(self.__PD_SCK_pin, GPIO.OUT)
        for pin in self.__DOUT_pins:
            GPIO.setup(pin, GPIO.IN)
            
        self.__setGain(gain)
        self.__powerUp()

    def isReady(self):

        # DOUT pin goes low (0V) when it is ready to send a reading
        for data_pin in self.__DOUT_pins:
            if GPIO.input(data_pin) == GPIO.HIGH:
                if self.__debug_enabled:
                    print("HX711 on pin", data_pin, "not ready")
                    continue
                return False
                
        return True

    def tare(self, num_of_samples: int, max_std_dev_from_mean: float):

        if num_of_samples < 100:
            print("Cannot tare with less than 100 samples!")
            return False
        
        samples = []
        while len(samples) < num_of_samples:
            if self.isReady():
                samples.append(self.readRaw())

        """
            Do some fat stats to reject outlier data points based on
            https://www.adamsmith.haus/python/answers/how-to-remove-
            outliers-from-a-numpy-array-in-python
        """

        samples = np.array(samples).T
        means = np.mean(samples, axis=1).reshape(-1,1)
        std_devs = np.std(samples, axis=1).reshape(-1,1)
        dists_from_means = abs(samples - means)

        # True/false mask to extract non outlier values
        no_outliers = dists_from_means <= (max_std_dev_from_mean * std_devs)
        clean_data = [row[no_outliers[i]] for i,row in enumerate(samples)]

        clean_data_length = 0
        for data_list in clean_data:
            clean_data_length += len(data_list)

        if len(clean_data) < 0.8*len(samples):
            if self.__debug_enabled:
                print("Failed to tare. Excessive deviations measured.")
            return false
            
        # Calculate offsets from clean data
        avg_samples = [np.average(row) for row in clean_data]
        self.__offsets = avg_samples

        if self.__debug_enabled:
            print("Tared, offsets:")
            print(self.__offsets)

        return True

    def read(self):
        raw_readings = self.readRaw()
        
        if raw_readings == False:
           return False 
        else:
            return np.array(raw_readings) - np.array(self.__offsets)

    def readRaw(self):

        if self.__debug_enabled and not self.isReady():
            print("HX711s are not ready! Ensure isReady() returns True",
                  "before calling read() or readRaw()")

        # Read value from every HX711. Each cycle of PD_SCK shifts one bit
        # out in twos complement.
        readings = [0]*self.__num_of_HX711s

        for bits in range(24):

            GPIO.output(self.__PD_SCK_pin, GPIO.HIGH)
            GPIO.output(self.__PD_SCK_pin, GPIO.LOW)

            for i, data_pin in enumerate(self.__DOUT_pins):
                readings[i] = readings[i] << 1
                readings[i] |= GPIO.input(data_pin)

        # Gain for the next reading is set by cycling the PD_SCK pin
        # __gain number of times.
        GPIO.output(self.__PD_SCK_pin, GPIO.LOW)

        for _ in range(self.__gain):
            GPIO.output(self.__PD_SCK_pin, GPIO.HIGH)
            GPIO.output(self.__PD_SCK_pin, GPIO.LOW)
            
        # Calculate int from 2's complement as this is the form the HX711
        # sends its data according to the datasheet. Readings are 24bit.
        for reading in readings:
            if (reading & (1 << (24 - 1))) != 0:
                reading = reading - (1 << 24)

        return readings

    def __powerUp(self):
        GPIO.output(self.__PD_SCK_pin, GPIO.LOW)

    def __setGain(self, gain):

        if gain == 128:
            self.__gain = 1
        elif gain == 64:
            self.__gain = 3
        elif self.__debug_enabled:
            print("Invalid gain used. Pass values of 128 or 64 only!")
