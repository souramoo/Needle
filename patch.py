#!/usr/bin/env python3
import os, subprocess, tempfile, time, shutil, sys

# check if dependencies are there
deperrors = []
DEVNULL = open(os.devnull, 'w')

def exists(program):
    try:
        process = subprocess.call([program, "-h"], stdout=DEVNULL, stderr=DEVNULL)
        return 0
    except:
        deperrors.append(program)
        return 1

if exists("zip") + exists("adb") + exists("java") > 0:
    print(" *** ERROR: Dependencies not satisfied.")
    print("\tPlease make sure you install:\n\t%s" % (deperrors))

# check if device is connected
devices = subprocess.check_output(["adb", "devices"]).decode("utf-8")

if devices.count('\n') <= 2:
    print(" *** Please connect your device first.")
    sys.exit(0)

devices = devices.split('\n')[1:-2]
devices = [a.split("\t")[0] for a in devices]

if len(devices) > 1:
    print("Enter id of device to target:")
    id = input("\n\t".join([str(i)+" - "+a for i,a in zip(range(1, len(devices)+1), devices)]) + "\n\n> ")
    chosen_one = devices[int(id)-1]
else:
    chosen_one = devices[0]

print(" *** Selected device " + chosen_one)

print(" *** Device detected! proceeding...")

# pull framework somewhere temporary
curdir = os.getcwd()
dirpath = tempfile.mkdtemp()
os.chdir(dirpath)
print(" *** Working dir: %s" % dirpath)

print(" *** Rooting adbd...")
subprocess.call(["adb", "-s", chosen_one, "root"])
subprocess.call(["adb", "-s", chosen_one, "wait-for-device"])
subprocess.call(["adb", "-s", chosen_one, "remount", "/system"])

print(" *** Pulling framework from device...")
subprocess.check_output(["adb", "-s", chosen_one, "pull", "/system/framework/framework.jar", "."])

# disassemble it
print(" *** Disassembling framework...")
subprocess.call(["java", "-jar", curdir+"/apktool.jar", "d", "framework.jar"])

# do the injection
print(" *** Done. Now this won't hurt a bit...")
to_patch = "framework.jar.out/smali/android/content/pm/PackageParser.smali"

f = open(to_patch, "r")
old_contents = f.readlines()
f.close()

f = open(curdir+"/fillinsig.smali", "r")
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
subprocess.call(["java", "-jar", curdir+"/apktool.jar", "b", "framework.jar.out"])

# put classes.smali into framework.jar
print(" *** Putting things back like nothing ever happened...")
os.chdir("framework.jar.out/build/apk")
subprocess.call(["zip", "-r", "../../../framework.jar", "classes.dex"])
os.chdir("../../..")

# push to device
print(" *** Pushing changes to device...")
subprocess.check_output(["adb", "-s", chosen_one, "push", "framework.jar", "/system/framework/framework.jar"])

print(" *** All done! :)")

# clean up
os.chdir(curdir)
#shutil.rmtree(dirpath)
