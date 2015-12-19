#!/usr/bin/env python3
import os, subprocess, tempfile, time, shutil, sys

# ensure binaries are present
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

print(" *** Rooting adbd...")
subprocess.call(["adb", "-s", chosen_one, "root"])
subprocess.call(["adb", "-s", chosen_one, "wait-for-device"])

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

while i < len(old_contents):
    if "fillinsig" in old_contents[i]:
        already_patched = True
    if ".method public static generatePackageInfo(Landroid/content/pm/PackageParser$Package;[IIJJLandroid/util/ArraySet;Landroid/content/pm/PackageUserState;I)Landroid/content/pm/PackageInfo;" in old_contents[i]:
        in_function = True
    if ".line" in old_contents[i]:
        start_of_line = i + 1
    if "arraycopy" in old_contents[i]:
        right_line = True
    if not already_patched and in_function and right_line and not done_patching:
        contents = contents[:start_of_line]
        contents.append("move-object/from16 v0, p0\n")
        contents.append("invoke-static {v11, v0}, Landroid/content/pm/PackageParser;->fillinsig(Landroid/content/pm/PackageInfo;Landroid/content/pm/PackageParser$Package;)V\n")
        done_patching = True
    else:
        contents.append(old_contents[i])
    i = i + 1

if not already_patched:
    contents.extend(fillinsig)
else:
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
print(dirpath)
#shutil.rmtree(dirpath)
