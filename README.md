# Firmware 'scripts'
**UPDATE: There is now a website for this. [Click me!](https://zykrah.me/).** This repository acts mainly as documentation. Please read through it.

![image](https://user-images.githubusercontent.com/23428162/194707201-99dbab42-5239-49ad-9d80-84f04316c726.png)

Python scripts to make writing firmware faster/easier. The idea of the script/s is to remove the need to manually write a lot of the boring/repetitve/time-consuming firmware stuff.

Basic demonstration on how quick it is (placing this at the beginning because it seems some people are missing the point of the script):

https://user-images.githubusercontent.com/23428162/194706855-201f43f8-fdc8-446c-abba-55e9742c7588.mp4

> Disclaimer: The script utilizes some code from other places like [pykle_serial](https://github.com/hajimen/pykle_serial) (for the deserializer code) and some small util scripts from [vial-qmk](https://github.com/vial-kb/vial-qmk/blob/vial/util/vial_generate_keyboard_uid.py) (for the uid generation) and [qmk_firmware](https://github.com/qmk/qmk_firmware/blob/master/lib/python/qmk/json_encoders.py) (for the json encoders; to match the official qmk info.json formatting). I translated the serialization code from [kle-serial](https://github.com/ijprest/keyboard-layout-editor/blob/master/serial.js) myself. The rest of the scripts to actually convert from the deserialized layout to the other firmware files is done by me.

Realistcally you can use just the serialization and deserialization code to write your own scripts in python too. What I've coded are just examples/what I think is useful to me.

You start with your KLE (colours for multilayout not necessary). Keep in mind that apart from the image below (and the images in the guidelines), all files/images have been generated **entirely** by the script.

![image](https://user-images.githubusercontent.com/23428162/168476589-b85a1463-1e89-4ac8-a9f1-03661b76595a.png)

The idea is to then follow the following guidelines to be able to output various firmware-related files (e.g. a whole via.json).

# Guidelines:
![image](https://user-images.githubusercontent.com/23428162/168476640-09a4b226-8364-4fc1-833d-9fd1efac6a04.png)
- 0:  (QMK info.json only) If there is text here, it is included as the "label" in the info.json
- 1:  (For keymap.c) QMK Keycodes go here for layer 0 of the keymap.c, if nothing is included keys default to `KC_TRNS`
- 2:  (VIAL only) If there is a 'u' here, the key is included as a key for the unlock combo 
- 3:  Multilayout index
- 4:  (VIAL only) If there is an 'e' here, the key is an encoder
- 5:  Multilayout value
- 6:  Secondary Multilayout name (if there is a list of multilayout options i.e. more than 2 e.g. multiple bottom row layouts. See example board below.)
- 7:  Primary Multilayout name/label (needs to be in at least one of the keys for any given multilayout option. If there is a list of multilayout options, at least one key of each value should have a secondary label in position 6. See example board below.)
- 9:  Row
- 11: Col

> The name of the board can also be edited in KLE

Example of the initial board being converted as per above guidelines:

![image](https://user-images.githubusercontent.com/23428162/174466850-897b7da3-389b-4c21-8d17-2f1fae60f7bf.png)

The script takes in the `json` file of that KLE, downloaded as shown:

![image](https://user-images.githubusercontent.com/23428162/168476867-7477de1c-a342-41e8-b515-0a1d21b097b8.png)

# VIA files
The script automatically generates a `via.json`.
You just need to set a vendor id, product id, and lighting manually.
The rows, cols, keymap and even multilayout labels are automatically set.

Example of the initial board being converted (this image is slightly outdated):

![image](https://user-images.githubusercontent.com/23428162/168476979-1143ec2b-9967-4b91-9240-816fe28cd861.png)

# VIAL files
The script can also generate a `vial.json` and accompanying `config.h` with required settings.
(the vial.json is the same as the via.json, it just includes encoder keys)
It automatically randomly generates the UID. No need to run the script manually and pain-stakingly paste it.
It also automatically adds the unlock combo based on which keys were marked with a `u` in the input KLE. If no keys are assigned, it defines `VIAL_INSECURE` instead.

Example of the initial board being converted:

![image](https://user-images.githubusercontent.com/23428162/168477177-2f198dd4-32a1-4d5a-8aa1-39888b8c1ce3.png)


# QMK info.json file

**UPDATE: As on the website, you can now define certain things and it will add various configuration options to the info.json. e.g. MCU presets (currently there's just RP2040 and 32U4).**

![image](https://user-images.githubusercontent.com/23428162/194707307-b2602525-1038-4d2e-9990-cdfd4140324f.png)

![image](https://user-images.githubusercontent.com/23428162/194707291-e9a8b5d4-0a35-4835-aa2b-34612637e298.png)

![image](https://user-images.githubusercontent.com/23428162/194707400-353325d1-40ba-4501-a62b-5f0d9918ac13.png)

The script also automatically generates an `info.json`.
Matrix labels are automatically added.
Key labels/names are automatically added if applicable.
It automatically detects (based on the multilayout keys), which combination of multi-layout options produces a layout with the most amount of keys. In other words, a `LAYOUT_ALL` for use with VIA/L.
The keys are also offset appropriately.

> ~~WIP: I want to be able to automatically detect (based on the multilayout keys), which combination of multi-layout options produces a `LAYOUT_ALL` for use with via (maximum amount of keys).~~ DONE

> WIP: Add a more generic converter.
> WIP: Add the option to create more layouts based on multilayouts picked by the user

Example of the initial board being converted:

![image](https://user-images.githubusercontent.com/23428162/168613346-3093326b-dd5f-4cf3-8b72-df4aa86ce260.png)

Below is what the `LAYOUT_ALL` looks like (represented in KLE). You can see how the script automatically picked the layout option with the most keys for each multilayout (e.g. the split backspace). If all multilayouts have the same amount of keys (e.g. non/stepped capslocks), the default one (value 0) is picked. You can also see how the everything is offset appropriately. 

![image](https://user-images.githubusercontent.com/23428162/168613442-5ea87f88-3bc4-4406-91d6-df2550f58f43.png)

> NOTE: I haven't tested this with more complex multilayouts or larger boards.

# KEYMAP.C

Use label `1` to set QMK keycodes for the keymap. Currently only applies to layer 0. Keys without this label will default to `KC_TRNS`. The script splits the lines by rows, but it's up to you to do the rest of the formatting. (Planning on improving this later)

![image](https://user-images.githubusercontent.com/23428162/194707078-5e48a970-c7c0-4ddc-86b5-41b8785d11d2.png)


# LAYOUT macro (in kb.h file)
~~I plan on creating this soon. However, you can compile firmware without this through the use of the info.json and the matrix labels.~~ DONE. While the functionality hasn't been published to this repo, it appears on the website. This conversion directly reflects what QMK generates when you use `info.json` and the `matrix` labels. This can be **useful for creating/visualizing your keymap**.

![image](https://user-images.githubusercontent.com/23428162/194707361-32adabbc-d5c0-460f-b22f-c65cf43d3c7e.png)


# Extra
I plan on further improving the scripts, and also adding more features.

I also plan on soon implementing some code to convert from VIA -> KLE, VIA -> info.json, info.json -> KLE, etc.

WIP:
- be able to re-configure the "guidelines"/labels as you wish
- ~~the info.json stuff mentioned above~~
- ~~generate layout macro (kb.h) and keymap.c~~ DONE on the website
- more conversions
- generate more firmware files (e.g. kb.c rgb stuff, ~~main config.h file~~, rules.mk file, maybe even kicad projects?)

Maybes:
- automatically detect/generate matrix from just a KLE
- be able to input a kicad project/pcb? automatically detect everything from the matrix, switch positions, etc? UPDATE: See [here](https://github.com/zykrah/kicad-kle-placer) for a kicad switch placer plugin.
- be able to generate a kicad project
- be able to output things useful in blender (for the renderers)

# Usage
 Use [the website](https://zykrah.me/). OR if you still intend on using the code from this repo (it's outdated), modify the code as required in `run.py` and run it.
 
 ~~I plan to turn this into a script usable on a website or something that can be ran in command line eventually.~~ DONE
