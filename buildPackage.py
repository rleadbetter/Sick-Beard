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
from subprocess import call, check_output

from sickbeard.version import SICKBEARD_VERSION
######################

pythonMainPy = "SickBeard.py"

name = "SickBeard"
version = SICKBEARD_VERSION # master / myAnime
osVersion = "Unknown"
gitLastCommit = str(check_output(["git", "rev-parse", "HEAD"])).rstrip()
bundleIdentifier = "com.sickbeard.sickbeard"

# OSX
osxOriginalSpraseImageZip = "osx/template.sickbeard.sparseimage.zip"
osxSpraseImage = "build/template.sickbeard.sparseimage"

#####################

os.system('rm -rf build dist') # remove old build stuff
os.system("mkdir build")# create tmp build dir

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
    nameOS = name + "-OSX"
    osxDmg = "dist/" + nameOS + ".dmg" # dmg file name
    volumeName = nameOS # volume name

    # Check which Python flavour
    apple_py = 'ActiveState' not in sys.copyright

    APP = [pythonMainPy]
    DATA_FILES = ['data',
                  'sickbeard',
                  'cache',
                  'lib']

    OPTIONS = {'argv_emulation': False,
               'iconfile': 'osx/head-hq.icns',
               'plist': {'NSUIElement': 0,
                        'CFBundleShortVersionString': name + " " + version + " " + gitLastCommit,
                        'NSHumanReadableCopyright': 'The ' + name + '-Team',
                        'CFBundleIdentifier': bundleIdentifier,
                        'CFBundleVersion' : gitLastCommit,
                        'CFBundleGetInfoString' : "".join(["Build on: OSX ", osVersion, ". Based on: ", version, "(", gitLastCommit , ")"])
                        }
               }

    sys.argv.append("py2app")
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
    print
    print "########################################"
    print "Build finished. Creating DMG"
    print "########################################"
    # unzip template sparse image
    check_output(["unzip", osxOriginalSpraseImageZip, "-d", "build"])

    # mount sparseimage and modify volumeName label
    os.system("hdiutil mount %s | grep /Volumes/SickBeard >build/mount.log" % (osxSpraseImage))
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

    print
    print "########################################"
    if not (volRenameCmd and copyCmd and unmountCmd and convertCmd and enabelInetCmd):
        print "App build successful."
        print "DMG is located at %s" % os.path.abspath(osxDmg)
    else:
        print "There was an error somewhere :(", (volRenameCmd , copyCmd , unmountCmd , convertCmd , enabelInetCmd)
    print "########################################"

exit()
