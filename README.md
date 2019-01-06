# janet

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)

A not-so-smart virtual assistant



# The idea

Janet (based on the AI of Netflix's "The Good Place" series) is a dumb virutal assistant that can help you do stuff by voice.

This is a conceptual fork of [OpenJarvis](https://openjarvis.com), but python-all-the-way.

It uses local hotword detection for both privacy concerns and performance, using [snowboy](https://snowboy.kitt.ai).

Then uses [Bing Speech API](https://azure.microsoft.com/en-us/services/cognitive-services/speech/) for Speech-To-Text recognition.

And finally some python magic.

# How to install

## Setup audio

First, check your audio input/output using alsa's utils :

##### arecord -l

```shell
> arecord -l
**** List of CAPTURE Hardware Devices ****
card 1: AK5371 [AK5371], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

I want to use my AK5371 USB microphone as my input, which is card 1, subdevice 0.

##### aplay -l

```shell
> aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: ALSA [bcm2835 ALSA], device 1: bcm2835 ALSA [bcm2835 IEC958/HDMI]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

Here i want to use my USB sound card as my output, which is card 1, subdevice 0.

Just create the /etc/asound.conf file and fill it using the aformentionned cards and subdevices:

##### sudo nano /etc/asound.conf

```shell
pcm.!default {
  type asym #  THis is important, it tells alsa that we are not using the same cards
   playback.pcm {
     type plug
     slave.pcm "hw:2,0" # This is the card of my AK5371 USB mic
   }
   capture.pcm {
     type plug
     slave.pcm "hw:1,0" # This is the card of my USB audio card
   }
}
```

## Install


Download and run the install script

*Note : Run it with your current user, not root (except if you use root only).
Sudo will be used to access aptitude and pip packages installation,
but you must be able to read/write the janet/ folder with your user*


### If on a Raspberry Pi :
```bash
wget https://raw.githubusercontent.com/Hereath/janet/master/pi-install.sh
bash pi-install.sh
```

### If on Ubuntu (maybe also debian, not tested though):
```bash
wget https://raw.githubusercontent.com/Hereath/janet/master/ubuntu-install.sh
bash ubuntu-install.sh
```

That's it. It will create a `janet/`folder which will contain all what's needed for janet to run.

*Note: The installation of the various dependancies (aptitude and pip) might take a while depending on your setup.*

## Configuration

You will need to fill the config file (janet.conf) with :

- a working BING API key,

- a model (you can use the one provided `snowboy/janet.pmdl`, which responds to "Hey janet".)

For a example config file, look at the `template-janet.conf` file.


## Starting janet

Just `python janet.py`


## Arduino led Ring

For the arduino part, grab the .ino file in the Neopixel folder, and compile it using the Arduino IDE. The programm requires 2 dependancies that you can download from the IDE :

- `Adafruit_Neopixel `(for the Neopixel control)
- `FreeRTOS` (for the mutex capability)

You must connect the Data In of the Neopixel Ring to PIN 6 of the Arduino (or change it in code).


# Documentation about extensions

Janet supports extensions, that responds to a pattern in the user's command.

e.g. John is asking :

```shell
What is the weather tomorrow ?
```

Janet will try to match this sentence against the patterns written in the configuration file, and will find a match with the pattern :

```
*weather*tomorrow* = python weather.py tomorrow
```

And will launch the associated script, here

```
python weather.py tomorrow
```

The script will check the weather and asks Janet to tell John

```
Tomorrow will be cold, will a low of -1° and a high of 8°
```

## Interactivity of extensions

An extension can communicate with Janet, using stdin/stdout, and be interactive.

An extension can access Janet's builtin functions using special commands :

- `$say Hello` will make Janet convert the payload `Hello` into voice, and echo it out loud
- `$ask How are you ?` will make Janet say the payload `How are you ?` and then wait a vocal response from the user. Janet will convert the speech to text and give it back to the extension
- `$play song.wav` will make Janet play the given audio file.

If needed, you can pass to any extension the written translation of what the user said, using `$question` in the command associated with the pattern :

```
*repeat* = python repeat.py $question
```

would pass whatever the user said to the python script.

Concurrency and ressources access (mic and speaker) between the various extensions and Janet itself are managed by Janet, so you won't have 2 or more extensions accessing the speaker / mic at the same time.
