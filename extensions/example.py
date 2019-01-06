import sys

# Say something through the spakers
print "$say Bonjour, mon nom est Jarvis !"

# Ask something to the user
print "$ask Comment allez-vous ?"

#read reply
line = sys.stdin.readline()

# Reply accordingly
if 'super' in line:
    print "$say Super ! Moi aussi !"
elif 'nul' in line:
    print "$say je ne me sens pas bien non plus..."

# Control NeoPixel (set it off)
print "$neopixel 0"

# Play a sound
#print "$play path/to/song.wav"
