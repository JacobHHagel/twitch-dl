#!/usr/local/bin/python3.7

import sys
import re
from itertools import *
import datetime

if len(sys.argv) <= 1:
    sys.exit("Need an m3u8 file.")

with open(sys.argv[1], "r") as f:
    playlist_text = f.read()

playlist = []
time = 0
for segment_length, filename in re.findall("EXTINF:([\d\.]+),\n(\d+.ts)", playlist_text):
    length = float(segment_length)
    playlist.append((time, length, filename))
    time += length

def parse_delta(inp):
    match = re.match("(\d{2}):(\d{2}):(\d{2})", inp)
    if not match:
        sys.exit("Error with date input " + inp + ". Format is hh:mm:ss.")
    hh, mm, ss = match.groups()
    return datetime.timedelta(hours=int(hh), minutes=int(mm), seconds=int(ss)).total_seconds()

if len(sys.argv) > 2:
    time_from = parse_delta(sys.argv[2])
else:
    time_from = 0
if len(sys.argv) > 3:
    time_to = parse_delta(sys.argv[3])
else:
    time_to = time

from_items = dropwhile(lambda x: time_from > x[0], playlist)
to_items = takewhile(lambda x : time_to >= x[0] + x[1], from_items)

for s, l, name in to_items:
    print(name)
