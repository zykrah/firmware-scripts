#Package import
from flask import Flask, render_template, send_file, make_response, url_for, Response, redirect, request, jsonify
from serial import serialize, deserialize
from util import read_file, write_file, gen_uid
from converters import kbd_to_keymap, kbd_to_qmk_info, kbd_to_via, kbd_to_vial, kbd_to_layout_macro, kbd_to_main_config
import json
import re


from json_encoders import * # from qmk_firmware/lib/python/qmk/json_encoders.py, for generating info.json


#initialise app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


MCU_PRESETS = ['None', 'RP2040', '32U4']

#decorator for homepage 
@app.route('/' )
def index():
    return render_template('index.html',
                           PageTitle = "Landing page",
                           mcu_presets=MCU_PRESETS)


#These functions will run when POST method is used.
@app.route('/', methods = ["POST", "GET"] )
def run_script():
    form_data = request.form


    kle_raw = form_data['kle-raw']
    board_name = form_data['board-name']
    if not board_name:
        board_name = "Keyboard"
    maintainer = form_data['maintainer']
    url = form_data['url']
    lighting = form_data['lighting']
    vendor_id = form_data['vendor-id']
    product_id = form_data['product-id']
    device_ver = form_data['device-ver']
    mcu_choice = form_data.get('mcu-preset')


    uploaded_file = request.files['file']
    if 'file' in request.files.keys():
        uploaded_file = request.files['file']
    else:
        uploaded_file = None
    
    if uploaded_file or kle_raw:
        if uploaded_file:
            content = uploaded_file.read()
            text = str(content, 'utf-8')
        elif kle_raw:
            text = '[' + re.sub("(\w+):", r'"\1":',  kle_raw) + ']'


        try:
            # print(text)
            write_file('test-text.json', text)


            # Deserialize json
            deserialized_path = 'deserialized.json'
            keyboard = deserialize(json.loads(text))

            # To test de/serialization. Should generate same kle json as provided
            serialized_path = 'serialized.json'
            srlzd = serialize(keyboard)
            # write_file(serialized_path, json.dumps(srlzd, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))

            # MCU PRESET

            if mcu_choice == 'RP2040':
                mcu = 'RP2040'
                bootloader = 'rp2040'
            elif mcu_choice == '32U4':
                mcu = 'atmega32u4'
                bootloader = 'atmel-dfu'
            else:
                mcu = None
                bootloader = None

            # Generate a QMK info.json file used for QMK Configurator
            qmk_info_path = 'info.json'
            qmk_info_json = kbd_to_qmk_info(keyboard, board_name, maintainer, url, vendor_id, product_id, device_ver, mcu, bootloader)
            qmk_info_content = json.dumps(qmk_info_json, indent=4, separators=(', ', ': '), sort_keys=False, cls=InfoJSONEncoder)
            # write_file(qmk_info_path, qmk_info_content)


            # Generate a VIAL json file used to identify a keyboard in VIAL. Same as via but with encoders and no required product/vendor ID
            # Also generate a config.h file with a randomly generated UID and unlocking combo (if included)
            vial_vendor_id = vendor_id
            vial_product_id = product_id
            vial_uid = gen_uid()
            vial_json, vial_config_h = kbd_to_vial(keyboard, vial_uid, vial_vendor_id, vial_product_id, lighting, board_name)

            vial_json_path = 'vial.json'
            vial_json_content = json.dumps(vial_json, ensure_ascii=False, indent=2, cls=KLEJSONEncoder)
            # write_file(vial_json_path, vial_json_content)

            vial_config_h_path = 'config.h'
            # write_file(vial_config_h_path, vial_config_h)

            keyboard_h_content = kbd_to_layout_macro(keyboard)

            keymap_content = kbd_to_keymap(keyboard)

            main_config_h_content = kbd_to_main_config(keyboard)

            print("Successfully completed compilation of a board!")


        except Exception as e:
            error_message = "ERROR: " + str(e) + "\n\nREAD THE DOCUMENTATION IF YOU HAVE NOT ALREADY.\nSEE https://github.com/zykrah/firmware-scripts."
            return render_template('index.html',
                                   qmk_info_json = error_message,
                                   vial_json = error_message,
                                   vial_config_h = error_message,
                                   main_config_h = error_message,
                                   keyboard_h = error_message,
                                   keymap = error_message,
                                   mcu_presets=MCU_PRESETS,
                                   mcu_choice=mcu_choice
                                   )


        # return Response(vial_json_content)
        # return jsonify(vial_json)
        return render_template('index.html',
                                qmk_info_json = qmk_info_content,
                                vial_json = vial_json_content,
                                vial_config_h = vial_config_h,
                                main_config_h = main_config_h_content,
                                keyboard_h = keyboard_h_content,
                                keymap = keymap_content,
                                mcu_presets=MCU_PRESETS,
                                mcu_choice=mcu_choice
                                )
    
    else:
        return index()
      #This just reloads the page if no file is selected and the user tries to POST. 


@app.route("/", methods=['GET'])
def back():
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug = True)

