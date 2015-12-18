# Framework Patcher for Android

## What this does
If you have a rooted phone, this will allow you to patch the android system and inject features without needing to recompile the OS or install xposed.

Notably, I made this to inject a fake-signature patch into the system so I can spoof android app signatures.

## How to use
Make sure you have adb and java available, connect your device via usb and run `python3 patch.py` (Note: I have only tested this under Linux)

Note: You will need to redo this everytime you flash a new /system partition (e.g. flashing an updated cyanogenmod zip or new ROM)

## How to fake signatures
If you have run `patch.py`, you should now have a system patched to accept spoofed app signatures. (Useful for ).

If you want to modify an app and keep its signature, copy the output of:

```
java /path/to/framework/patcher/ApkSig <apk name>
```

into a meta-data underneath <application> in the AndroidManifest.xml - disassemble the app as follows:

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

