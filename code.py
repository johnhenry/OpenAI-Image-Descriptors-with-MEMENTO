# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import binascii
import wifi
import vectorio
import socketpool
import adafruit_requests
import displayio
from jpegio import JpegDecoder
from adafruit_display_text import label, wrap_text_to_lines
import terminalio
import adafruit_pycamera


# scale for displaying returned text from OpenAI
text_scale = 2

# OpenAI key and prompts from settings.toml
openai_api_key = os.getenv("OPENAI_API_KEY")
prompts = ["ALIEN","ALT_TEXT","CABLE","HAIKU","HOW","HOW_BIG","HOW_BRIGHT","HOW_COLD","HOW_DARK","HOW_DEEP","HOW_FAST","HOW_HEAVY","HOW_HOT","HOW_LONG","HOW_LOUD","HOW_MANY","HOW_MUCH","HOW_OLD","HOW_OLD","HOW_TALL","HOW_WIDE","MYSTERY","POEM","RECIPE","RIDDLE","SONNET","STORY","TANKA","TECHNICAL","THREE_WORDS","WHAT","WHEN","WHERE","WHO","WHY","YE_OLDE"]
num_prompts = len(prompts)
prompt_index = 0

# encode jpeg to base64 for OpenAI
def encode_image(image_path):
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        base64_encoded_data = binascii.b2a_base64(image_data).decode('utf-8').rstrip()
        return base64_encoded_data

# view returned text on MEMENTO screen
def view_text(the_text):
    rectangle = vectorio.Rectangle(pixel_shader=palette, width=240, height=240, x=0, y=0)
    cam.splash.append(rectangle)
    the_text = "\n".join(wrap_text_to_lines(the_text, 20))
    if prompt_index == 1:
        the_text = the_text.replace("*", "\n")
    text_area = label.Label(terminalio.FONT, text=the_text,
                            color=0xFFFFFF, x=2, y=10, scale=text_scale)
    cam.splash.append(text_area)
    cam.display.refresh()

# send image to OpenAI, print the returned text and save it as a text file
def send_img(img, prompt):
    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {openai_api_key}"
    }
    payload = {
      "model": "gpt-4-vision-preview",
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": f"{os.getenv("PROMPT_" + prompt)}"
            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(img)}"
              }
            }
          ]
        }
      ],
      "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions",headers=headers, json=payload)
    content = response.json()['choices'][0]['message']['content']
    print(content)
    alt_text_file = img.replace('jpg', 'txt')
    alt_text_file = alt_text_file[:11] + f"_{prompts[prompt_index]}" + alt_text_file[11:]
    if prompt_index == 5:
        alt_text_file = alt_text_file.replace("?", "")
    with open(alt_text_file, "a") as fp:
        fp.write(content)
        fp.flush()
        time.sleep(1)
        fp.close()
    view_text(content)
# view images on sd card to re-send to OpenAI
def load_image(bit, file):
    bit.fill(0b00000_000000_00000)  # fill with a middle grey
    decoder.open(file)
    decoder.decode(bit, scale=0, x=0, y=0)
    cam.blit(bit, y_offset=32)
    cam.display.refresh()

print()
print("Connecting to WiFi:", end ="")
try:
  wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
  print(os.getenv('CIRCUITPY_WIFI_SSID'))
except:
  wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID_BACKUP'), os.getenv('CIRCUITPY_WIFI_PASSWORD_BACKUP'))
  print(os.getenv('CIRCUITPY_WIFI_SSID_BACKUP'))

time.sleep(2)

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

palette = displayio.Palette(1)
palette[0] = 0x000000
decoder = JpegDecoder()
# used for showing images from sd card
bitmap = displayio.Bitmap(240, 176, 65535)

cam = adafruit_pycamera.PyCamera()
cam.mode = 0  # only mode 0 (JPEG) will work in this example

# Resolution of 320x240 is plenty for OpenAI
cam.resolution = 1  # 0-12 preset resolutions:
#                      0: 240x240, 1: 320x240, 2: 640x480, 3: 800x600, 4: 1024x768,
#                      5: 1280x720, 6: 1280x1024, 7: 1600x1200, 8: 1920x1080, 9: 2048x1536,
#                      10: 2560x1440, 11: 2560x1600, 12: 2560x1920
# cam.led_level = 1  # 0-4 preset brightness levels
# cam.led_color = 0  # 0-7  preset colors: 0: white, 1: green, 2: yellow, 3: red,
#                                          4: pink, 5: blue, 6: teal, 7: rainbow
cam.effect = 0  # 0-7 preset FX: 0: normal, 1: invert, 2: b&w, 3: red,
#                                  4: green, 5: blue, 6: sepia, 7: solarize
# sort image files by numeric order
all_images = [
    f"/sd/{filename}"
    for filename in os.listdir("/sd")
    if filename.lower().endswith(".jpg")
    ]
all_images.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
# add label for selected prompt
rect = vectorio.Rectangle(pixel_shader=palette, width=240, height=20, x=0, y=0)
prompt_txt = label.Label(
            terminalio.FONT, text=prompts[prompt_index], color=0xFF0055, x=10, y=15, scale=2
        )
# pylint: disable=protected-access
cam._botbar.append(rect)
cam._botbar.append(prompt_txt)
# pylint: enable=protected-access
cam.display.refresh()

view = False
new_prompt = False
file_index = -1

while True:
    if new_prompt:
        cam.display_message("SEND?")
    if not view:
        if not new_prompt:
            cam.blit(cam.continuous_capture())
    cam.keys_debounce()
    if cam.shutter.long_press:
        cam.autofocus()
    if cam.shutter.short_count:
        try:
            cam.display_message("~>", color=0x00DD00)
            cam.capture_jpeg()
            cam.live_preview_mode()
        except TypeError as exception:
            cam.display_message(":(", color=0xFF0000)
            time.sleep(0.5)
            cam.live_preview_mode()
        except RuntimeError as exception:
            cam.display_message("SD :(", color=0xFF0000)
            time.sleep(0.5)
        all_images = [
        f"/sd/{filename}"
        for filename in os.listdir("/sd")
        if filename.lower().endswith(".jpg")
        ]
        all_images.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        the_image = all_images[-1]
        cam.display_message("send..", color=0x00DD00)
        send_img(the_image, prompts[prompt_index])
        view = True

    if cam.up.fell:
        prompt_index = (prompt_index - 1) % num_prompts
        prompt_txt.text = prompts[prompt_index]
        cam.display.refresh()

    if cam.down.fell:
        prompt_index = (prompt_index + 1) % num_prompts
        prompt_txt.text = prompts[prompt_index]
        cam.display.refresh()

    if cam.right.fell:
        if new_prompt:
            file_index = (file_index - -1) % -len(all_images)
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            prompt_index = (prompt_index + 1) % num_prompts
            prompt_txt.text = prompts[prompt_index]
            cam.display.refresh()

    if cam.left.fell:
        if new_prompt:
            file_index = (file_index + -1) % -len(all_images)
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            prompt_index = (prompt_index - 1) % num_prompts
            prompt_txt.text = prompts[prompt_index]
            cam.display.refresh()

    if cam.select.fell:
        if not new_prompt:
            file_index = -1
            new_prompt = True
            filename = all_images[file_index]
            load_image(bitmap, filename)
        else:
            new_prompt = False
            cam.display.refresh()

    if cam.ok.fell:
        if view:
            cam.splash.pop()
            cam.splash.pop()
            cam.display.refresh()
            view = False
        if new_prompt:
            cam.display_message("send..", color=0x00DD00)
            send_img(filename, prompts[prompt_index])
            new_prompt = False
            view = True

