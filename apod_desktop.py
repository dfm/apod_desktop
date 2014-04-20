#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import hashlib
import logging
import requests
import subprocess

# Make sure that the APOD directory exists.
basedir = os.path.expanduser(os.path.join("~", ".apod"))
try:
    os.makedirs(basedir)
except os.error:
    pass

# Install the launchd script.
script = os.path.expanduser("~/Library/LaunchAgents/io.dfm.apod_desktop.plist")
if "--install" in sys.argv:
    plist = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
                           "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>KeepAlive</key>
        <false/>
        <key>Label</key>
        <string>io.dfm.apod_desktop</string>
        <key>RunAtLoad</key>
        <true/>
        <key>Program</key>
        <string>{program}</string>
        <key>StandardOutPath</key>
        <string>{logfile}</string>
        <key>StandardErrorPath</key>
        <string>{logfile}</string>
        <key>StartCalendarInterval</key>
        <dict>
            <key>Hour</key>
            <integer>00</integer>
            <key>Minute</key>
            <integer>30</integer>
        </dict>
    </dict>
    </plist>
    """.format(
        program=os.path.abspath(__file__),
        logfile=os.path.expanduser(os.path.join(basedir, "apod_desktop.log")),
    )

    # Save the script.
    with open(script, "w") as f:
        f.write(plist)

    # Load the launchd script.
    subprocess.check_call(["launchctl", "load", script])
    sys.exit(0)

if "--uninstall" in sys.argv:
    subprocess.check_call(["launchctl", "unload", script])
    sys.exit(0)

# Get the HTML page.
r = requests.get("http://apod.nasa.gov/apod/astropix.html")
if r.status_code != requests.codes.ok:
    logging.error("Couldn't fetch APOD HTML page")
    sys.exit(1)

# Parse the image URL.
g = re.findall(r"<IMG SRC=\"image/(.+)\"", r.text)
if not len(g):
    logging.error("Couldn't parse APOD image URL")
    sys.exit(2)

# Create the hashed image name and check for existence.
ext = os.path.splitext(g[0])[1].lower()
if ext not in [".png", ".jpg", ".jpeg"]:
    logging.error("Invalid image extension")
    sys.exit(3)

fn = os.path.join(basedir, hashlib.md5(g[0]).hexdigest() + ext)
if not os.path.exists(fn):
    # Download the image.
    r = requests.get("http://apod.nasa.gov/apod/image/{0}".format(g[0]))
    if r.status_code != requests.codes.ok:
        logging.error("Couldn't download APOD image")
        sys.exit(4)

    # Save the image file.
    with open(fn, "wb") as f:
        f.write(r.content)
else:
    logging.info("Image file {0} exists".format(fn))

# Set the Desktop image.
subprocess.check_call("""
/usr/bin/osascript<<END
    tell application "Finder"
        set desktop picture to POSIX file "{0}"
    end tell
END""".format(fn), shell=True)
