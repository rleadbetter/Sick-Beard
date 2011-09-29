# coding=UTF-8
"""
Usage:
    python buildPackage.py
"""

from distutils.core import setup

import sys
import os
import re
import platform
import getopt
import shutil
import glob
from datetime import date
import subprocess
from subprocess import call, Popen

from sickbeard.version import SICKBEARD_VERSION
######################

pythonMainPy = "SickBeard.py"

name = "SickBeard"
version = SICKBEARD_VERSION # master / myAnime
majorVersion = "alpha"
build = version.split(" ")[1]
osVersion = "Unknown"
gitLastCommit = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).communicate()[0].strip()
bundleIdentifier = "com.sickbeard.sickbeard"
todayString = date.today().strftime("%y-%m-%d")
thisYearString = date.today().strftime("%Y")

# OSX
osxOriginalSpraseImageZip = "osx/template.sickbeard.sparseimage.zip"
osxSpraseImage = "build/template.sickbeard.sparseimage"
osxDmgImage = "" # using "" will leave the default image at time of writing this is osx/sb_sb_osx.png
osxAppIcon = "osx/sickbeard.icns"
# mode
leaveBuild = False
onlyApp = False
py2AppArgs = ['py2app']

#####################
print "Removing old build dirs ..."
os.system('rm -rf build dist') # remove old build stuff
os.system("mkdir build") # create tmp build dir

#####################

try:
    opts, args = getopt.getopt(sys.argv[1:], "", [ 'leaveBuildDir', 'onlyApp', 'dmgbg=', 'py2appArgs=']) #@UnusedVariable
except getopt.GetoptError:
    print "Available options: --dmgbg, --leaveBuildDir, --onlyApp, --py2appArgs"
    exit(1)

for o, a in opts:
    if o in ('--dmgbg'):
        osxDmgImage = a

    if o in ('--leaveBuildDir'):
        leaveBuild = True

    if o in ('--onlyApp'):
        onlyApp = True

    if o in ('--py2appArgs'):
        py2AppArgs = py2AppArgs + a.split()

#####################

# mac osx
if sys.platform == 'darwin':
    try:
        import py2app
    except ImportError:
        print 'you need py2app to build a mac app'
        exit(1)

    osVersion = platform.mac_ver()[0]
    osVersionMayor, osVersionMinor, osVersionMicro = osVersion.split(".")
    volumeName = "%s-osx-%s-build%s" % (name , majorVersion, build) # volume name
    osxDmg = "dist/%s.dmg" % (volumeName) # dmg file name
    #SickBeard-win32-alpha-build489.zip
    # Check which Python flavour
    apple_py = 'ActiveState' not in sys.copyright

    APP = [pythonMainPy]
    DATA_FILES = ['data',
                  'sickbeard',
                  'lib',
                  ('', glob.glob("osx/resources/*"))]
    _NSHumanReadableCopyright = "(c) %s The %s-Team\nBuild on: OSX %s\nBased on: %s (%s)\nPython used & incl: %s" % (thisYearString, name , osVersion, version, gitLastCommit , str(sys.version))

    OPTIONS = {'argv_emulation': False,
               'iconfile': osxAppIcon,
               'packages':["email"],
               'plist': {'NSUIElement': 1,
                        'CFBundleShortVersionString': "build " + build,
                        'NSHumanReadableCopyright': _NSHumanReadableCopyright,
                        'CFBundleIdentifier': bundleIdentifier,
                        'CFBundleVersion' : version + " " + todayString
                        }
               }
    if len(sys.argv) > 1:
        sys.argv = [sys.argv[1]]
    for x in py2AppArgs:
        sys.argv.append(x)
    print
    print "########################################"
    print "Building App"
    print "########################################"
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
    if onlyApp:
        print
        print "########################################"
        print "STOPING here you only wanted the App"
        print "########################################"
        exit()

    print
    print "########################################"
    print "Build finished. Creating DMG"
    print "########################################"
    # unzip template sparse image
    call(["unzip", osxOriginalSpraseImageZip, "-d", "build"])

    # mount sparseimage and modify volumeName label
    os.system("hdiutil mount %s | grep /Volumes/SickBeard >build/mount.log" % (osxSpraseImage))

    # Select OSX version specific background image
    # Take care to preserve the special attributes of the background image file
    if osxDmgImage:
        if os.path.isfile(osxDmgImage):
            print "Writing new background image. %s ..." % os.path.abspath(osxDmgImage),
            # we need to read and write the data because otherwise we would lose the special hidden flag on the file
            f = open(osxDmgImage, 'rb')
            png = f.read()
            f.close()
            f = open('/Volumes/SickBeard/sb_osx.png', 'wb')
            f.write(png)
            f.close()
            print "ok"
        else:
            print "The provided image path is not a file"
    else:
        print "# Using default background image"

    # Rename the volumeName
    fp = open('build/mount.log', 'r')
    data = fp.read()
    fp.close()
    m = re.search(r'/dev/(\w+)\s+', data)
    print "Renaming the volume ...",
    if not call(["disktool", "-n", m.group(1), volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    #copy builded app to mounted sparseimage
    print "Copying SickBeard.app ...",
    if not call(["cp", "-r", "dist/SickBeard.app", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    #copy scripts to mounted sparseimage
    print "Copying Scripts ...",
    if not call(["cp", "-r", "autoProcessTV/autoProcessTV.cfg.sample", "/Volumes/%s/Scripts/autoProcessTV.cfg" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok",
    else:
        print "ERROR",
    if not call(["cp", "-r", "autoProcessTV/autoProcessTV.py", "/Volumes/%s/Scripts/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok",
    else:
        print "ERROR",
    if not call(["cp", "-r", "autoProcessTV/sabToSickBeard.py", "/Volumes/%s/Scripts/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    print "# Sleeping 5"
    os.system("sleep 5")
    #Unmount sparseimage
    print "Unmount sparseimage ...",
    if not call(["hdiutil", "eject", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    #Convert sparseimage to read only compressed dmg
    print "Convert sparseimage to read only compressed dmg ...",
    if not call(["hdiutil", "convert", osxSpraseImage, "-format", "UDBZ", "-o", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    #Make image internet-enabled
    print "Make image internet-enabled ...",
    if not call(["hdiutil", "internet-enable", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"

    if not leaveBuild:
        print "Removing build dir ...",
        shutil.rmtree('build')
        print "ok"

    print
    print "########################################"
    print "App build successful."
    print "DMG is located at %s" % os.path.abspath(osxDmg)
    print "########################################"

exit()
