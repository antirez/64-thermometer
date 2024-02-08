# Low cost C64-style thermometer

This is an ESP8266 project aiming to provide a useful thermometer project
that is also a tribute to the old 80s computing era: the graphics is
reminiscent of the Commodore 64, and the backgrounds are extracted
from actual games screenshots.

[<img src="https://i.ytimg.com/vi/GHrPLEnpWjo/0.jpg" width="50%">](https://www.youtube.com/watch?v=GHrPLEnpWjo "C64 style thermometer demo")

*Click the above image to see the video*


The hardware has a total cost of ~5 euros. You will need:
* A 160x128 display based on ST7789 / ST7735. I used [this one](https://it.aliexpress.com/item/1005005621843286.html)
* A DHT22 temperature sensor. You will find one everywhere.
* A cheap ESP8266 with all the required pins accessible. I used [one almost identical to this one](https://it.aliexpress.com/item/1005005977505151.html). Any ESP8266 (or ESP32, if you prefer) with all the pins we need will work.

All the code is written in MicroPython, using an home-made TFT driver.

## Features

The thermometer displays the current temperature and humidity and takes
history of past temperatures in order to display hourly and daily graphs.
The hourly graph is sampled every 30 second by default (two readings 15 seconds apart averaged together), so the graph actually covers 30*160 seconds (160 is the screen width), for a total of 80 minutes. This can be configured.

The daily graph covers a full day, since each data point in the day is taken at intervals of 9 minutes (and is the average of the past 9 minutes of hourly data, so you get a smooth graph). From time to time, the display saves the historical data on the device flash: this way if the device is disconnected from the power for a short time, graphs are retained, however I'm not sure what is the effect of all this writing in your device flash memory. If are concerned with this, edit the `main.py` file and set `save_history` to `False`.

**The background images are copyrighted by the their owners**. I hope that this project is considered fair use / tribute artwork. The games are not really included of course, I just selected a few real gameplay screenshot and cut relevant 160x128 areas. You can add your own images if you wish (read later).

# Creating a C64 thermometer from scratch

To start, get your hardware. I got my stuff from AliExpress (links at the start of this README), feel free to reuse what you have at home. For instance while an EXP32 is an overkill for this project, it will work well. Similarly you should be able to adapt some other ST77xx based display easily if you have some programming / tinkering experience. Likewise, there are better sensors than the DHT22 I'm using, and you may want to get one. Otherwise it could be better to stick to the exact hardware I used.

## Flashing the MicroPython image into your ESP8266

Install esptool with pip or by any other mean. Than erase the flash and install MicroPython image with the following commands. Of course you have to substitute `/dev/ttyUSB0` with your device. The name is `ttyACM...` or `tty.usbmodem...` or similar, depending on the operating system, serial-USB driver and so forth.

    esptool.py --port /dev/ttyUSB0 erase_flash
    esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 ESP8266_GENERIC-20240105-v1.22.1.bin

If the installation works as expected, you should be able to see the MicroPython prompt via the USB-serial. Install `mpremote` with `pip`, then:

    mpremote repl

Press CTRL+C a few times. You should see:

```
MicroPython v1.22.1 on 2024-01-05; ESP module with ESP8266
Type "help()" for more information.
```

**If it does not work, when flashing the `.bin` image to the ESP8266, you may need an additional flag, `-fm dout`**, so try again with:


    esptool.py --port /dev/ttyUSB0 --baud 460800 -fm dout write_flash --flash_size=detect 0 ESP8266_GENERIC-20240105-v1.22.1.bin

## Connecting the display and the DHT22 sensor

Connect the display following these instructions:

    LED -> GPIO5 (sometimes called "D1" on the board)
    SCK -> GPIO14 (sometimes called "D5" on the board)
    SDA/MOSI -> GPIO13 (sometimes called "D7" on the board)
    A0/DC -> GPIO4 (sometimes called "D2" on the board)
    RESET -> GPIO2 (sometimes called "D4" on the board)
    CS -> GPIO10 (sometimes called "SDD3" on the board)
    GND -> Any GND on the board
    VC -> Any V3.3 on the board

Connect the DHT22 in this way:

     -----
    /     \
    +-----+
    |-...-|
    |-...-|
    +-----+
     ||||
     1234

    Pin 1 -> VCC -> Any V3.3 on the board
    Pin 2 -> Data -> GPIO16 (sometimes called "D0" on the board)
    Pin 3 -> not connected
    Pin 4 -> GND -> Any GND on the board

Finally plug your ESP2866 to the USB port.

## Transfer the MicroPython code and background images to the device

Use the following command, making sure to also write the final `:` as specified below.

    mpremote cp *.py :
    mpremote cp pngs/*.565 :

Then when the transfer is completed, press the reset button in the device, or remove the power and then restore it, and you should see the C64 splash screen in the device.

## Using your own images

Using `mpremote` you can easily list the files content in your device.
For instance try:

    mpremote ls

Similarly you can remove the existing .565 images with `rm`.
Then, cat 160x128 pixels PNG from other screenshots, your own pictures or
whatever you want. To convert the PNG files to 565 files, clone the ST77xx-pure-MP driver repository and compile the `pngto565` utility:

    git clone https://github.com/antirez/ST77xx-pure-MP
    cd ST77xx-pure-MP/pngto565
    make

Use the `png565` utility like that:

    ./png565 myfile.png myfile.565

Then transfer your image to the ESP2866 device:

    mpremote cp myfile.565 :

Now the thermometer will randomly display your image, too. You can load as many images as you wish (and as your flash size allows). Images don't use device memory, they are loaded on demand directly on the display memory.

## 3D printed case

A friend of mine is working to a 3D printed case shaped as a Commodore 64 monitor, she plans to sell those on her Etsy shop, I'll put a link here when available. In the meantime, if you create a cool case for this project, ping me: I'll put a link here.
