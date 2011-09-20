"""
Usage:
    python buildPackage.py
"""

from distutils.core import setup

import sys
import os
import re
import platform
import subprocess
import getopt
import shutil
import glob
from datetime import date
from subprocess import call

from sickbeard.version import SICKBEARD_VERSION
######################

pythonMainPy = "SickBeard.py"

name = "SickBeard"
version = SICKBEARD_VERSION # master / myAnime
osVersion = "Unknown"
#gitLastCommit = str(check_output(["git", "rev-parse", "HEAD"])).rstrip()
gitLastCommit = "unknown"
bundleIdentifier = "com.sickbeard.sickbeard"
todayString = date.today().strftime("%y-%m-%d")

# OSX
osxOriginalSpraseImageZip = "osx/template.sickbeard.sparseimage.zip"
osxSpraseImage = "build/template.sickbeard.sparseimage"
osxDmgImage = "osx/sb_osx2.png" # using "" will leave the default image at time of writing this is osx/sb_sb_osx.png
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
    opts, args = getopt.getopt(sys.argv[1:], "", [ 'leaveBuildDir', 'onlyApp', 'dmgBG=', 'py2appArgs=']) #@UnusedVariable
except getopt.GetoptError:
    print "Available options: --dmgBG, --leaveBuildDir, --onlyApp, --py2appArgs"
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
    osxDmg = "dist/" + name + ".dmg" # dmg file name
    volumeName = "%s-%s-%s" % (name , version, todayString) # volume name

    # Check which Python flavour
    apple_py = 'ActiveState' not in sys.copyright

    APP = [pythonMainPy]
    DATA_FILES = ['data',
                  'sickbeard',
                  'lib',
                  ('', glob.glob("osx/resources/*"))]

    OPTIONS = {'argv_emulation': False,
               'iconfile': osxAppIcon,
               'packages':["email"],
               'plist': {'NSUIElement': 1,
                        'CFBundleShortVersionString': version + " " + todayString,
                        'NSHumanReadableCopyright': 'The ' + name + '-Team',
                        'CFBundleIdentifier': bundleIdentifier,
                        'CFBundleVersion' : version + " " + todayString,
                        'CFBundleGetInfoString' : "".join(["Build on: OSX ", osVersion, ". Based on: ", version, "(", gitLastCommit , ")"])
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
            print "Writing new background image. %s ..." % os.path.abspath(osxDmgImage)
            f = open(osxDmgImage, 'rb')
            png = f.read()
            f.close()
            f = open('/Volumes/SickBeard/sb_osx.png', 'wb')
            f.write(png)
            f.close()
        else:
            print "The provided image path is not a file"
    else:
        print "Using default background image"

    # Rename the volumeName
    fp = open('build/mount.log', 'r')
    data = fp.read()
    fp.close()
    m = re.search(r'/dev/(\w+)\s+', data)
    print "Renaming the volume ..."
    volRenameCmd = call(["disktool", "-n", m.group(1), volumeName], stdout=subprocess.PIPE)

    #copy builded app to mounted sparseimage
    print "Copying SickBeard.app ..."
    copyCmd = call(["cp", "-r", "dist/SickBeard.app", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE)

    print "Sleeping 5"
    os.system("sleep 5")
    #Unmount sparseimage
    print "Unmount sparseimage ..."
    unmountCmd = call(["hdiutil", "eject", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE)

    #Convert sparseimage to read only compressed dmg
    print "Convert sparseimage to read only compressed dmg ..."
    convertCmd = call(["hdiutil", "convert", osxSpraseImage, "-format", "UDBZ", "-o", osxDmg], stdout=subprocess.PIPE)

    #Make image internet-enabled
    print "Make image internet-enabled ..."
    enabelInetCmd = call(["hdiutil", "internet-enable", osxDmg], stdout=subprocess.PIPE)

    if not leaveBuild:
        print "Removing build dir ..."
        shutil.rmtree('build')

    print
    print "########################################"
    if not (volRenameCmd and copyCmd and unmountCmd and convertCmd and enabelInetCmd):
        print "App build successful."
        print "DMG is located at %s" % os.path.abspath(osxDmg)
    else:
        print "There was an error somewhere :(", (volRenameCmd , copyCmd , unmountCmd , convertCmd , enabelInetCmd)
    print "########################################"

exit()
