#Package import
from flask import Flask, render_template, send_file, make_response, url_for, Response, redirect, request, jsonify
from util.serial import serialize, deserialize
from util.util import read_file, write_file, gen_uid, MCU_PRESETS, MCU_DICT
from util.converters import kbd_to_keymap, kbd_to_qmk_info, kbd_to_vial, kbd_to_layout_macro, kbd_to_main_config, layout_str_to_layout_dict, keycodes_md_to_keycode_dict, generate_keycode_conversion_dict, extract_matrix_pins, via_to_kbd
import json
import re
import requests
from traceback import format_exc

from util.json_encoders import * # from qmk_firmware/lib/python/qmk/json_encoders.py, for generating info.json


#initialise app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


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
    manufacturer = form_data['manufacturer']
    mcu_choice = form_data.get('mcu-preset')
    alternate_layouts = form_data.get("layouts")
    try:
        layers = int(form_data.get('layers'))
    except ValueError as e:
        raise Exception(f'Number of Layers needs to be an integer, {e}')
    layout_file = form_data.get('layout-file')

    uploaded_file = request.files.get('file')

    uploaded_netlist = request.files.get('netlist')

    if uploaded_netlist:
        netlist = str(uploaded_netlist.read(), 'utf-8')
    else:
        netlist = None

    if uploaded_file or kle_raw:
        if uploaded_file:
            content = uploaded_file.read()
            text = str(content, 'utf-8')
        elif kle_raw:
            text = '[' + re.sub("(\w+):", r'"\1":',  kle_raw) + ']'

        try:
            # print(text)
            # write_file('test-text.json', text)

            # Deserialize json
            deserialized_path = 'deserialized.json'
            keyboard = deserialize(json.loads(text))

            # To test de/serialization. Should generate same kle json as provided
            serialized_path = 'serialized.json'
            srlzd = serialize(keyboard)
            # write_file(serialized_path, json.dumps(srlzd, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))

            # MCU PRESET

            mcu_dict = MCU_DICT[mcu_choice]
            mcu = mcu_dict['mcu']
            board = mcu_dict['board']
            bootloader = mcu_dict['bootloader']
            if netlist:
                output_pin_pref = mcu_dict['output_pin_pref']
                schem_pin_pref = mcu_dict['schem_pin_pref']

            diode_dir = "COL2ROW"
            if mcu_choice != 'None' and netlist:
                try:
                    pin_dict = extract_matrix_pins(netlist, mcu, output_pin_pref, schem_pin_pref)
                except Exception as e:
                    raise Exception(f"Invalid netlist provided!, {e}")
            elif mcu_choice == 'None' and netlist:
                raise Exception("You need to choose a MCU preset to utilise the netlist function!")
            else:
                pin_dict = {}

            # Parse alt layouts
            if alternate_layouts:
                alt_layouts = json.loads(alternate_layouts)
            else:
                alt_layouts = {}

            # Generate a QMK info.json file used for QMK Configurator
            qmk_info_path = 'info.json'
            qmk_info_json = kbd_to_qmk_info(keyboard, board_name, maintainer, url, vendor_id, product_id, device_ver, mcu, bootloader, board, pin_dict, diode_dir, manufacturer, alt_layouts)
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

            if layout_file:
                layout_dict = layout_str_to_layout_dict(layout_file)
                # keycodes_dict = keycodes_md_to_keycode_dict(read_file('keycodes.md')) # Local fallback
                link = "https://raw.githubusercontent.com/qmk/qmk_firmware/master/docs/keycodes.md"
                keycodes_dict = keycodes_md_to_keycode_dict(requests.get(link).text)
                conversion_dict = generate_keycode_conversion_dict(read_file('deprecated_keycodes.txt'))

                keymap_content = kbd_to_keymap(keyboard, layers, 1, layout_dict, keycodes_dict, conversion_dict)
            else:
                keymap_content = kbd_to_keymap(keyboard, layers, 1)

            main_config_h_content = kbd_to_main_config(keyboard, layers)

            print("Successfully completed compilation of a board!")


        except Exception as e:
            error_message = "ERROR: \n\n" + format_exc() + "\n\nREAD THE DOCUMENTATION IF YOU HAVE NOT ALREADY.\nSEE https://github.com/zykrah/firmware-scripts.\n\nIf there isn't a specific error, please contact me."
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


VIA_TEMPLATE = """{
  "name": "Keyboard",
  "layouts": {
    "labels": [],
    "keymap": []
  }
}"""

#These functions will run when POST method is used.
@app.route('/from-via', methods = ["POST", "GET"] )
def run_script_():
    form_data = request.form
    via_json = form_data.get('via-json')
    raw_kle = form_data.get('raw-kle')

    if via_json or raw_kle:
        try:
            if not via_json:
                via_json = VIA_TEMPLATE
            if raw_kle:
                keymap = json.loads('[' + re.sub("(\w+):", r'"\1":',  raw_kle) + ']')
                obj = json.loads(VIA_TEMPLATE)
                obj['layouts']['keymap'] = keymap
                via_json = json.dumps(obj)

            # TO-DO: Create a proper KLE raw data JSON encoder
            kle_ouput = json.dumps(serialize(via_to_kbd(via_json)), ensure_ascii=False, indent=2, cls=KLEJSONEncoder)
            
            print("Successfully completed a conversion of a via json!")

        except Exception as e:
            error_message = "ERROR: \n\n" + format_exc()
            return render_template('from-via.html', output=error_message)

        return render_template('from-via.html', output=kle_ouput)
    
    else:
        return render_template('from-via.html', via_template=VIA_TEMPLATE)
      #This just reloads the page if no file is selected and the user tries to POST. 


if __name__ == '__main__':
    app.run(debug = True)

