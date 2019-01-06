# -*- coding: utf-8 -*-

###########
# Imports #
###########
import sys  # system info and path modif
import snowboy.snowboydecoder as decoder  # hotword recognition
import uuid  # UUID creation
import ConfigParser  # configuration get/set
import datetime  # datetime manipulation
import os  # path and shell commands
import requests  # POST requests
import json  # JSON decoding
import re  # regular expressions
import threading  # multi-thread operations
import time  # sleep operations
import serial  # Serial port com
import signal  # SIG catching
import logging  # Loggind duty
import subprocess  # run other process
import shlex  # args parsing for subprocess
import pyaudio  # audio work
import wave  # .wav work

###############
# GLOBAL VARS #
###############

OFF = 0
STANDBY = 1
LOADING = 2
LISTENING = 3
DOING = 4
SAYING = 5
ERROR = 6
MORE_LIGHT = "+"
LESS_LIGHT = "-"

root = os.path.dirname(os.path.abspath(__file__))
configFilePath = root + "/janet.conf"  # Where is the config file
verbosity = logging.DEBUG
dongFile = root+"/snowboy/resources/dong.wav"
dingFile = root+"/snowboy/resources/ding.wav"


#############################################
# Janet, the not-so-smart virtual assistant #
#############################################

class Janet(object):
    """
    A not-so-smart virtual assistant.
    It is supposed to help you do stuff by voice, but don't trust it. #Skynet
    """

    def __init__(self):
        """
        Reads the config file,
        Sets some basic variables,
        Creates the logger,
        Launch all the startup tasks.
        """

        # Logging configuration
        self.logger = logging.getLogger("Janet")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s'))
        self.logger.addHandler(ch)

        # Signal catcher for clean quit
        signal.signal(signal.SIGINT, self.signal_watchdog)
        signal.signal(signal.SIGTERM, self.signal_watchdog)

        # Semaphores for ressources allocation
        self.userLock = threading.RLock()  # The user is a ressource :D
        self.neopixelLock = threading.RLock()  # Avoid multiple calls to NeoPixel

        # Vars
        self.neopixel = False
        self.interrupted = False
        self.bingKey = None
        self.token = None
        self.validity = None
        self.model = None
        self.splitter_word = None
        self.language = None
        self.detector = None
        self.current_command = ""
        self.available_commands = {}
        self.sentences = {}
        self.tasks_objects = []

        # Call to init functions
        self.config = ConfigParser.ConfigParser()  # Config Parser object
        task = threading.Thread(target=self.start_arduino_Serial)
        task.start()
        self.get_config()
        self.check_token_validity()
        self.get_sentences()

        self.get_commands()
        self.get_tasks()

        task.join()
        self.logger.info("Janet is up !")

    def get_sentences(self):
        """

        """
        self.logger.debug("Loading sentences..")
        self.config.read(configFilePath)
        for each in self.config._sections["Sentences"]:
            if "__" not in each:
                self.sentences[each] = self.config._sections["Sentences"][each]

    def get_config(self):
        """
        Get Janet's config from the config file

        :return:
        """
        # Load configuration variables
        if not os.path.exists(configFilePath):
            self.logger.error("No config file detected with provided path : "+configFilePath)
            exit(1)
        try:
            self.config.read(configFilePath)
            self.bingKey = self.config.get('Global', 'bingKey')
            if self.bingKey is "":
                self.logger.debug("Bing API key is empty, please enter a valid one before goign any further.")
                self.interrupted = True
                exit(0)

            self.token = self.config.get('Global', 'token')
            self.validity = self.config.get('Global', 'validity')
            self.model = self.config.get('Global', 'model')
            if self.model is "" or not os.path.exists(self.model):
                self.logger.debug("Provided hotword model is empty or not valid, please select a valid hotword model")
                self.interrupted = True
                exit(0)

            self.splitter_word = self.config.get('Global', 'splitter_word')
            self.language = self.config.get('Global', 'language')
        except Exception:
            self.logger.error("Error in config file")
            exit(1)

    def get_commands(self):
        """
        Get all the commands (or triggers) from the config file and add them
        to janet's dict
        :return:
        """

        self.logger.debug("Loading commands from config ")
        # Load commands
        self.config.read(configFilePath)
        for each in self.config._sections["Commands"]:
            if "__" not in each:
                trigger = each.replace("*", "(.*)")
                self.available_commands[trigger] = self.config._sections["Commands"][each]

    def get_tasks(self):
        """
        Get all the startup tasks from the config file and launch them in individual threads
        :return:
        """
        self.logger.debug("Starting up tasks")
        self.config.read(configFilePath)
        for each in self.config._sections["Tasks"]:
            if "__" not in each:
                self.execute(self.config._sections["Tasks"][each])

    def save_values(self, keys_values):

        """
        Updates the new values passed as a dict to the config file

        param: keys_values: The dict to save to the config file
        """
        self.logger.debug("Saving values to config")
        for each in keys_values:
            self.config.set("Global", each, keys_values[each])
        with open(configFilePath, 'wb') as configfile:
            self.config.write(configfile)

    def start_arduino_Serial(self):
        """
        Create a Serial connection to the arduino via USB
        :return:
        """
        try:
            with self.neopixelLock:
                self.neopixel = serial.Serial('/dev/ttyUSB0', 9600)
                self.logger.debug("Connected to arduino, initializing connection..")
                time.sleep(2)
                self.update_led_ring_state(LOADING)
                time.sleep(3)
                self.update_led_ring_state(STANDBY)
        except:
            self.neopixel = False
            self.logger.debug("Unable to connect to Neopixel")

    def update_led_ring_state(self, state):
        """
        Update the led ring with the provided state

        :param state: The state to put the led ring in
        (see Global vars for list of supported states)
        :return:
        """
        if self.neopixel is not False:
            with self.neopixelLock:
                self.logger.debug("Updating LED ring : " + str(state))
                self.neopixel.write(str(state))

    def check_token_validity(self):
        """
        A Bing API Token is only valid for 10 minutes and must be renewed for further transactions

        Checks if the token is older than 10 mins, and renew it if it is

        :return: Nothing
        """
        # Get fresh info
        self.get_config()
        now = datetime.datetime.now().strftime("%s")

        # If token dont exists or older than 10 mins
        if self.token is '' or int(self.validity) <= int(now):
            self.logger.debug("Token either not set or too old, lets get a new fresh one !")
            endpoint = "https://api.cognitive.microsoft.com/sts/v1.0/issueToken"
            bing_headers = {'Ocp-Apim-Subscription-Key': self.bingKey}
            try:
                resp = requests.post(endpoint, headers=bing_headers)
                self.token = resp.content
                self.logger.debug("Token renewed !")
                self.validity = datetime.datetime.now() + datetime.timedelta(minutes=9, seconds=40)
                self.save_values({"token": self.token, "validity": self.validity.strftime("%s")})
            except Exception as e:
                self.logger.error("Error while getting token : " + str(e.args))


    def listen_4_a_command(self):
        """
        Uses sox to listen a command from the user,
        using sound level thresholds to only grab the command,
        and timeout to stop an infinite listening

        :return:
        """
        self.logger.debug('stopping snowboy stream')
        self.stop_snowboy_stream()
        self.logger.debug("Listening for a command..")
        self.play_audio_file(dingFile)
        self.update_led_ring_state(LISTENING)

        # timeout 10 rec -V0 -q -r 16000 -c 1 -b 16 cmd.wav gain 1 silence 1 0.0 2% 1 1.0 2% pad 0.2 0.2
        if sys.platform == "darwin":
            cmd = ""
        else:
            cmd = "timeout 8 " # Kill if still running after 10 secs..
        cmd += "rec "  # Rec to record audio
        cmd += "-V0 -q "  # for a quiet output
        cmd += "-r 16000 -c 1 -b 16 "  # rate of 16KHz, 1 Channel , 16 bit depth
        cmd += "cmd.wav"  # Where to put it
        cmd += " gain 1 "  # Gain to add to the recorded sound
        cmd += "silence 1 0.0 2% 1 1.0 2% "  # For rec to record only the command and avoid silence
        cmd += "pad 0.2 0.2" # Add a bit of blank at both ends to improve last syllab recognition

        os.system(cmd)
        self.play_audio_file(dongFile)
        self.update_led_ring_state(STANDBY)
        self.logger.debug("Command has been recorded, starting back snwoboy")
        self.resume_snowboy_stream()

    def convert_Speech_2_text(self):
        """
        Converts a given .wav file to a speakable string

        Uses Bing Speech API (API Key needed)
        :return: True if the conversion was successful, False otherwise
        """
        self.check_token_validity()
        self.logger.debug("Sending to bing for translation ! ")
        endpoint = 'https://speech.platform.bing.com/recognize/query'
        params = {'scenarios': 'ulm',
                  'appid': 'D4D52672-91D7-4C74-8AD8-42B1D98141A5',
                  'locale': self.language,
                  'version': '3.0',
                  'format': 'json',
                  'instanceid': 'E043E4FE-51EF-4B74-8133-B728C4FEA8AA',
                  'requestid': uuid.uuid4(),
                  'device.os': 'linux'}
        content_type = "audio/wav; codec=""audio/pcm""; samplerate=16000"

        headers = {'Authorization': 'Bearer ' + self.token,
                   'Content-Type': content_type}

        try:
            resp = requests.post(endpoint,
                             params=params,
                             data=open("cmd.wav").read(),
                             headers=headers)

            os.remove("cmd.wav")
            data = json.loads(resp.content)
            self.current_command = data["results"][0]["name"]
            return True
        except Exception as e:
            self.current_command = "None"
            self.logger.debug("Error while connecting..")
            return False

    def convert_Text_2_Speech(self, message):
        """
        Uses Bing Speech API to convert a text to voice

        :param message: The text message to be translated to speech

        :return:
        """
        self.check_token_validity()
        self.logger.debug("Sending text to bing for speech")
        endpoint = "https://speech.platform.bing.com/synthesize"
        headers = {
            "Content-type": "application/ssml+xml",
            "Authorization": "Bearer " + self.token,
            "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
            "X-Search-AppId": "07D3234E49CE426DAA29772419F436CA",
            "X-Search-ClientID": "1ECFAE91408841A480F00935DC390960",
            "User-Agent": "Janet"
        }

        params = "<speak version='1.0' xml:lang='"+self.language+"'>"

        # Language selection (default is en_US)
        if "fr" in self.language.lower():
            params += "<voice xml:gender='Female' name='Microsoft Server Speech Text to Speech Voice (fr-FR, HortenseRUS)'>"
        elif 'gb' in self.language.lower():
            params += "<voice xml:gender='Female' name='Microsoft Server Speech Text to Speech Voice (en-GB, HazelRUS)'>"
        else:
            params += "<voice xml:gender='Female' name='Microsoft Server Speech Text to Speech Voice (en-US, ZiraRUS)'>"

        params += "<prosody pitch='high' contour='(20%,+40%) (90%,-30%)' >"
        params += message + "</prosody></voice></speak>"
        try:
            resp = requests.post(endpoint, data=params, headers=headers)
            self.update_led_ring_state(SAYING)
            with open("voice.wav", 'w+') as f:
                f.write(resp.content)
            self.play_audio_file("voice.wav")
            os.remove("voice.wav")
        except Exception as e:
            self.logger.debug(str(e.args))
            self.logger.debug("Transaction status : "+resp.reason)

    def play_audio_file(self, filename):
        """As the name implies, it plays the given audio file..

        :param str fname: wave file name
        :return: None
        """
        if sys.platform == "darwin":
            os.system("afplay "+filename)
        else:
            os.system("aplay "+filename)

    def say(self, message):
        """

        :param message: The message to say
        :return:
        """
        self.logger.debug("Saying "+message)
        self.convert_Text_2_Speech(message)
        self.update_led_ring_state(STANDBY)

    def execute(self, command):
        """
        Create a separate thread to run a command whithout blocking the main thread

        :param command: the command to be executed
        :return:
        """
        id = "Task-" + str(len(self.tasks_objects) + 1)
        task = threading.Thread(target=self.threaded_task, args=(id, command))
        task.start()

    def threaded_task(self, id, command):
        """
        Handler for the threaded task.
        Creates and runs the subprocess

        Communicate with it using the stdin/stdout of the process

        :param id: The id of the task, used for logging purpose
        :param command: the command to be run
        :return:
        """

        args = shlex.split(command)
        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   stdin=subprocess.PIPE,
                                   universal_newlines=True)
        self.tasks_objects.append(process)

        # Poll process for new output
        while True:
            nextline = process.stdout.readline()
            nextline = nextline.replace("\n", "")
            nextline = nextline.strip()
            if nextline == '' and process.poll() is not None:
                break

            # Grant acess to mic - STT capabilities
            if "$ask" in nextline:
                question = nextline.replace("$ask", "")
                with self.userLock:
                    self.say(question)
                    self.listen_4_a_command()
                    correct_reply = self.convert_Speech_2_text()
                    if not correct_reply:
                        self.say(self.sentences["not_understood"] + question)
                        self.listen_4_a_command()
                        self.convert_Speech_2_text()

                    process.stdin.write(self.current_command.encode('utf-8') + "\n")
                    process.stdin.flush()
                self.update_led_ring_state(STANDBY)

            # Grant access to Text-to-speech capabilities
            elif "$say" in nextline:
                voice = nextline.replace("$say ", "")
                with self.userLock:
                    self.say(voice)

            # Grant access to play_audio_file capabilities
            elif "$play" in nextline:
                path = nextline.replace("$play ", "")
                with self.userLock:
                    self.play_audio_file(path)

            # Grant access to update_led_ring_state capabilities
            elif "$neopixel" in nextline:
                state = nextline.replace("$neopixel ", "")
                self.logger.debug("updating neopixel state to "+state)
                self.update_led_ring_state(state)

    def stop_snowboy_stream(self):
        """
        Closes the audio stream from the mic to snwoboy to avoid ressources starvation
        for Janet

        Happens before Janet listens to a command,
        otherwise would cause a 'Device busy' error
        """
        self.detector.stream_in.close()
        self.detector.audio.terminate()

    def resume_snowboy_stream(self):
        """
        Resumes audio stream from the mic to snowboy for hotword detection

        Happens after Janet is done listening to a command
        """
        self.detector.audio = pyaudio.PyAudio()
        self.detector.stream_in = self.detector.audio.open(
            input=True, output=False,
            format=self.detector.audio.get_format_from_width(
                self.detector.detector.BitsPerSample() / 8),
            channels=self.detector.detector.NumChannels(),
            rate=self.detector.detector.SampleRate(),
            frames_per_buffer=2048,
            stream_callback=self.detector.audio_callback)
        self.detector.stream_in.start_stream()

    def understand_command(self):
        """

        :return:
        """
        current_command_str = self.current_command.encode('utf-8')
        self.logger.info("Request : " + current_command_str)


        if self.splitter_word in current_command_str:
            list_of_commands = current_command_str.split(self.splitter_word)
        else:
            list_of_commands = [current_command_str]

        command_has_trigger = False
        for one_command in list_of_commands:
            for each in self.available_commands:
                if re.search(each, one_command):
                    command_has_trigger = True
                    if "$question" in self.available_commands[each]:
                        command = self.available_commands[each].replace("$question", '"' + one_command + '"')
                    else:
                        command = self.available_commands[each]
                    self.logger.debug("Command executed : " + command)
                    # status, output = os.system(self.available_commands[each])
                    self.execute(command)
                    break
        if not command_has_trigger:
            self.logger.debug("No command is associated with : " + current_command_str)
            self.say(self.sentences["no_command"] + current_command_str)

    def failed_recognition(self):
        """
        Routine called when the voice recognition failed
        i.e. the user's input wasn't words

        :return:
        """
        self.update_led_ring_state(ERROR)
        time.sleep(0.5)
        self.logger.warning("Unable to get transcription")
        self.say(self.sentences["error_trad"])
        self.update_led_ring_state(STANDBY)

    def hotword_has_been_detected(self):
        """
        Called when a hotword has been detected by snowboy

        Calls other routines in waterfall
        :return:
        """
        # If privacy bit is set, don't do anything
        self.logger.info("Janet was called !")
        with self.userLock:
            self.listen_4_a_command()
            recognized = self.convert_Speech_2_text()
            if recognized:
                self.understand_command()
            else:
                self.failed_recognition()
        self.logger.info("Listening..")
        self.update_led_ring_state(STANDBY)

    def signal_watchdog(self, signal, frame):
        """
        Catch a SIGINT or SIGTERM to properly shutdown Janet before quitting

        :param signal:
        :param frame:
        :return:
        """

        # let's quit
        self.logger.debug("Quitting..")
        self.interrupted = True
        with self.userLock:
            self.say(self.sentences["quit"])

        # Turn off Neopixel
        self.update_led_ring_state(OFF)
        if self.neopixel is not False:
            self.neopixel.close()

        # Quit
        self.logger.info("Quitting Janet !")
        exit(0)

    def interrupt_callback(self):
        return self.interrupted

    def start(self):
        """
        Wrapper around snowboy's detector()

        :return:
        """
        with self.userLock:
            self.say(self.sentences["startup"])

        self.detector = decoder.HotwordDetector(root + "/" + self.model, sensitivity=0.4)
        self.detector.start(detected_callback=self.hotword_has_been_detected,
                            interrupt_check=self.interrupt_callback,
                            sleep_time=0.03)


if __name__ == '__main__':
    # Let's initialize !
    HeyIamJanet = Janet()
    # Say my name
    HeyIamJanet.start()
