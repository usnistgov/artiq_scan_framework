device_db = {
    "core": {
        "type": "local",
        "module": "artiq.coredevice.core",
        "class": "Core",

        # see: hardware/artiq/clock-setup
        "arguments": {
            "host": "192.168.1.1",
            "ref_period": 1.2e-9,
            "external_clock": True
        }
    },
    "core_log": {
        "type": "controller",
        "host": "::1",
        "port": 1068,
        "command": "aqctl_corelog -p {port} --bind {bind} 192.168.1.1"
    },
    "core_cache": {
        "type": "local",
        "module": "artiq.coredevice.cache",
        "class": "CoreCache"
    },
    "core_dma": {
        "type": "local",
        "module": "artiq.coredevice.dma",
        "class": "CoreDMA"
    },
    "core_dds": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "DDSGroupAD9914",
        "arguments": {
            "first_dds_bus_channel": 50,
            "dds_bus_count": 1,
            "dds_channel_count": 12,
            # see: hardware/artiq/clock-setup
            "sysclk": 2.5e9
        }
    },

    # i2c
    "i2c_switch": {
        "type": "local",
        "module": "artiq.coredevice.i2c",
        "class": "PCA9548"
    },
    "i2c_expander": {
        "type": "local",
        "module": "artiq.coredevice.i2c",
        "class": "TCA6424A",
    },

    # ttl
    "ttl_init_exp": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 0},
    },
    "ttl_rp": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 1},
        "comment": "ttl 1"
    },
    "ttl_bd": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 2},
        "comment": "ttl 2"
    },
    "ttl_sh": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 3},
        "comment": "ttl 3"
    },
    "ttl_bdd": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 4},
        "comment": "ttl 4"
    },
    "ttl_rr": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 5},
        "comment": "ttl 5"
    },
    "ttl_br": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 6},
        "comment": "ttl 6"
    },
    "ttl_brco": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 7},
    },
    "ttl_micro": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 8},
    },
    "ttl_tickle": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 9},
    },
    "ttl_rf_chip": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 10},
    },
    "ttl_pmt": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 11}
    },
    "ttl_bdne": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 12}
    },
    "ttl_ramne": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 13}
    },
    "ttl_PI_shutter": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 14}
    },
    "ttl_pmt_switch": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 15}
    },
    "ttl_cs0": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 16},
    },
    "ttl_cs1": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 17},
    },
    "ttl_ldac": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 18}
    },
    "ttl_clr": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 19}
    },
    "ttl20": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 20},
    },
    "ttl21": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 21},
    },
    "ttl22": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 22}
    },
    "ttl23": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 23}
    },
    "ttl24": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 24}
    },
    "ttl25": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 25}
    },
    "ttl26": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 26}
    },
    "ttl27": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 27}
    },
    "ttl_sma": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLInOut",
        "arguments": {"channel": 40}
    },
    "led": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": 41}
    },
    "ttl_ams101_ldac": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLOut",
        "arguments": {"channel": 42}
    },
    "ttl_clock0": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLClockGen",
        "arguments": {"channel": 43}
    },
    "ttl_clock1": {
        "type": "local",
        "module": "artiq.coredevice.ttl",
        "class": "TTLClockGen",
        "arguments": {"channel": 44}
    },

    # dds'
    "dds_micro": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 0},
        "comment": "dds0 \n micro"
    },
    "dds1": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 1},
        "comment": "broken"
    },
    "dds_bd": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 2},
        "comment": "dds2 \n blue doppler"
    },
    "dds_sh": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 3},
        "comment": "dds3 \n shift after uv doubler"
    },
    "dds_bdd": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 4},
        "comment": "dds4 \n far detuned"
    },
    "dds_rr": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 5},
        "comment": "dds5 red raman\n "
    },
    "dds_br": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 6},
        "comment": "dds6 \n blue raman "
    },
    "dds_rp": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 7},
        "comment": "dds 7 \n repump"
    },
    "dds8": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 8},
        "comment": "broken"
    },
    "dds_tickle": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 9},
        "comment": "dds 9 tickle"
    },
    "dds_rf_chip": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 10},
        "comment": "dds 10 rf chip"
    },
    "dds_I2shift": {
        "type": "local",
        "module": "artiq.coredevice.dds",
        "class": "AD9914",
        "arguments": {"bus_channel": 50, "channel": 11},
        "comment": "dds 11 i2 shift before lock"
    },

    # spi
    "spi_ams101": {
        "type": "local",
        "module": "artiq.coredevice.spi",
        "class": "SPIMaster",
        "arguments": {"channel": 45}
    },
    "spi0": {
        "type": "local",
        "module": "artiq.coredevice.spi",
        "class": "SPIMaster",
        "arguments": {"channel": 46}
    },
    "spi1": {
        "type": "local",
        "module": "artiq.coredevice.spi",
        "class": "SPIMaster",
        "arguments": {"channel": 47}
    },
    "spi2": {
        "type": "local",
        "module": "artiq.coredevice.spi",
        "class": "SPIMaster",
        "arguments": {"channel": 48}
    },
    "spi3": {
        "type": "local",
        "module": "artiq.coredevice.spi",
        "class": "SPIMaster",
        "arguments": {"channel": 49}
    },
    # controllers
    #"hello": {
    #    "type": "controller",
    #    # ::1 is the IPv6 localhost address. If this controller is running on a remote machine,
    #    # replace it with the IP or hostname of the machine. If using the hostname, make sure
    #    # that it always resolves to a network-visible IP address (see documentation).
    #    "host": "687STYLAB",
    #    "port": 4000,
    #    "command": "./hello_controller.py -v -p {port} --bind {bind} --no-localhost-bind"
    #},
    # bk precision power 1785b supply
    #"bkp1785b": {
    #    "type": "controller",
    #    "host": "127.0.0.1",
    #    "port": 4001,
    #   "command": "bkp1785b_controller.py -v -p {port} --bind {bind} --simuation"
    #},
    "oven": {
        "type": "local",
        "module": "lib.drivers.bkp1785b",
        "class": "Bkp1785B",
    	"arguments": {
    	    "port": "/dev/ttyUSB2",
			"baudrate": 9600,
			"timeout": 5,
			"max_current": 1.44,
			"max_voltage": 0.6,
			"simulation": True
		}
    },
    "position_sensor": {
        "type": "local",
        "module": "lib.drivers.keyence_dlrs1a",
        "class": "KeyenceDLRS1A",
    	"arguments": {
    	    "port": "COM1",
			"baudrate": 9600,
			"timeout": 0.1,
			"simulation": False,
            "parity": 'N',
            "stopbits": 1
		}
    },
    # thorlabs pm100 power meter
    "thorlabs_pm100": {
        "type": "controller",
        "host": "687STYLAB",
        "port": 4002,
        "command": "/home/maglab/artiq/work/artiq_controllers/thorlabs_pm100_controller.py -v -p {port} --bind {bind} --device /dev/usbtmc0 --no-localhost-bind"
    },
    # national instruments 7433 DAC
    #"ni_7433": {
    #    "type": "controller",
    #    "host": "686PPMS",
    #    "port": 4003,
    #    "command": "python ni_6733_controller.py -v -p {port} --bind {bind} --device 6733 --no-localhost-bind"
    #},
    "dac": {
        "type": "local",
        "module": "artiq.coredevice.ad5360",
        "class": "AD5360",
        "arguments": {
            "spi_device": "spi0",
            "ldac_device": "ttl18"
        }
    },

    # -- aliases --

    # ttls
    "ttl0": "ttl_init_exp",
    "ttl1": "ttl_rp",
    "ttl2": "ttl_bd",
    "ttl3": "ttl_sh",
    "ttl4": "ttl_bdd",
    "ttl5": "ttl_rr",
    "ttl6": "ttl_br",
    "ttl7": "ttl_brco",
    "ttl8": "ttl_micro",
    "ttl9": "ttl_tickle",
    "ttl10": "ttl_rf_chip",
    "ttl11": "ttl_pmt",
    "ttl12": "ttl_bdne",
    "ttl13": "ttl_ramne",
    "ttl14": "ttl_PI_shutter",
    "ttl15": "ttl_pmt_switch",
    "ttl16": "ttl_cs0",
    "ttl17": "ttl_cs1",
    "ttl18": "ttl_ldac",
    "ttl19": "ttl_clr",

    # dds'

    # allows dds' to always be refered to by their number
    # e.g. in the startup kernel
    "dds0": "dds_micro",
    "dds2": "dds_bd",
    "dds3": "dds_sh",
    "dds4": "dds_bdd",
    "dds5": "dds_rr",
    "dds6": "dds_br",
    "dds7": "dds_rp",
    "dds9": "dds_tickle",
    "dds10": "dds_rf_chip",
    "dds11": "dds_I2shift",


    # i2c bus
    "pca": "i2c_switch",
    "tca": "i2c_expander",
    "power_meter": "thorlabs_pm100",
}