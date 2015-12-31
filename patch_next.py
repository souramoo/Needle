#!/usr/bin/env python3
import os, subprocess, tempfile, time, shutil, sys

# ensure binaries are present
print(" *** CM13/marshmallow patch to fix play-services")
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
to_patch = "framework.jar.out/smali_classes2/android/view/inputmethod/InputMethodManager.smali"

f = open(to_patch, "r")
old_contents = f.readlines()
f.close()

i = 0
contents = []
done_patching = False
already_patched = False
stored_register = "v1"

while i < len(old_contents):
    if "Landroid/content/Context;->getPackageName()" in old_contents[i]:
        already_patched = True
    if "Landroid/content/Context;->getOpPackageName()" in old_contents[i] and not done_patching:
        stored_register = old_contents[i].split("{")[1].split("}")[0]
        contents.append("invoke-virtual {%s}, Landroid/content/Context;->getPackageName()Ljava/lang/String;\n" % stored_register)
        done_patching = True
    else:
        contents.append(old_contents[i])
    i = i + 1

if already_patched:
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
subprocess.call(["zip", "-r", "../../../framework.jar", "classes2.dex"])
os.chdir("../../..")

# push to device
print(" *** Pushing changes to device...")
subprocess.check_output(["adb", "-s", chosen_one, "push", "framework.jar", "/system/framework/framework.jar"])

print(" *** All done! :)")

# clean up
os.chdir(curdir)
#shutil.rmtree(dirpath)
