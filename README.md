# Framework Patcher for Android

## What this does
If you have a rooted phone, this will allow you to patch the android system and inject features without needing to recompile the OS or install xposed.

Notably, I made this to inject a fake-signature patch into the system so I can spoof android app signatures.

## How to use
1. Make sure you have Python, Java and adb available
2. Connect your device via usb.
3. Make sure Developer Settings is enabled. This is hidden by default since sometime in Android 4.x, you can show it by going to `About Phone` and tapping on the build number five times in succession.
4. In the phone settings, find the setting for 'Android debugging' and enable it.
5. Find the setting for 'Root Access' and make sure ADB has root access.
6. Now, on the computer, run `python3 patch.py`
7. Reboot phone

(Note: I have only tested this under Linux)

You will need to reboot for Android to detect that you've installed a new framework and so for Dalvik/ART to re-optimise all the apps on the phone. Without this, you may receive an `INSTALL_FAILED_DEXOPT` error when installing new apps. You can do this in android's recovery too (provided /system is mounted). 

Note: You will need to redo this everytime you flash a new /system partition (e.g. flashing an updated cyanogenmod zip or new ROM)

## How to fake signatures
If you have run `patch.py`, you should now have a system patched to accept spoofed app signatures. (Useful for [microG](https://github.com/microg/android_packages_apps_GmsCore)). This bit below is not necessary if you just want that.

If you want to modify an arbitrary app and keep its signature by making use of this patch, copy the output of:

```
java /path/to/framework/patcher/ApkSig <apk name>
```

into a meta-data underneath <application> in the app's AndroidManifest.xml. Disassemble the app as follows:

```
apktool d <apk name>
```

Then in AndroidManifest.xml, find the following: (the dots represent other parameters not important for this)

```
<application ... >
```

And insert the meta-data

```
<application ... >
    <meta-data
        android:name="fake-signature"
        android:value="(value obtained from ApkSig earlier)" />
```

