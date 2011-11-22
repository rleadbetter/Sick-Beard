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

######################
# helper functions
def writeSickbeardVersionFile(version):
    # Create a file object:
    # in "write" mode
    versionFile = open(os.path.join("sickbeard", "version.py"), "w")
    sbVersionVarName = "SICKBEARD_VERSION"
    content = '%s = "%s"\n' % (sbVersionVarName, version)
    # Write all the lines at once:
    versionFile.writelines(content)
    versionFile.close()
    # now lets try to import the written file
    from sickbeard.version import SICKBEARD_VERSION
    if SICKBEARD_VERSION == version:
        return True
    else:
        return False

def getNiceOSString():
    if sys.platform == 'darwin':
        return "OSX"
    else:
        return "Win32"

def buildWIN():
    return False

def buildOSX(buildParams):
    # OSX constants
    bundleIdentifier = "com.sickbeard.sickbeard" # unique program identifier used on osx 
    osxOriginalSpraseImageZip = "osx/template.sickbeard.sparseimage.zip" # 
    osxSpraseImage = "build/template.sickbeard.sparseimage"
    osxAppIcon = "osx/sickbeard.icns" # the app icon location
    osVersion = platform.mac_ver()[0]
    osVersionMayor, osVersionMinor, osVersionMicro = osVersion.split(".")
    volumeName = "%s-%s-%s" % (buildParams['name'] , buildParams['osName'] , buildParams['build']) # volume name
    osxDmg = "dist/%s.dmg" % (volumeName) # dmg file name/path

    try:
        import py2app
    except ImportError:
        print 'ERROR you need py2app to build a mac app http://pypi.python.org/pypi/py2app/'
        return False

    #SickBeard-win32-alpha-build489.zip
    # Check which Python flavour
    apple_py = 'ActiveState' not in sys.copyright

    APP = [buildParams['mainPy']]
    DATA_FILES = ['data',
                  'sickbeard',
                  'lib',
                  ('', glob.glob("osx/resources/*"))]
    _NSHumanReadableCopyright = "(c) %s The %s-Team\nBuild on: %s %s\nBased on: %s\nPython used & incl: %s" % (buildParams['thisYearString'],
                                                                                                                    buildParams['name'],
                                                                                                                    buildParams['osName'],
                                                                                                                    osVersion,
                                                                                                                    buildParams['gitLastCommit'],
                                                                                                                    str(sys.version))

    OPTIONS = {'argv_emulation': False,
               'iconfile': osxAppIcon,
               'packages':["email"],
               'plist': {'NSUIElement': 1,
                        'CFBundleShortVersionString': buildParams['build'],
                        'NSHumanReadableCopyright': _NSHumanReadableCopyright,
                        'CFBundleIdentifier': bundleIdentifier,
                        'CFBundleVersion' :  buildParams['build']
                        }
               }
    if len(sys.argv) > 1:
        sys.argv = [sys.argv[1]]
    for x in buildParams['py2AppArgs']:
        sys.argv.append(x)

    if buildParams['test']:
        print
        print "########################################"
        print "NOT Building App this was a TEST. Here are the names"
        print "########################################"
        print "volumeName: " + volumeName
        print "osxDmg: " + osxDmg
        print "OPTIONS: " + str(OPTIONS)
        return True

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
    if buildParams['onlyApp']:
        print
        print "########################################"
        print "STOPING here you only wanted the App"
        print "########################################"
        return True

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
    if buildParams['osxDmgImage']:
        if os.path.isfile(buildParams['osxDmgImage']):
            print "Writing new background image. %s ..." % os.path.abspath(buildParams['osxDmgImage']),
            # we need to read and write the data because otherwise we would lose the special hidden flag on the file
            f = open(buildParams['osxDmgImage'], 'rb')
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
        return False

    #copy builded app to mounted sparseimage
    print "Copying SickBeard.app ...",
    if not call(["cp", "-r", "dist/SickBeard.app", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

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
        return False

    print "# Sleeping 5 sec"
    os.system("sleep 5")
    #Unmount sparseimage
    print "Unmount sparseimage ...",
    if not call(["hdiutil", "eject", "/Volumes/%s/" % volumeName], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #Convert sparseimage to read only compressed dmg
    print "Convert sparseimage to read only compressed dmg ...",
    if not call(["hdiutil", "convert", osxSpraseImage, "-format", "UDBZ", "-o", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    #Make image internet-enabled
    print "Make image internet-enabled ...",
    if not call(["hdiutil", "internet-enable", osxDmg], stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        print "ok"
    else:
        print "ERROR"
        return False

    print
    print "########################################"
    print "App build successful."
    print "DMG is located at %s" % os.path.abspath(osxDmg)
    print "########################################"
    return True

def main():
    print
    print "########################################"
    print "Starting..."
    print "########################################"
    
    
    buildParams = {}
    ######################
    # check arguments
    # defaults
    buildParams['test'] = False
    buildParams['nightly'] = False
    # win
    buildParams['py2ExeArgs'] = []
    # osx
    buildParams['onlyApp'] = False
    buildParams['py2AppArgs'] = ['py2app']
    buildParams['osxDmgImage'] = ""

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [ 'test', 'onlyApp', 'nightly', 'dmgbg=', 'py2appArgs=']) #@UnusedVariable
    except getopt.GetoptError:
        print "Available options: --test, --dmgbg, --onlyApp, --nightly, --py2appArgs"
        exit(1)

    for o, a in opts:
        if o in ('--test'):
            buildParams['test'] = True

        if o in ('--nightly'):
            buildParams['nightly'] = True

        if o in ('--dmgbg'):
            buildParams['osxDmgImage'] = a

        if o in ('--onlyApp'):
            buildParams['onlyApp'] = True

        if o in ('--py2appArgs'):
            buildParams['py2AppArgs'] = py2AppArgs + a.split()

    ######################
    # constants
    buildParams['mainPy'] = "SickBeard.py" # this should never change
    buildParams['name'] = "SickBeard" # this should never change
    buildParams['majorVersion'] = "alpha" # one day we will change that to BETA :P

    buildParams['osName'] = getNiceOSString(); # look in getNiceOSString() for default os nice names

    """
    # dynamic build number and date stuff
    tagsRaw = subprocess.Popen(["git", "tag"], stdout=subprocess.PIPE).communicate()[0]
    lastTagRaw = tagsRaw.split("\n")[-2] # current tag e.g. build-###
    tag = lastTagRaw.split("-")[1] # current tag pretty... change according to tag scheme
    """
    # date stuff
    buildParams['thisYearString'] = date.today().strftime("%Y") # for the copyright notice
    buildParams['yearMonth'] = date.today().strftime("%y.%m")
    buildParams['gitLastCommit'] = subprocess.Popen(["git", "describe", "--tag"], stdout=subprocess.PIPE).communicate()[0].strip().split("-")[2] # bet there is a simpler way

    # this is the yy.mm string
    # or for nightlys yy.mm.commit
    buildParams['build'] = buildParams['yearMonth']
    if buildParams['nightly']:
        buildParams['build'] = "%s.%s" % (buildParams['yearMonth'], buildParams['gitLastCommit'])

    # the new SICKBEARD_VERSION string visible to the user and used in the binary package file name
    buildParams['newSBVersion'] = "%s %s" % (buildParams['osName'], buildParams['build'])
    
    print "setting SICKBEARD_VERSION to %s ..." % (buildParams['newSBVersion']),
    if not writeSickbeardVersionFile(buildParams['newSBVersion']):
        print "ERROR"
        print "seams like writing the verision.py file failed. permissions ?"
        print "stopping..."
        exit(1)
    else:
        print "ok"

    #####################
    # clean the build dirs
    if not buildParams['test']:
        print "Removing old build dirs ...",
        # remove old build stuff
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        os.makedirs('build') # create tmp build dir
    #####################
    # os switch
    if sys.platform == 'darwin':
        result = buildOSX(buildParams)
    else:
        result = buildWIN(buildParams)

    if result:
        exit()
    else:
        print "ERROR during build we have failed you"
        exit(1)

if __name__ == '__main__':
    main()

