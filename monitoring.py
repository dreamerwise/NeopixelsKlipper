#!/usr/bin/env python
import board
import time
import requests
import json
import board
import neopixel
import multiprocessing


class StatusMonitor:

    def __init__(self):

        # COLOR SETTINGS:
        self.bed_color = (0, 0, 255)
        self.bed_heating_color = (0, 0, 100)
        self.bed_cooling_color = (0, 100, 255)
        self.extruder_color = (255, 0, 0)
        self.extruder_heating_color = (100, 0, 0)
        self.extruder_cooling_color = (255, 100, 0)
        # OFFSET Values for rings:
        self.bed_offset = 0
        self.extruder_offset = 13
        self.progress_offset = 7
        # ANIMATION SPEED
        self.time_interval = 0.03
        # RING ORDER 3 - status, 2 - extruder temp, 1 - heat bed temp
        self.ring_order = [3, 2, 1]
        # GPIO PORT
        self.pixel_pin = board.D18
        self.status = None
        self.bed_temp = 0
        self.bed_given = 0
        self.extruder_temp = 0
        self.extruder_given = 0
        self.progress = 0
        self.num_pixels = 48
        self.status_to_color_dict = {
            'Operational': (255, 255, 255),
            'Printing': (0, 255, 0),
            'Pausing': (0, 191, 255),
            'Paused': (0, 0, 255),
            'Cancelling': (220, 20, 60),
            'Error': (255, 0, 0),
            'Offline': (255, 0, 0),
            'Offline after error': (139, 0, 0),
            'Opening serial connection': (248, 248, 255),
            None: None
        }

        self.pixels = neopixel.NeoPixel(
            self.pixel_pin, self.num_pixels, brightness=0.2, auto_write=False,
            pixel_order=neopixel.GRB
        )

        for i in range(0, 47):
            self.pixels[i] = (0, 0, 0)
        self.pixels.show()

        self.t = multiprocessing.Process(target=waiting, args=(self.time_interval, self.pixels))

    def check_status(self):
        try:
            printer = requests.get("http://localhost:7125/api/printer")
            printer_dict = printer.json()
            extruder_temp = str(printer_dict['temperature']['tool0']['actual'])
            extruder_given = str(printer_dict['temperature']['tool0']['target'])
            self.extruder_temp = calulate_pos(240, extruder_temp, 20)
            self.extruder_given = calulate_pos(240, extruder_given, 20)
            bed_temp = str(printer_dict['temperature']['bed']['actual'])
            bed_given = str(printer_dict['temperature']['bed']['target'])
            self.bed_temp = calulate_pos(80, bed_temp, 23)
            self.bed_given = calulate_pos(80, bed_given, 23)

        except:
            print("Moonraker api not responding")

        try:
            job = requests.get("http://localhost:7125/api/job")
            job_progerss = requests.get("http://localhost:7125/printer/objects/query?virtual_sdcard=progress")
            job_dict = job.json()
            job_progerss_dict = job_progerss.json()
            self.status = str(job_dict['state'])
            progress = str(job_progerss_dict['result']['status']['virtual_sdcard']['progress'])
            if progress == "0.0":
                self.progress = 16
            else:
                self.progress = float(progress) * 16

        except:
            print("Moonraker api not responding")
            print(self.extruder_temp, self.bed_temp, self.progress, self.status)

        if self.extruder_temp == 0 and not self.t.is_alive():
            self.t.start()

    def update_pixels(self):

        if self.extruder_temp != 0:
            if self.t.is_alive():
                self.t.terminate()

            progress_color = self.status_to_color_dict[self.status]
            for i in range(16):
                               if self.bed_temp <= self.bed_given:
                    if i <= self.bed_temp:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = self.bed_color
                    elif i <= self.bed_given:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = self.bed_heating_color
                    else:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = (0, 0, 0)
                else:
                    if i <= self.bed_given:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = self.bed_color
                    elif i <= self.bed_temp:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = self.bed_cooling_color
                    else:
                        self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = (0, 0, 0)

                if self.extruder_temp <= self.extruder_given:
                    if i <= self.extruder_temp:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = self.extruder_color
                    elif i <= self.extruder_given:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = self.extruder_heating_color
                    else:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = (0, 0, 0)
                else:
                    if i <= self.extruder_given:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = self.extruder_color
                    elif i <= self.extruder_temp:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = self.extruder_cooling_color
                    else:
                        self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = (0, 0, 0)

                if i <= self.progress:
                    self.pixels[((15 - i + self.offsets[self.ring_order[2]]) % 16) + (self.ring_order[2] * 16)] = progress_color
                else:
                    self.pixels[((15 - i + self.offsets[self.ring_order[2]]) % 16) + (self.ring_order[2] * 16)] = (0, 0, 0)
            # print (self.pixels)
            self.pixels.show()


def calulate_pos(max, value, offset):
    pos = (float(value) - offset) / (max - offset) * 16
    if pos < 0:
        pos = 0
    return pos


def waiting(interval, pixels):
    colorlist = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

    for i in range(3):
        for j in range(16):
            pixel = ((15 - j) % 16)
            pixels[pixel] = colorlist[i]
            pixels[pixel + 16] = colorlist[i]
            pixels[pixel + 32] = colorlist[i]
            pixels[pixel + 1] = (0, 0, 0)
            pixels[pixel + 17] = (0, 0, 0)
            if j == 0:
                pixels[0] = (0, 0, 0)
            else:
                pixels[pixel + 33] = (0, 0, 0)
            pixels.show()
            time.sleep(interval)
    colorbase = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    color = (0, 0, 0)
    while True:
        for i in range(3):
            for j in range(511):
                if j <= 255:
                    color = tuple(col * j for col in colorbase[i])
                else:
                    color = tuple((col * (511 - j)) for col in colorbase[i])
                for k in range(48):
                    pixels[k] = color
                pixels.show()
                time.sleep(interval / 100)
    """while True:
        for j in range(96):
            if j <= 47:
                pixels[47 - j] = (255, 255, 255)
            else:
                pixels[95 - j] = (0, 0, 0)
            pixels.show()
            time.sleep(interval)
    """


Monitor = StatusMonitor()
while True:
    Monitor.check_status()
    Monitor.update_pixels()
    time.sleep(1)
