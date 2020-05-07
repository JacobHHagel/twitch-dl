#!/usr/local/bin/python3.7

import sys
import re
from itertools import *
import datetime
from multiprocessing import Pool, Lock
import subprocess
import urllib.request
import argparse
import os
import tempfile
import time

#functions
def parse_delta(inp):
    match = re.match("(\d{2}):(\d{2}):(\d{2})", inp)
    if not match:
        sys.exit("Error with date input " + inp + ". Format is hh:mm:ss.")
    hh, mm, ss = match.groups()
    return datetime.timedelta(hours=int(hh), minutes=int(mm), seconds=int(ss)).total_seconds()


def download_file(tup):
    url, target = tup
    with open(target, "wb") as f:
        b = urllib.request.urlopen(url).read()
        f.write(b)
        return len(b)

#parse args
parser = argparse.ArgumentParser()
parser.add_argument("link", help='twitch vod to download')
parser.add_argument("-s", "--start", help="only download from this time")
parser.add_argument("-e", "--end", help="only download up to this time")
parser.add_argument("-f", "--format", help="youtube-dl -f parameter") 
parser.add_argument("-o", "--outfile", help="output file name")
args = parser.parse_args()

#parse start and end
if args.start:
    time_from = parse_delta(args.start)
else:
    time_from = None
if args.end:
    time_to = parse_delta(args.end)
else:
    time_to = None

#get m3u8 file.
ydl = ["youtube-dl", '-g', args.link]
if args.format:
    ydl.extend(["-f", args.format])

res = subprocess.run(ydl, capture_output=True)
m3u8_link = str(res.stdout, 'utf-8')
if not re.match('^http', m3u8_link):
    sys.exit('unable to find playlist file.')

baseurl = re.sub("(.*)/.*?.m3u8", '\\1/', m3u8_link).strip()
print(baseurl)
playlist_text = str(urllib.request.urlopen(m3u8_link).read(), 'utf-8')

#get the parts to download
playlist = []
playlist_time = 0
segments = re.findall("EXTINF:([\d\.]+),\n(\d+.ts)", playlist_text)
for segment_length, filename in segments:
    length = float(segment_length)
    playlist.append((playlist_time, length, filename))
    playlist_time += length

from_items = dropwhile(lambda x: time_from and time_from > x[0], playlist)
to_items = list(takewhile(lambda x : (not time_to) or time_to >= x[0] + x[1], from_items))

#download the parts
n_complete = 0
bits_down = 0
start = time.time()

with tempfile.TemporaryDirectory() as tmpdir:
    files_to_download = list(
        (baseurl + name, os.path.join(tmpdir, name))
        for s, l, name in to_items
    )

    with Pool(5) as pool:
        async_result = pool.imap_unordered(download_file, files_to_download)
        for res in async_result:
            n_complete += 1
            bits_down += (8 * res)
            delta_s = time.time() - start
            mbps = bits_down / delta_s / 1_000_000
            prog_percent = n_complete / len(files_to_download) * 100
            sys.stderr.write("\r")
            sys.stderr.write(f'Progress: {prog_percent:.4}% @ {mbps:.4} mbps  ')
            if (n_complete == len(files_to_download)):
                sys.stderr.write(os.linesep)

    if args.outfile:
        filename = args.outfile
    else:
        filename = args.link.split("/")[-1] + ".mp4"
    with tempfile.NamedTemporaryFile("w") as tmpfile:
        outfiles = os.linesep.join("file " + outfile for _, outfile in files_to_download)
        tmpfile.write(outfiles + os.linesep)
        tmpfile.flush()
        ffmpeg = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                tmpfile.name,'-c', 'copy', filename
            ]
        print(ffmpeg)
        subprocess.run(ffmpeg)
