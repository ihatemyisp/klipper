# Support for the PCA9632 LED driver ic
#
# Copyright (C) 2022  Ricardo Alcantara <ricardo@vulcanolabs.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from . import bus, mcp4018

BACKGROUND_PRIORITY_CLOCK = 0x7fffffff00000000

# Register addresses
PCA9632_MODE1 = 0x00
PCA9632_MODE2 = 0x01
PCA9632_PWM0 = 0x02
PCA9632_PWM1 = 0x03
PCA9632_PWM2 = 0x04
PCA9632_PWM3 = 0x05
PCA9632_GRPPWM = 0x06
PCA9632_GRPFREQ = 0x07
PCA9632_LEDOUT = 0x08

LED_PWM = 0x02
PCA9632_LED0 = 0x00
PCA9632_LED1 = 0x02
PCA9632_LED2 = 0x04
PCA9632_LED3 = 0x06

class PCA9632:
    def __init__(self, config):
        self.printer = printer = config.get_printer()
        if config.get("scl_pin", None) is not None:
            self.i2c = mcp4018.SoftwareI2C(config, 98)
        else:
            self.i2c = bus.MCU_I2C_from_config(config, default_addr=98)
        color_order = config.get("color_order", "RGBW")
        if sorted(color_order) != sorted("RGBW"):
            raise config.error("Invalid color_order '%s'" % (color_order,))
        self.color_map = ["RGBW".index(c) for c in color_order]
        self.prev_regs = {}
        pled = printer.load_object(config, "led")
#        *Note*
#        For now, just commenting out to get v0.12 compiling.
#
#        !Warning!
#        This build will only work on a Replicator 2 and 2X.
#
#        self.led_helper = pled.setup_helper(config, self.update_leds, 1)
        self.led_helper = pled.setup_helper(config, self.update_leds, 1, True)
        printer.register_event_handler("klippy:connect", self.handle_connect)
    def reg_write(self, reg, val, minclock=0):
        if self.prev_regs.get(reg) == val:
            return
        self.prev_regs[reg] = val
        self.i2c.i2c_write([reg, val], minclock=minclock,
                           reqclock=BACKGROUND_PRIORITY_CLOCK)
    def handle_connect(self):
        #Configure MODE1
        self.reg_write(PCA9632_MODE1, 0x00)
#       See note and warning above
#
#        #Configure MODE2 (DIMMING, INVERT, CHANGE ON STOP,TOTEM)
#        self.reg_write(PCA9632_MODE2, 0x15)
        #Configure MODE2 (BLINKING, INVERT, CHANGE ON STOP,TOTEM)
        self.reg_write(PCA9632_MODE2, 0x35)
        #Configure duty cycle for blink
        self.reg_write(PCA9632_GRPPWM, 128)
        self.update_leds(self.led_helper.get_status()['color_data'], None)
    def update_leds(self, led_state, print_time):
        minclock = 0
        if print_time is not None:
            minclock = self.i2c.get_mcu().print_time_to_clock(print_time)

        color = [int(v * 255. + .5) for v in led_state[0]]
        led0, led1, led2, led3 = [color[idx] for idx in self.color_map]
        self.reg_write(PCA9632_PWM0, led0, minclock=minclock)
        self.reg_write(PCA9632_PWM1, led1, minclock=minclock)
        self.reg_write(PCA9632_PWM2, led2, minclock=minclock)
        self.reg_write(PCA9632_PWM3, led3, minclock=minclock)
        self.reg_write(PCA9632_GRPFREQ , color[4], minclock=minclock)

        LEDOUT = (LED_PWM << PCA9632_LED0 if led0 else 0)
        LEDOUT |= (LED_PWM << PCA9632_LED1 if led1 else 0)
        LEDOUT |= (LED_PWM << PCA9632_LED2 if led2 else 0)
        LEDOUT |= (LED_PWM << PCA9632_LED3 if led3 else 0)
        if color[4] > 0:
            LEDOUT = LEDOUT | (LEDOUT >> 1)
        self.reg_write(PCA9632_LEDOUT, LEDOUT, minclock=minclock)
    def get_status(self, eventtime):
        return self.led_helper.get_status(eventtime)

def load_config_prefix(config):
    return PCA9632(config)
