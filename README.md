# firmware-scripts
 Python scripts to make writing firmware faster/easier.

 Disclaimer: This code utilizes some code from other places like [pykle_serial](https://github.com/hajimen/pykle_serial) (for the deserializer code) and some small util scripts from [vial-qmk](https://github.com/vial-kb/vial-qmk/blob/vial/util/vial_generate_keyboard_uid.py) (for the uid generation) and [qmk_firmware](https://github.com/qmk/qmk_firmware/blob/master/lib/python/qmk/json_encoders.py) (for the json encoders; to match the official qmk info.json formatting). However, I translated the serialization code from [kle-serial](https://github.com/ijprest/keyboard-layout-editor/blob/master/serial.js) myself, and the rest of the scripts (used to actually convert from the deserialized layout to the other firmware files) is done by me.

 Read [this](https://gist.github.com/zykrah/bdcb893a73e2ffde932da9ad69bd81c4) for some more info.
