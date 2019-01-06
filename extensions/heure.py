#!/usr/bin/python

import datetime

date = datetime.datetime.now().time()
heure = date.hour
minutes = date.minute

print "$say Il est ", heure, "heures et ", minutes, "minutes"
