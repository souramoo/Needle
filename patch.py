#!/usr/bin/env python3
import os, subprocess, tempfile, time, shutil, sys, glob
from distutils.spawn import find_executable

POSIX = False if os.sep is "\\" else True
DEBUG_PROCESS = False

# check if dependencies are there
deperrors = []

def exists(program):
    if find_executable(program) is not None:
        return 0
    deperrors.append(program)
    return 1

if exists("zip") + exists("adb") + exists("java") > 0:
    print(" *** ERROR: Dependencies not satisfied.")
    print("\tPlease make sure you install:\n\t%s" % (deperrors))
    sys.exit(2)

# start adb server before using it otherwise we get an unintended output inside other commands
subprocess.check_output(["adb", "start-server"])

# check if device is connected
devices = subprocess.check_output(["adb", "devices"]).decode("utf-8")

if devices.count('\n') <= 2:
    print(" *** Please connect your device first.")
    sys.exit(0)

if DEBUG_PROCESS:
    print(" *** NOTE: Running in debug mode, WILL NOT ACTUALLY PATCH AND PUSH TO DEVICE")

devices = devices.split('\n')[1:-2]
devices = [a.split("\t")[0] for a in devices]

if len(devices) > 1:
    print("Enter id of device to target:")
    id = input("\t"+("\n\t").join([str(i)+" - "+a for i,a in zip(range(1, len(devices)+1), devices)]) + "\n\n> ")
    chosen_one = devices[int(id)-1]
else:
    chosen_one = devices[0]

print(" *** Selected device " + chosen_one)

print(" *** Device detected! proceeding...")

PREVIOUS_DIR = os.getcwd()
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# pull framework somewhere temporary
dirpath = tempfile.mkdtemp()
os.chdir(dirpath)
print(" *** Working dir: %s" % dirpath)

print(" *** Rooting adbd...")
subprocess.check_call(["adb", "-s", chosen_one, "root"])
subprocess.check_call(["adb", "-s", chosen_one, "wait-for-device"])
subprocess.check_call(["adb", "-s", chosen_one, "remount", "/system"])

print(" *** Pulling framework from device...")
subprocess.check_output(["adb", "-s", chosen_one, "pull", "/system/framework/framework.jar", "."])
shutil.copy2("framework.jar", "framework.jar.backup") # back it up in case things ever go wrong

# disassemble it
print(" *** Disassembling framework...")
subprocess.check_call(["java", "-jar", os.path.join(SCRIPT_DIR, "tools", "baksmali.jar"), "framework.jar", "-o", "classes", "-ls"])

# do the injection
print(" *** Done. Now this won't hurt a bit...")
to_patch = os.path.join("classes", "android", "content", "pm", "PackageParser.smali")
if not os.path.exists(to_patch):
    print(" *** ERROR: The file to patch cannot be found, probably the ROM is odexed.")
    sys.exit(1)

f = open(to_patch, "r")
old_contents = f.readlines()
f.close()

f = open(os.path.join(SCRIPT_DIR, "smali", "fillinsig.smali"), "r")
fillinsig = f.readlines()
f.close()

# add fillinsig method
i = 0
contents = []
already_patched = False
in_function = False
right_line = False
start_of_line = None
done_patching = False
stored_register = "v11"
partially_patched = False

while i < len(old_contents):
    if ";->fillinsig" in old_contents[i]:
        already_patched = True
    if ".method public static fillinsig" in old_contents[i]:
        partially_patched = True
    if ".method public static generatePackageInfo(Landroid/content/pm/PackageParser$Package;[IIJJLjava/util/Set;Landroid/content/pm/PackageUserState;I)Landroid/content/pm/PackageInfo;" in old_contents[i]:
        in_function = True
    if ".method public static generatePackageInfo(Landroid/content/pm/PackageParser$Package;[IIJJLandroid/util/ArraySet;Landroid/content/pm/PackageUserState;I)Landroid/content/pm/PackageInfo;" in old_contents[i]:
        in_function = True
    if ".method public static generatePackageInfo(Landroid/content/pm/PackageParser$Package;[IIJJLjava/util/HashSet;Landroid/content/pm/PackageUserState;I)Landroid/content/pm/PackageInfo;" in old_contents[i]:
        in_function = True
    if ".method public static generatePackageInfo(Landroid/content/pm/PackageParser$Package;[IIJJLjava/util/HashSet;ZII)Landroid/content/pm/PackageInfo;" in old_contents[i]:
        in_function = True
    if ".end method" in old_contents[i]:
        in_function = False
    if in_function and ".line" in old_contents[i]:
        start_of_line = i + 1
    if in_function and "arraycopy" in old_contents[i]:
        right_line = True
    if in_function and "Landroid/content/pm/PackageInfo;-><init>()V" in old_contents[i]:
        stored_register = old_contents[i].split("{")[1].split("}")[0]
    if not already_patched and in_function and right_line and not done_patching:
        contents = contents[:start_of_line]
        contents.append("move-object/from16 v0, p0\n")
        contents.append("invoke-static {%s, v0}, Landroid/content/pm/PackageParser;->fillinsig(Landroid/content/pm/PackageInfo;Landroid/content/pm/PackageParser$Package;)V\n" % stored_register)
        done_patching = True
    else:
        contents.append(old_contents[i])
    i = i + 1

if not DEBUG_PROCESS:
    if not already_patched and not partially_patched:
        contents.extend(fillinsig)
    elif partially_patched and not already_patched:
        print(" *** Previous failed patch attempt, not including the fillinsig method again...")
    elif already_patched:
        print(" *** This framework.jar appears to already have been patched... Exiting.")
        sys.exit(0)
    f = open(to_patch, "w")
    contents = "".join(contents)
    f.write(contents)
    f.close()

# reassemble it
print(" *** Injection successful. Reassembling smali...")
subprocess.check_call(["java", "-jar", os.path.join(SCRIPT_DIR, "tools", "smali.jar"), "classes", "-o", "classes.dex"])

# put classes.smali into framework.jar
print(" *** Putting things back like nothing ever happened...")
for f in glob.glob("classes*.dex"):
    subprocess.check_call(["zip", "-r", "framework.jar", f])

# push to device
print(" *** Pushing changes to device...")
if not DEBUG_PROCESS:
    subprocess.check_output(["adb", "-s", chosen_one, "push", "framework.jar", "/system/framework/framework.jar"])

print(" *** All done! :)")
fjar = os.path.join(dirpath, "framework.jar.backup")
print(" *** Your old framework.jar is present at %s, please run\n     \tadb push \"%s\" /system/framework/framework.jar\n     from recovery if your phone bootloops to recover." % (fjar, fjar))

# return to the previous working directory
os.chdir(PREVIOUS_DIR)
# clean up
#shutil.rmtree(dirpath)
