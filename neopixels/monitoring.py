#!/usr/bin/env python
import board
import time
import requests
import json
import board
import neopixel
import multiprocessing
import logging
from configparser import ConfigParser


class StatusMonitor:

    def __init__(self):

        logging.basicConfig(format='%(asctime)s, %(levelname)s - %(message)s', level=logging.INFO)

        config = ConfigParser()
        configFile = "/home/pi/neopixels/monitoring.cfg"
        config.read(configFile)
        try:
            self.bed_min = config.getint('Bed', 'min_temp')
            logging.info("Minimum bed temperature set to {}".format(self.bed_min))
            self.bed_max = config.getint('Bed', 'max_temp')
            logging.info("Maximum bed temperature set to {}".format(self.bed_max))
            self.bed_color = tuple(map(int, (config.get('Bed', 'main_color')).split(',')))
            logging.info("Bed main color set to {}".format(self.bed_color))
            self.bed_heating_color = tuple(map(int, (config.get('Bed', 'heating_color')).split(',')))
            logging.info("Bed heating color set to {}".format(self.bed_heating_color))
            self.bed_cooling_color = tuple(map(int, (config.get('Bed', 'cooling_color')).split(',')))
            logging.info("Bed cooling color set to {}".format(self.bed_cooling_color))
            self.extruder_min = config.getint('Extruder', 'min_temp')
            logging.info("Minimum extruder temperature set to {}".format(self.extruder_min))
            self.extruder_max = config.getint('Extruder', 'max_temp')
            logging.info("Maximum extruder temperature set to {}".format(self.extruder_max))
            self.extruder_color = tuple(map(int, (config.get('Extruder', 'main_color')).split(',')))
            logging.info("Extruder main color set to {}".format(self.extruder_color))
            self.extruder_heating_color = tuple(map(int, (config.get('Extruder', 'heating_color')).split(',')))
            logging.info("Extruder heating color set to {}".format(self.extruder_heating_color))
            self.extruder_cooling_color = tuple(map(int, (config.get('Extruder', 'cooling_color')).split(',')))
            logging.info("Extruder cooling color set to {}".format(self.extruder_cooling_color))
            self.offsets = [config.getint('Rings', 'first_offset'),
                            config.getint('Rings', 'second_offset'),
                            config.getint('Rings', 'third_offset')]
            logging.info("Ring offsets set to {}".format(self.offsets))
            self.time_interval = config.getfloat('Animation', 'time_interval')
            logging.info("Animation time interval set to {}".format(self.time_interval))
            self.ring_order = list(map(int, (config.get('Rings', 'order').split(','))))
            logging.info("Rings order set to {}".format(self.ring_order))
            pin_selector = [board.D10, board.D12, board.D18, board.D21]
            pin_enumerator = ["10", "12", "18", "21"]
            self.pixel_pin = pin_selector[pin_enumerator.index(config.get('GPIO', 'communincation_pin'))]
            logging.info("Communication GPIO pin set to {}".format(self.pixel_pin))
            self.power_monitor = config.getboolean('Power', 'power_monitor')
            if self.power_monitor:
                logging.info("Using power monitor")
            logging.info("Whole config loaded")

        except:
            logging.error("missing configuration")
            exit(1)

        self.power_status = None
        self.status = None
        self.bed_temp = None
        self.bed_given = None
        self.extruder_temp = None
        self.extruder_given = None
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

        self.power_loger_svitch = True
        self.printer_loger_svitch = True
        self.job_loger_svitch = True
        self.object_loger_svitch = True
        self.led_loger_svitch = True

        self.pixels = neopixel.NeoPixel(
            self.pixel_pin, self.num_pixels, brightness=0.2, auto_write=False,
            pixel_order=neopixel.GRB
        )

        for i in range(0, 47):
            self.pixels[i] = (0, 0, 0)
        self.pixels.show()

        self.start_animation = multiprocessing.Process(target=waiting, args=(self.time_interval, self.pixels))

    def check_status(self):

        if self.power_monitor:
            try:
                power = requests.get("http://localhost:7125/machine/device_power/device?device=printer")
                power_dict = power.json()
                self.power_status = str(power_dict['result']['printer'])
                if not self.power_loger_svitch:
                    logging.info("Moonraker power api connected")
                    self.power_loger_svitch = True
            except:
                if self.power_loger_svitch:
                    logging.info("Moonraker power api not responding")
                    self.power_loger_svitch = False

        try:
            printer = requests.get("http://localhost:7125/api/printer")
            printer_dict = printer.json()
            extruder_temp = str(printer_dict['temperature']['tool0']['actual'])
            extruder_given = str(printer_dict['temperature']['tool0']['target'])
            self.extruder_temp = calulate_pos(self.extruder_max, extruder_temp, self.extruder_min)
            self.extruder_given = calulate_pos(self.extruder_max, extruder_given, self.extruder_min)
            bed_temp = str(printer_dict['temperature']['bed']['actual'])
            bed_given = str(printer_dict['temperature']['bed']['target'])
            self.bed_temp = calulate_pos(self.bed_max, bed_temp, self.bed_min)
            self.bed_given = calulate_pos(self.bed_max, bed_given, self.bed_min)
            if not self.printer_loger_svitch:
                logging.info("Moonraker printer api connected")
                self.printer_loger_svitch = True
        except:
            if self.printer_loger_svitch:
                logging.info("Moonraker printer api not responding")
                self.printer_loger_svitch = False

        try:
            job = requests.get("http://localhost:7125/api/job")
            job_dict = job.json()
            status = str(job_dict['state'])
            if self.status != status:
                logging.info("Printer status changed from {} to {}".format(self.status, status))
                self.status = status
            if not self.job_loger_svitch:
                logging.info("Moonraker job api connected")
                self.job_loger_svitch = True
        except:
            if self.job_loger_svitch:
                logging.info("Moonraker job api not responding")
                self.job_loger_svitch = False

        try:
            job_progerss = requests.get("http://localhost:7125/printer/objects/query?virtual_sdcard=progress")
            job_progerss_dict = job_progerss.json()
            progress = str(job_progerss_dict['result']['status']['virtual_sdcard']['progress'])
            if progress == "0.0":
                self.progress = 16
            else:
                self.progress = float(progress) * 16
            if not self.object_loger_svitch:
                logging.info("Moonraker printer object connected")
                self.object_loger_svitch = True
        except:
            if self.object_loger_svitch:
                logging.info("Moonraker printer object not responding")
                self.object_loger_svitch = False

        if self.extruder_temp is None and not self.start_animation.is_alive():
            logging.info("Starting animation")
            self.start_animation.start()

    def update_pixels(self):

        if self.extruder_temp is not None:
            if self.start_animation.is_alive():
                logging.info("Stopping animation")
                self.start_animation.terminate()

            progress_color = self.status_to_color_dict[self.status]
            if self.power_monitor and self.power_status == "off":
                if self.led_loger_svitch:
                    for i in range(48):
                        self.pixels[i - 1] = (0, 0, 0)
                    logging.info("Turning down led lights")
                    self.led_loger_svitch = False
            else:
                if not self.led_loger_svitch:
                    logging.info("Displaing status of data")
                    self.led_loger_svitch = True
                for i in range(16):
                    if self.bed_temp <= self.bed_given:
                        if i <= self.bed_temp:
                            self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (
                                    self.ring_order[0] * 16)] = self.bed_color
                        elif i <= self.bed_given:
                            self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (
                                    self.ring_order[0] * 16)] = self.bed_heating_color
                        else:
                            self.pixels[
                                ((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = (
                                0, 0, 0)
                    else:
                        if i <= self.bed_given:
                            self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (
                                    self.ring_order[0] * 16)] = self.bed_color
                        elif i <= self.bed_temp:
                            self.pixels[((15 - i + self.offsets[self.ring_order[0]]) % 16) + (
                                    self.ring_order[0] * 16)] = self.bed_cooling_color
                        else:
                            self.pixels[
                                ((15 - i + self.offsets[self.ring_order[0]]) % 16) + (self.ring_order[0] * 16)] = (
                                0, 0, 0)

                    if self.extruder_temp <= self.extruder_given:
                        if i <= self.extruder_temp:
                            self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (
                                    self.ring_order[1] * 16)] = self.extruder_color
                        elif i <= self.extruder_given:
                            self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (
                                    self.ring_order[1] * 16)] = self.extruder_heating_color
                        else:
                            self.pixels[
                                ((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = (
                                0, 0, 0)
                    else:
                        if i <= self.extruder_given:
                            self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (
                                    self.ring_order[1] * 16)] = self.extruder_color
                        elif i <= self.extruder_temp:
                            self.pixels[((15 - i + self.offsets[self.ring_order[1]]) % 16) + (
                                    self.ring_order[1] * 16)] = self.extruder_cooling_color
                        else:
                            self.pixels[
                                ((15 - i + self.offsets[self.ring_order[1]]) % 16) + (self.ring_order[1] * 16)] = (
                                0, 0, 0)

                    if i <= self.progress:
                        self.pixels[
                            ((23 - i + self.offsets[self.ring_order[2]]) % 16) + (
                                        self.ring_order[2] * 16)] = progress_color
                    else:
                        self.pixels[((23 - i + self.offsets[self.ring_order[2]]) % 16) + (self.ring_order[2] * 16)] = (
                            0, 0, 0)
            self.pixels.show()


def calulate_pos(max, value, min):
    pos = (float(value) - min) / (max - min) * 16
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
