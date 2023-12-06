// Software SPI emulation
//
// Copyright (C) 2019  Kevin O'Connor <kevin@koconnor.net>
//
// This file may be distributed under the terms of the GNU GPLv3 license.

#include "board/gpio.h" // gpio_out_setup
#include "basecmd.h" // oid_alloc
#include "command.h" // DECL_COMMAND
#include "sched.h" // sched_shutdown
#include "spicmds.h" // spidev_set_software_bus

struct spi_software {
    struct gpio_in miso;
    struct gpio_out mosi, sclk;
    uint8_t mode;
//        *Note*
//        For now, just commenting out to get v0.12 compiling. Not sure if this will break other builds
//
//        !Warning!
//        This build will likely only work on a Replicator 2 and 2X.
//
    uint8_t flags;
};

enum {
    SF_HAVE_MOSI = 1, SF_HAVE_MISO = 2
};

void
command_spi_set_software_bus(uint32_t *args)
{
    uint8_t mode = args[4];
    if (mode > 3)
        shutdown("Invalid spi config");

    struct spidev_s *spi = spidev_oid_lookup(args[0]);
    struct spi_software *ss = alloc_chunk(sizeof(*ss));
//  See note and warning above
//    ss->miso = gpio_in_setup(args[1], 1);
//    ss->mosi = gpio_out_setup(args[2], 0);

    if (args[1] != args[0])
        ss->flags |= SF_HAVE_MISO;
    if (args[2] != args[0])
        ss->flags |= SF_HAVE_MOSI;

    if (ss->flags & SF_HAVE_MISO)
        ss->miso = gpio_in_setup(args[1], 1);
    if (ss->flags & SF_HAVE_MOSI)
        ss->mosi = gpio_out_setup(args[2], 0);
    ss->sclk = gpio_out_setup(args[3], 0);
    ss->mode = mode;
    spidev_set_software_bus(spi, ss);
}
DECL_COMMAND(command_spi_set_software_bus,
             "spi_set_software_bus oid=%c miso_pin=%u mosi_pin=%u sclk_pin=%u"
             " mode=%u rate=%u");

void
spi_software_prepare(struct spi_software *ss)
{
    gpio_out_write(ss->sclk, ss->mode & 0x02);
}

void
spi_software_transfer(struct spi_software *ss, uint8_t receive_data
                      , uint8_t len, uint8_t *data)
{
    while (len--) {
        uint8_t outbuf = *data;
        uint8_t inbuf = 0;
        for (uint_fast8_t i = 0; i < 8; i++) {
            if (ss->mode & 0x01) {
                // MODE 1 & 3
                gpio_out_toggle(ss->sclk);
//                See note and warning above
//                gpio_out_write(ss->mosi, outbuf & 0x80);
                if (ss->flags & SF_HAVE_MOSI)
                    gpio_out_write(ss->mosi, outbuf & 0x80);
                outbuf <<= 1;
                gpio_out_toggle(ss->sclk);
//              See note and warning above                
//                inbuf <<= 1;
//                inbuf |= gpio_in_read(ss->miso);
                if (ss->flags & SF_HAVE_MISO) {
                    inbuf <<= 1;
                    inbuf |= gpio_in_read(ss->miso);
                }
            } else {
                // MODE 0 & 2
//              See note and warning above
//                gpio_out_write(ss->mosi, outbuf & 0x80);
                if (ss->flags & SF_HAVE_MOSI)
                    gpio_out_write(ss->mosi, outbuf & 0x80);
                outbuf <<= 1;
                gpio_out_toggle(ss->sclk);
//              See note and warning above
//                inbuf <<= 1;
//                inbuf |= gpio_in_read(ss->miso);
                if (ss->flags & SF_HAVE_MISO) {
                    inbuf <<= 1;
                    inbuf |= gpio_in_read(ss->miso);
                }
                gpio_out_toggle(ss->sclk);
            }
        }

//      See note and warning above
//        if (receive_data)
//            *data = inbuf;
//        data++;
        if (ss->flags & SF_HAVE_MISO) {
            if (receive_data)
                *data = inbuf;
            data++;
        }
    }
}
