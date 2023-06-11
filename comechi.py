import os
import re
import json
import math
import time
import datetime
from copy import deepcopy
import xml.dom.minidom
import requests
import argparse
from collections import Counter


def draw_rounded_rectangle(width, height, r):
    bgw = width
    bgh = height
    br = round(r * 0.55, 3)
    p0 = '{} 0'.format(r)
    c1 = '{} {} b {} {} {} {} {} {}'.format(bgw - r, 0, bgw - r + br, 0, bgw, r - br, bgw, r)
    c2 = '{} {} b {} {} {} {} {} {}'.format(bgw, bgh - r, bgw, bgh - r + br, bgw - r + br, bgh, bgw - r, bgh)
    c3 = '{} {} b {} {} {} {} {} {}'.format(r, bgh, r - br, bgh, 0, bgh - r + br, 0, bgh - r)
    c4 = '{} {} b {} {} {} {} {} {}'.format(0, r, 0, r - br, r - br, 0, r, 0)
    ass_drawing_command = '{\p1}' + 'm {} l {} l {} l {} l {}'.format(p0, c1, c2, c3, c4) + '{\p0}'
    return ass_drawing_command


def color(rgba):
    r = hex(rgba['r'])[2:4].upper().zfill(2)
    g = hex(rgba['g'])[2:4].upper().zfill(2)
    b = hex(rgba['b'])[2:4].upper().zfill(2)
    a = hex(round((1 - float(rgba['a'])) * 255))[2:4].upper().zfill(2)
    return f"&H{a}{b}{g}{r}"


# 将时间戳(个位数为0.01s)转换成ass文件的时间(x:xx:xx.xx)
def stamp_to_time(stamp):
    h = stamp // 360000
    re = stamp % 360000
    m = re // 6000
    re = re % 6000
    s = re // 100
    ms = re % 100
    timehmsms = '{}:{}:{}.{}'.format(str(h), str(m).zfill(2), str(s).zfill(2), str(ms).zfill(2))
    return timehmsms


def time_to_stamp(t):
    h, m, s, ms = re.split('[:.]', t)
    if len(ms) == 3:
        ms = round(int(ms) / 10)
    stamp = (int(h) * 3600 + int(m) * 60 + int(s)) * 100 + int(ms)
    return stamp


def fix_invalid_file_name(file_name):
    return re.sub(r'[/\\:*?\"<>|]', '_', file_name)


class AssTag:
    color_command = {'white': '#FFFFFF', 'red': '#FF0000', 'pink': '#FF8080', 'orange': '#FFC000', 'yellow': '#FFFF00',
                     'green': '#00FF00', 'cyan': '#00FFFF', 'blue': '#0000FF', 'purple': '#C000FF', 'black': '#000000',
                     'white2': '#CCCC99', 'red2': '#CC0033', 'pink2': '#FF33CC', 'orange2': '#FF6600',
                     'yellow2': '#999900', 'green2': '#00CC66', 'cyan2': '#00CCCC', 'blue2': '#3399FF',
                     'purple2': '#6633CC', 'black2': '#666666'}

    def __init__(self):
        self.font_name = ''
        self.font_size = ''
        self.color = ''
        self.outline_color = ''
        self.opacity = ''
        self.outline_opacity = ''

        self.alignment = ''
        self.pos_tag = ''
        self.other = ''

        self.x = ''
        self.x1 = ''
        self.x2 = ''
        self.y = ''

    def set_font_name(self, f_name):
        self.font_name = fr'\fn{f_name}'

    def set_font_size(self, f_size):
        self.font_size = fr'\fs{f_size}'

    def set_color(self, color_code):
        r_hex = color_code[1:3]
        g_hex = color_code[3:5]
        b_hex = color_code[5:7]
        self.color = fr"\c&H{b_hex}{g_hex}{r_hex}&"

    def set_outline_color(self, color_code):
        r_hex = color_code[1:3]
        g_hex = color_code[3:5]
        b_hex = color_code[5:7]
        self.outline_color = fr"\3c&H{b_hex}{g_hex}{r_hex}&"

    def set_opacity(self, value):
        self.opacity = fr"\1a&H{hex(round(255 * value))[2:4]}&"

    def set_outline_opacity(self, value):
        self.outline_opacity = fr"\3a&H{hex(round(255 * value))[2:4]}&"

    def set_alignment(self, a):
        """
        设置对齐方式
        :param a: 对齐方式 取值范围[1-9] 效果参照小键盘
        :return:
        """
        self.alignment = fr'\an{a}'

    def set_pos(self, x, y):
        self.pos_tag = fr'\pos({x}, {y})'

    def set_move(self, x1, x2, y):
        self.x1 = x1
        self.x2 = x2
        self.y = y
        self.pos_tag = fr'\move({x1},{y},{x2},{y})'

    def translate_command(self, command_list):
        for command in command_list:
            if command in self.color_command:
                self.set_color(self.color_command[command])
            elif re.search('#.{6}', command):
                self.set_color(command)
            elif command == 'small':
                self.set_font_size(round(style['font_size'] * 0.6))
            elif command == 'big':
                self.set_font_size(round(style['font_size'] * 1.47))
            elif command == 'mincho':
                self.set_font_name('Yu Mincho')
            elif command == 'gothic':
                self.set_font_name('Yu Gothic')
            elif command == 'ue':
                self.set_alignment('8')
                self.set_pos(WIDTH / 2, 0)
            elif command == 'shita':
                self.set_alignment('2')
                self.set_pos(WIDTH / 2, HEIGHT)

    def string(self):
        attribute_dict = {}
        attribute_dict_temp = self.__dict__
        key_del = ['x', 'x1', 'x2', 'y']

        for k, v in attribute_dict_temp.items():
            if k not in key_del:
                attribute_dict[k] = v

        tag_text = ''.join(attribute_dict.values())
        if tag_text:
            tag_text = f"{{{tag_text}}}"
        return tag_text


class Dialogue:
    def __init__(self):
        self.layer = '0'
        self.start = ''
        self.end = ''
        self.style = ''
        self.name = ''
        self.margin_l = '0'
        self.margin_r = '0'
        self.margin_v = '0'
        self.effect = ''
        self.text = ''

        self.tag = AssTag()

        self.text_row_cnt = 1

        self.raw = None

    def tag_and_text(self):
        return f"{self.tag.string()}{self.text}"

    def set_default_bg_style(self, style_bg):
        self.tag.set_color(style_bg['color'])
        self.tag.set_opacity(style_bg['opacity'])
        self.tag.set_outline_color(style_bg['outline_color'])
        self.tag.set_outline_opacity(style_bg['outline_opacity'])
        self.tag.other += style_bg['other']

    def draw_bg_official(self, font_size):
        self.layer = '3'
        self.name = f'BG {self.name}'

        style_bg = style['official']['background']
        self.set_default_bg_style(style_bg)

        bg_width = WIDTH - style_bg['marginH'] * 2
        bg_height = font_size * self.text_row_cnt + style_bg['paddingV'] * 2
        border_radius = style_bg['border_radius']

        self.text = draw_rounded_rectangle(bg_width, bg_height, border_radius)

    def draw_bg_vote_question(self, bg_width, bg_height):
        self.layer = '3'
        self.name = f'BG {self.name}'

        style_bg = style['vote']['question']['bg']
        self.set_default_bg_style(style_bg)

        border_radius = style_bg['border_radius']
        self.text = draw_rounded_rectangle(bg_width, bg_height, border_radius)

    def draw_bg_vote_choice(self, bg_width, bg_height):
        self.layer = '3'
        self.name = f'BG {self.name}'

        style_bg = style['vote']['choice']['bg']
        self.set_default_bg_style(style_bg)

        border_radius = style_bg['border_radius']
        self.text = draw_rounded_rectangle(bg_width, bg_height, border_radius)

    def draw_bg_vote_result(self, x1, bg_width, result):
        self.layer = '4'
        self.name = 'BG アンケート 結果'

        style_bg = style['vote']['result']['bg']
        self.set_default_bg_style(style_bg)

        result = float(result[:-1]) / 100
        x2 = round(x1 + bg_width * result)
        t1 = style_bg['animation']['time_start']
        t2 = style_bg['animation']['time_end']
        accel = style_bg['animation']['accel']

        self.tag.clip = rf"\clip(0,0,{x1},{HEIGHT})\t({t1},{t2},{accel}\clip(0,0,{x2},{HEIGHT})))"

    def string(self):
        d_list = [self.layer, self.start, self.end, self.style, self.name, self.margin_l, self.margin_r, self.margin_v,
                  self.effect, self.tag_and_text()]

        return f"Dialogue: {','.join(d_list)}"


class Comment:
    def __init__(self):
        self.ng_pattern = re.compile('(NGコメントです)')

        self.title = None
        self.platform = None
        self.source = None
        self.data_raw = None

        self.open_time = None
        self.official_name = None

        self.save = False

        self.normal = []
        self.normal_still = []
        self.official = []
        self.vote = []
        self.comment_art = []
        self.other = []

        self.cnt = 0
        self.vote_cnt = 0
        self.ca_cnt = 0
        self.viewer_cnt = []

        self.d_comment_art = []
        self.d_official = []
        self.d_vote = []
        self.d_normal = []
        self.d_bg = []

        self.style_official = {'Name': '運営コメント',
                               'Fontname': style['official']['font_name'],
                               'Fontsize': str(style['official']['font_size']),
                               'PrimaryColour': color(style['official']['color']),
                               'SecondaryColour': '&H00B4FCFC',
                               'OutlineColour': color(style['official']['outline_color']),
                               'BackColour': '&H80000008',
                               'Bold': '-1',
                               'Italic': '0',
                               'Underline': '0',
                               'StrikeOut': '0',
                               'ScaleX': '100',
                               'ScaleY': '100',
                               'Spacing': '0',
                               'Angle': '0',
                               'BorderStyle': '1',
                               'Outline': str(style['official']['outline']),
                               'Shadow': '0',
                               'Alignment': '8',
                               'MarginL': '0',
                               'MarginR': '0',
                               'MarginV': str(
                                   style['official']['background']['marginV'] + style['official']['background'][
                                       'paddingV']),
                               'Encoding': '1'
                               }
        self.style_normal = {'Name': 'コメント',
                             'Fontname': style['font_name'],
                             'Fontsize': str(style['font_size']),
                             'PrimaryColour': color(style['color']),
                             'SecondaryColour': '&H00FFFFFF',
                             'OutlineColour': color(style['outline_color']),
                             'BackColour': '&H00000000',
                             'Bold': '-1',
                             'Italic': '0',
                             'Underline': '0',
                             'StrikeOut': '0',
                             'ScaleX': '100',
                             'ScaleY': '100',
                             'Spacing': '0',
                             'Angle': '0',
                             'BorderStyle': '1',
                             'Outline': str(style['outline']),
                             'Shadow': '0',
                             'Alignment': '7',
                             'MarginL': '0',
                             'MarginR': '0',
                             'MarginV': '0',
                             'Encoding': '1',
                             }
        self.style_comment_art = {'Name': 'コメントアート',
                                  'Fontname': 'Yu Gothic',
                                  'Fontsize': str(style['comment_art']['font_size']),
                                  'PrimaryColour': color(style['comment_art']['color']),
                                  'SecondaryColour': '&HFF0000FF',
                                  'OutlineColour': color(style['comment_art']['outline_color']),
                                  'BackColour': '&HFF000000',
                                  'Bold': '-1',
                                  'Italic': '0',
                                  'Underline': '0',
                                  'StrikeOut': '0',
                                  'ScaleX': '128.5',
                                  'ScaleY': '129',
                                  'Spacing': '0',
                                  'Angle': '0',
                                  'BorderStyle': '1',
                                  'Outline': str(style['comment_art']['outline']),
                                  'Shadow': '0',
                                  'Alignment': '7',
                                  'MarginL': '0',
                                  'MarginR': '0',
                                  'MarginV': '0',
                                  'Encoding': '1',
                                  }

    def ass(self):
        def default_style():
            return f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {','.join(self.style_official.values())}
Style: {','.join(self.style_normal.values())}
Style: {','.join(self.style_comment_art.values())}

"""

        script_info = f'''[Script Info]
; Script generated by Aegisub 3.2.2
; http://www.aegisub.org/
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: Yes
Timing: 100.0000

[Aegisub Project Garbage]

'''

        events_header = '''[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

        ass_block_list = [script_info, default_style(), events_header, self.dialouges()]

        return ''.join(ass_block_list)

    def dialouges(self):
        self.build_dialogues()
        dialogue_list = [self.d_comment_art, self.d_official, self.d_vote, self.d_normal, self.d_bg]
        dialogue_list_string = []
        for dialogue in dialogue_list:
            for d in dialogue:
                dialogue_list_string.append(d.string())

        return '\n'.join(dialogue_list_string)

    def build_dialogues(self):
        self.reclassify_cmt()

        self.build_official()
        self.build_vote()
        self.build_comment_art()
        self.build_normal()

    # 获取评论信息并转成dict形式
    def get_data_raw(self):
        if self.platform == 'ニコニコ生放送':
            DOMTree = xml.dom.minidom.parse(self.source)
            root = DOMTree.documentElement

            if root.getElementsByTagName('LiveTitle'):
                # 是使用NCV下载的弹幕，从文档内容中获取生放标题
                self.title = root.getElementsByTagName('LiveTitle')[0].firstChild.data
                # NCV下载的弹幕时间参数有错误，需要用openTime来校正
                self.open_time = root.getElementsByTagName('OpenTime')[0].firstChild.data
            else:
                self.title = os.path.split(self.source)[1]
                self.title = os.path.splitext(self.title)[0]

            self.title = fix_invalid_file_name(self.title)

            chat = root.getElementsByTagName('chat')
            self.data_raw = []
            for c in chat:
                cmt_data = {'message': c.firstChild.data}
                for key, value in c.attributes.items():
                    cmt_data[key] = value

                if self.open_time:
                    cmt_data['vpos'] = (int(cmt_data['date']) - int(self.open_time)) * 100

                if cmt_data.get('date_usec'):
                    date_usec = cmt_data.get('date_usec')
                else:
                    date_usec = 0

                cmt_data['vpos'] = int(cmt_data['vpos']) + round(int(date_usec) / 10000)
                self.data_raw.append(cmt_data)
        elif self.platform == 'Zaiko':
            with open(source, 'r', encoding='utf-8') as f_source:
                chat = f_source.read()

            self.title = os.path.split(self.source)[1]
            self.title = os.path.splitext(self.title)[0]
            self.title = fix_invalid_file_name(self.title)

            self.data_raw = []
            index = 0

            non_duplicate_cmt_list = []
            for c in chat.split('\n'):
                try:
                    message = re.search('\{.*\}', c).group(0)
                    message = json.loads(message)
                except Exception as e:
                    continue

                data = message.get('data')
                if data:
                    data = json.loads(data)

                    text = data.get('text')
                    if text:
                        nickname = data.get('member', {}).get('nickname')

                        if nickname == '':
                            nickname = data.get('member', {}).get('uuid')

                        created_at = data.get('created_at')
                        created_at = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.000000Z')
                        created_at += datetime.timedelta(hours=9)
                        data['created_at_JST'] = created_at

                        data['name'] = nickname
                        data['message'] = text
                        data['vpos'] = created_at.timestamp() * 100

                        minimum_cmt_info = f"{data['vpos']}{nickname}{text}"
                        if minimum_cmt_info not in non_duplicate_cmt_list and not self.ng_pattern.search(
                                minimum_cmt_info):
                            non_duplicate_cmt_list.append(minimum_cmt_info)
                            if nickname == '(・D・)':
                                self.official.append(data)
                            else:
                                self.normal.append(data)
                                print(
                                    f"index：{index:5}|{datetime.datetime.strftime(created_at, '%Y-%m-%d %H:%M:%S')}|{text}")
                                index += 1

            print('\n请先选择一条评论，输入其index\n再输入希望它在视频中出现的时间点')

            while True:
                sample_index = int(input(f'index(0~{len(self.normal)}) = '))
                if 0 <= sample_index <= len(self.normal):
                    break
                else:
                    print('[错误]输入值不在范围之内，请重新输入')

            while True:
                sample_time = input('时间(x:xx:xx.xxx) = ')
                if re.search('\d{1,2}:\d{2}:\d{2}.\d{2,3}', sample_time):
                    break
                else:
                    print('[错误]时间格式错误，请重新输入')

            vpos_time_delta = self.normal[sample_index]['vpos'] - time_to_stamp(sample_time)

            for c in self.normal:
                c['vpos'] = round(c['vpos'] - vpos_time_delta)
            for c in self.official:
                c['vpos'] = round(c['vpos'] - vpos_time_delta)

            self.normal.sort(key=lambda x: x['vpos'])
            self.official.sort(key=lambda x: x['vpos'])

        elif self.platform == 'YouTube':
            with open(source, 'r', encoding='utf-8') as f_source:
                chat = json.load(f_source)

            self.title = os.path.split(self.source)[1]
            self.title = os.path.splitext(self.title)[0]
            self.title = fix_invalid_file_name(self.title)

            for c in chat:
                c['name'] = c.get('author', {}).get('name')
                c['vpos'] = round(c.get('time_in_seconds') * 100)
                c['message'] = re.sub(':\w+?:', '', c['message'])

                badges = c.get('author', {}).get('badges')
                if badges:
                    for badge in badges:
                        if badge['title'] == 'Owner':
                            self.official.append(c)
                            break
                else:
                    self.normal.append(c)
        elif self.platform == 'ASOBISTAGE':
            t_start = time.time()

            def asobi_time_to_vpos(a_time):
                vpos = datetime.datetime.strptime(a_time[:19], '%Y-%m-%d %H:%M:%S')
                return round(vpos.timestamp() * 100 + (int(a_time[20:23]) / 10))

            def extract_info(c_line):
                line = json.loads(c_line)
                c_data = line.get('data')
                if not c_data:
                    return
                comment = c_data['comment']

                c_time = line['time']
                line['vpos'] = asobi_time_to_vpos(c_time) - vpos_time_delta
                if line['vpos'] < 0:
                    return

                user_name = c_data.get('userName')
                line['name'] = c_data['userName']

                comment = ''.join(comment)
                comment = re.sub(':\(.*\)?:', '', comment)
                line['message'] = comment

                c_type = c_data['type']

                minimum_cmt_info = f"{round(line['vpos'] / 100)}{user_name}{comment}"
                if minimum_cmt_info not in non_duplicate_cmt_list and not self.ng_pattern.search(minimum_cmt_info):
                    non_duplicate_cmt_list.append(minimum_cmt_info)
                    if c_type == "official/send-comment":
                        self.official.append(line)
                    else:
                        self.normal.append(line)

            os.startfile(source)
            print('已打开原始文件\n请先选择一条评论作为调整弹幕时间的依据，输入其time值\n再输入希望它在视频中出现的时间点')

            while True:
                sample_time_asobi = input(f'time(xxxx-xx-xx xx:xx:xx.xxxxxxxxx)\n>')
                if re.search('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{9}', sample_time_asobi):
                    break
                else:
                    print('[错误]时间格式错误，请重新输入')

            while True:
                sample_time = input('时间(x:xx:xx.xxx)\n>')
                if re.search('\d{1,2}:\d{2}:\d{2}.\d{2,3}', sample_time):
                    break
                else:
                    print('[错误]时间格式错误，请重新输入')

            vpos_time_delta = asobi_time_to_vpos(sample_time_asobi) - time_to_stamp(sample_time)

            with open(source, 'r', encoding='utf-8') as f_source:
                chat = f_source.read()
            self.title = os.path.split(self.source)[1]
            self.title = os.path.splitext(self.title)[0]
            self.title = fix_invalid_file_name(self.title)

            non_duplicate_cmt_list = []

            chat = chat.split('\n')

            for i, c in enumerate(chat):

                try:
                    data = json.loads(c)
                except Exception as e:
                    continue

                chat_history = data.get('all')
                if chat_history:

                    for h_c in chat_history:
                        extract_info(h_c)
                else:
                    extract_info(c)

            self.normal.sort(key=lambda x: x['vpos'])
            self.official.sort(key=lambda x: x['vpos'])

            print(f'out: {stamp_to_time(round((time.time() - t_start) * 100))}')
            print(f"normal: {len(self.normal)}")
            print(f"official: {len(self.official)}")
        elif self.platform == 'ニコニコチャンネルプラス':
            def nchp_time_to_vpos(time_nchp):
                import datetime
                return round(datetime.datetime.strptime(time_nchp, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp() * 100)

            chat, operator_broadcasts_list = self.download_comment_nchp()

            non_duplicate_cmt_list = []

            for c in chat:
                created_at = c.get('created_at')
                vpos = nchp_time_to_vpos(created_at) - self.open_time
                if vpos < 0:
                    continue

                c['vpos'] = vpos

                c['name'] = c.get('nickname')

                if c.get('nickname') == 'ゲスト':
                    c['name'] = c.get('id')

                minimum_cmt_info = f"{round(c['vpos'] / 100)}{c['message']}"

                if c.get('priority'):
                    if not self.official_name:
                        self.official_name = c['name']
                    if minimum_cmt_info not in non_duplicate_cmt_list:
                        non_duplicate_cmt_list.append(minimum_cmt_info)
                        self.official.append(c)
                else:
                    self.normal.append(c)

            for c in operator_broadcasts_list:
                if type(c) == list:

                    for q in c:

                        if not q['elapsed_show_time']:
                            continue
                        q['vpos'] = round(q['elapsed_show_time'] / 10)
                        self.vote.append(q)
                    continue
                created_at = c.get('created_at')
                c['vpos'] = nchp_time_to_vpos(created_at) - self.open_time
                c['name'] = self.official_name

                c_type = c.get('type')

                if c_type == 'announcement':
                    # 精简信息，提高去重速度
                    minimum_cmt_info = f"{round(c['vpos'] / 100)}{c['message']}"

                    if minimum_cmt_info not in non_duplicate_cmt_list:
                        non_duplicate_cmt_list.append(minimum_cmt_info)
                        self.official.append(c)
                elif c_type == 'questionnaire':

                    self.vote.append(c)

            self.normal.sort(key=lambda x: x['vpos'])
            self.official.sort(key=lambda x: x['vpos'])
            self.vote.sort(key=lambda x: x['vpos'])
        elif self.platform == 'Openrec':

            chats = self.download_comment_openrec()

            for c in chats:
                c['name'] = c.get('user', {}).get('nickname')
                if c['user']['is_official']:
                    self.official.append(c)
                else:
                    self.normal.append(c)

    def download_comment_nchp(self):

        headers = {
            'fc_use_device': 'null',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36', }

        content_code = self.source.split('/')[-1]
        url_page = f'https://nfc-api.nicochannel.jp/fc/video_pages/{content_code}'
        url_token = f'https://nfc-api.nicochannel.jp/fc/video_pages/{content_code}/comments_user_token'

        token = json.loads(requests.get(url_token, headers=headers).text)['data']['access_token']

        response_video_pages = requests.get(url_page, headers=headers)
        video_pages = json.loads(response_video_pages.text)

        group_id = video_pages['data']['video_page']['video_comment_setting']['comment_group_id']

        json_data = {'token': token, 'group_id': group_id}

        self.title = fix_invalid_file_name(video_pages['data']['video_page']['title'])
        self.title = fix_invalid_file_name(self.title)
        open_time = video_pages['data']['video_page']['live_started_at']
        self.open_time = round(datetime.datetime.strptime(open_time, '%Y-%m-%d %H:%M:%S').timestamp() * 100)

        number_of_comments = video_pages['data']['video_page']['video_aggregate_info']['number_of_comments']
        number_of_comments_for_dl = number_of_comments + 500

        video_questionnaires = video_pages['data']['video_page']['video_questionnaires']

        url_comment = f'https://comm-api.sheeta.com/messages.history?limit={number_of_comments_for_dl}'

        comments = json.loads(requests.post(url_comment, headers=headers, json=json_data).text)

        operator_broadcasts_list = json.loads(
            requests.post('https://comm-api.sheeta.com/groups.operator-broadcasts.list', headers=headers,
                          json=json_data).text)

        if self.save:
            with open(f"{self.title} video pages.json", 'w', encoding='utf-8') as f_dl:
                f_dl.write(json.dumps(video_pages, ensure_ascii=False))

            with open(f"{self.title}.json", 'w', encoding='utf-8') as f_dl:
                f_dl.write(json.dumps(comments, ensure_ascii=False))

            with open(f"{self.title} operator broadcasts list.json", 'w', encoding='utf-8') as f_dl_o:
                f_dl_o.write(json.dumps(operator_broadcasts_list, ensure_ascii=False))

        operator_broadcasts_list.append(video_questionnaires)

        return comments, operator_broadcasts_list

    def download_comment_openrec(self):
        def reformat_time_openrec(time):
            time_struct = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+09:00')
            tdelta = datetime.timedelta(hours=9)
            res = time_struct - tdelta
            return datetime.datetime.strftime(res, '%Y-%m-%dT%H:%M:%S.000Z')

        def cal_vpos(time, time_start):
            time = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+09:00')
            time_start = datetime.datetime.strptime(time_start, '%Y-%m-%dT%H:%M:%S+09:00')
            return int((time - time_start).total_seconds() * 100)

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36'
        }

        live_id = self.source.split('/')[-1]

        response = requests.get(f'https://public.openrec.tv/external/api/v5/movies/{live_id}', headers=headers)
        page = json.loads(response.content)
        created_at = page['created_at']  # 直播创建时间
        started_at = page['started_at']  # 直播实际开始时间

        self.title = page['title']
        self.title = fix_invalid_file_name(self.title)

        # 获取评论时用到的时间时UTC+0的时间，需要把从page页获取到的时间从UTC+9转成UTC+0再用
        # 以直播创建时间作为第一个获取评论的起始时间
        get_from_created_at = reformat_time_openrec(created_at)

        comments_id = []  # 存放评论id，用于去重
        comments = []  # 存放完整评论
        keep_get = True
        while keep_get:
            url_comment_from = f'https://public.openrec.tv/external/api/v5/movies/{live_id}/chats?from_created_at={get_from_created_at}'

            res_comments_from = requests.get(url_comment_from, headers=headers)
            comments_ori = json.loads(res_comments_from.content)

            # 找到这一次获取评论中时间最晚的那一条的时间，用作下一次获取评论的起始时间
            latest_post_time = datetime.datetime.strptime(comments_ori[0]['posted_at'], '%Y-%m-%dT%H:%M:%S+09:00')

            found_new_comment = False
            for c in comments_ori:
                posted_at = c['posted_at']  # 评论发布时间
                latest_post_time = max(datetime.datetime.strptime(posted_at, '%Y-%m-%dT%H:%M:%S+09:00'),
                                       latest_post_time)
                vpos = cal_vpos(posted_at, started_at)

                cmt_id = c['id']  # 评论id，用于去重

                if cmt_id not in comments_id:
                    found_new_comment = True
                    c['vpos'] = vpos if vpos > 0 else 0
                    comments_id.append(cmt_id)
                    comments.append(c)

            get_from_created_at = latest_post_time - datetime.timedelta(hours=9)
            get_from_created_at = datetime.datetime.strftime(get_from_created_at, '%Y-%m-%dT%H:%M:%S.000Z')

            if not found_new_comment and len(comments_ori) < 5:
                keep_get = False

        comments.sort(key=lambda x: x['vpos'])

        if self.save:
            with open(f"{self.title}.json", 'w', encoding='utf-8') as f_dl:
                f_dl.write(json.dumps(comments, ensure_ascii=False))

        return comments

    # 评论分类
    def reclassify_cmt(self):
        self.get_data_raw()

        if self.platform == 'ニコニコ生放送':
            for c in self.data_raw:
                # 屏蔽弹幕
                if not self.ng_pattern.search(c['message']):
                    if re.search(
                            '(/trialpanel|/nicoad|/info|/disconnect|/play |/commentlock|/gift|/jump|/redirect|/spi)',
                            c['message']):
                        self.other.append(c)
                    elif c.get('premium') and re.search('([37])', c.get('premium')):
                        self.official.append(c)
                        if '/vote' in c['message']:
                            self.vote.append(c)

                    elif re.search('\n', c['message']):
                        c['layer'] = 10
                        self.comment_art.append(c)
                    elif c.get('mail') and re.search(r'(\bue|\bshita)', c.get('mail')):
                        self.normal_still.append(c)
                    else:
                        self.normal.append(c)

    def build_official(self):
        default_time_delta = 15 * 100  # 15s

        for i, c in enumerate(self.official):
            if not c['message']:
                continue

            d = Dialogue()
            d.layer = '6'
            d.style = self.style_official['Name']

            if '/clear' in c['message'] or '/vote' in c['message']:
                continue

            d.start = stamp_to_time(c['vpos'])
            d.end = stamp_to_time(int(c['vpos']) + default_time_delta)
            if self.platform == 'ニコニコチャンネルプラス':

                if c.get('end_time_in_seconds'):
                    d.end = stamp_to_time(int(c['vpos']) + c.get('end_time_in_seconds') * 100)

            if i < len(self.official) - 2:
                c_next = self.official[i + 1]
                # /clear: 手动清除命令 /perm: 不会经过一定时间后自动消失
                if '/clear' in c_next['message'] or '/perm' in c['message'] or (
                        int(c_next['vpos']) - int(c['vpos'])) < default_time_delta:
                    d.end = stamp_to_time(c_next['vpos'])

            d.vpos_in = c['vpos']
            d.vpos_out = time_to_stamp(d.end)

            c['message'] = re.sub('/perm ', '', c['message'])

            text_length = len(c['message'])
            if 'href' in c['message']:
                msg = re.search('<.*>', c['message']).group(0)
                msg = msg.replace('&', '&amp;')
                doc = xml.dom.minidom.parseString(msg)
                text = doc.getElementsByTagName('u')[0].firstChild.data
                href = doc.getElementsByTagName('a')[0].getAttribute('href')
                text_length = max(len(text), round(len(href) / 2))

                c['message'] = f'{text}\\N{href}'

            d.text = c['message']

            name = c.get('name')
            if name and self.platform != 'ニコニコチャンネルプラス':
                d.name = name
                if not self.platform != 'ニコニコチャンネルプラス':
                    d.text = f"{name}「{c['message']}」"
                    text_length += len(f"{name}「」")
            else:
                d.name = '運営'

            max_text_width_available = WIDTH - 2 * (
                    style['official']['background']['marginH'] + style['official']['background']['paddingH'])
            max_font_size_available = math.floor(max_text_width_available / text_length)

            font_size = style['official']['font_size']
            if font_size > max_font_size_available:
                font_size = max_font_size_available
                d.tag.set_font_size(font_size)

            d.font_size = font_size

            self.d_official.append(d)
            print(f"[OFFICIAL] {d.start} {d.end} {stamp_to_time(d.vpos_out - d.vpos_in)} {d.text}")

            # 生成背景
            row_cnt = len(re.findall(r'\\N', d.text)) + 1
            d.text_row_cnt = row_cnt

            d_bg = deepcopy(d)
            d_bg.tag.set_pos(round(WIDTH / 2), style['official']['background']['marginV'])
            d_bg.draw_bg_official(font_size)

            self.d_bg.append(d_bg)

    def build_vote(self):
        if not self.vote:
            return

        question_id_list = []

        if self.platform == 'ニコニコチャンネルプラス':
            for cmt in self.vote:
                if not cmt.get('question'):

                    if cmt['payload']['type'] == 'questionnaire_post_questions' and cmt['payload'][
                        'video_questionnaire_id'] not in question_id_list:
                        question_id_list.append(cmt['payload']['video_questionnaire_id'])

        for i, cmt in enumerate(self.vote):

            if self.platform != 'ニコニコチャンネルプラス':
                vote_message = cmt['message'].split(' ')
                if '/vote start' not in cmt['message']:
                    continue

                # 处理选项中带空格的情况（待测试）
                if re.search('" "', cmt['message']):
                    q_and_c = re.search('/vote start (.*)', cmt['message']).group(1)
                    q_and_c = re.split(' "|" "', q_and_c)
                    q_and_c[len(q_and_c) - 1] = re.sub('"', '', q_and_c[len(q_and_c) - 1])
                    question, *choices = q_and_c
                else:
                    question = vote_message[2]
                    choices = vote_message[3:]

            else:
                if cmt.get('question'):

                    if cmt.get('id') in question_id_list:
                        continue
                    question = cmt.get('question')

                    choices = cmt.get('video_questionnaire_options')
                else:

                    payload = cmt.get('payload')
                    video_questionnaire_id = payload.get('video_questionnaire_id')

                    if payload.get('type') != 'questionnaire_post_questions':
                        continue

                    question = payload.get('question')
                    choices = payload.get('video_questionnaire_options')
                choices.sort(key=lambda x: x['id'])

            self.vote_cnt += 1

            d_question = Dialogue()
            d_question.layer = '7'
            d_question.start = stamp_to_time(cmt['vpos'])

            d_question.name = 'アンケート 問題'
            d_question.text = question
            d_question.style = self.style_official['Name']

            if not cmt.get('question'):
                for j, cmt_search in enumerate(self.vote[i:]):
                    if self.platform != 'ニコニコチャンネルプラス':
                        if '/vote showresult' in cmt_search['message']:
                            cmt_result = cmt_search
                        elif '/vote stop' in cmt_search['message']:
                            cmt_stop = cmt_search
                            break
                    else:
                        if cmt_search['payload']['video_questionnaire_id'] == video_questionnaire_id:
                            if cmt_search['payload']['type'] == 'questionnaire_result':
                                cmt_result = cmt_search
                            elif cmt_search['payload']['type'] == 'questionnaire_hide_result':
                                cmt_stop = cmt_search
                                break
                d_question.end = stamp_to_time(cmt_stop['vpos'])
            else:
                d_question.end = stamp_to_time(round(cmt['elapsed_hide_result_time'] / 10))
                cmt_result = True

            width_text_question = len(question) * style['vote']['question']['font_size']

            height_bg_question = style['vote']['question']['font_size'] + style['vote']['question']['bg'][
                'paddingV'] * 2
            height_bg_choice = style['vote']['choice']['font_size'] + style['vote']['choice']['bg']['paddingV'] * 2

            height_choices_section = height_bg_choice * len(choices) + style['vote']['choice']['bg']['marginV'] * (
                    len(choices) - 1)

            x_bottom_left_question = style['vote']['container']['marginH'] + style['vote']['container'][
                'padding_left'] + style['vote']['question']['bg']['paddingH']
            y_bottom_left_question = style['vote']['container']['marginV'] + style['vote']['container'][
                'padding_bottom'] \
                                     + height_choices_section + style['vote']['question']['bg']['margin_bottom'] + \
                                     style['vote']['question']['bg']['paddingV']

            x_question = x_bottom_left_question
            y_question = HEIGHT - y_bottom_left_question

            # 令投票区域不超出画面左半边的，问题的最大长度
            max_width_text_question_available = math.floor((WIDTH / 2) - (x_question * 2))
            if width_text_question > max_width_text_question_available:
                width_text_question = max_width_text_question_available
                max_font_size_question_available = math.floor(max_width_text_question_available / len(question))
                fscx_value = round(max_font_size_question_available / style['vote']['question']['font_size'] * 100)
                d_question.tag.other += rf'\fscx{fscx_value}'

            d_question.tag.set_font_name(style['vote']['question']['font_name'])
            d_question.tag.set_font_size(style['vote']['question']['font_size'])

            d_question.tag.set_alignment(1)
            d_question.tag.set_pos(x_question, y_question)

            self.d_vote.append(d_question)

            print(f'\n[VOTE][QUESTION] {d_question.start} {d_question.end} {d_question.text}')

            max_width_text_choice = 0
            for i, choice in enumerate(choices):
                if self.platform != 'ニコニコチャンネルプラス':
                    max_width_text_choice = max(max_width_text_choice,
                                                len(choice) * style['vote']['choice']['font_size'])
                else:
                    max_width_text_choice = max(max_width_text_choice,
                                                len(choice['text']) * style['vote']['choice']['font_size'])

            if self.platform != 'ニコニコチャンネルプラス':
                width_text_total = max_width_text_choice + style['vote']['result']['margin_left'] + len('100.0%') * \
                                   style['vote']['choice']['font_size']
            else:
                width_text_total = max_width_text_choice + style['vote']['result']['margin_left'] + 7 * \
                                   style['vote']['choice']['font_size']

            width_text_total = max(width_text_total, width_text_question)
            width_bg_total = width_text_total + style['vote']['question']['bg']['paddingH'] * 2

            # 添加背景
            d_bg_question = deepcopy(d_question)
            d_bg_question.tag.other = ''

            x_bg_question = x_question - style['vote']['question']['bg']['paddingH']
            y_bg_bottom_left_question = y_bottom_left_question - style['vote']['question']['bg']['paddingV']
            y_bg_question = HEIGHT - y_bg_bottom_left_question
            d_bg_question.tag.set_pos(x_bg_question, y_bg_question)

            d_bg_question.draw_bg_vote_question(width_bg_total, height_bg_question)

            self.d_bg.append(d_bg_question)

            d_bgs_result = []
            # 处理选项
            for i, choice in enumerate(choices):
                d_choice = deepcopy(d_question)
                d_choice.tag.other = ''

                d_choice.name = 'アンケート 選択肢'

                if self.platform != 'ニコニコチャンネルプラス':
                    d_choice.text = choice
                else:
                    d_choice.text = choice['text']

                d_choice.tag.set_font_name(style['vote']['choice']['font_name'])
                d_choice.tag.set_font_size(style['vote']['choice']['font_size'])

                x_choice = x_question
                y_bottom_left_choice = style['vote']['container']['marginV'] + style['vote']['container'][
                    'padding_bottom'] \
                                       + (len(choices) - 1 - i) * (
                                               height_bg_choice + style['vote']['choice']['bg']['marginV']) + \
                                       style['vote']['choice']['bg']['paddingV']
                y_choice = HEIGHT - y_bottom_left_choice

                d_choice.tag.set_alignment(1)
                d_choice.tag.set_pos(x_choice, y_choice)

                self.d_vote.append(d_choice)

                print(f'[VOTE]  [CHOICE] {d_choice.start} {d_choice.end} {d_choice.text}')

                # 添加背景
                d_bg_choice = deepcopy(d_choice)

                x_bg_choice = x_bg_question
                y_bg_choice = y_choice + style['vote']['choice']['bg']['paddingV']
                d_bg_choice.tag.set_pos(x_bg_choice, y_bg_choice)

                d_bg_choice.draw_bg_vote_choice(width_bg_total, height_bg_choice)

                d_bgs_result.append(deepcopy(d_bg_choice))
                self.d_bg.append(d_bg_choice)

            # 处理结果
            if cmt_result:
                d_result_base = Dialogue()
                d_result_base.layer = '6'

                d_result_base.style = self.style_official['Name']
                d_result_base.name = 'アンケート 結果'

                if not cmt.get('question'):
                    d_result_base.start = stamp_to_time(cmt_result['vpos'])
                    d_result_base.end = stamp_to_time(cmt_stop['vpos'])
                else:
                    d_result_base.start = stamp_to_time(round(cmt['elapsed_result_time'] / 10))
                    d_result_base.end = stamp_to_time(round(cmt['elapsed_hide_result_time'] / 10))

                # 添加投票倒计时

                if self.platform != 'ニコニコチャンネルプラス':
                    results = cmt_result['message'].split(' ')[3:]
                else:
                    if not cmt.get('question'):
                        results = cmt_result['payload']['video_questionnaire_results']

                        if len(results) != len(choices):
                            option_id_list = [r['id'] for r in results]

                            for choice in choices:
                                if choice['id'] not in option_id_list:
                                    res_add = deepcopy(results[0])
                                    option_id_list.append(choice['id'])
                                    if res_add.get('count_video_questionnaire_user_answers') is not None:
                                        res_add['count_video_questionnaire_user_answers'] = 0
                                        res_add['id'] = choice['id']
                                        res_add['percentage'] = 0
                                    results.append(res_add)
                        results.sort(key=lambda x: x['id'])
                    else:
                        results = choices

                sum_result_value = 0
                for i, result_value in enumerate(results):
                    d_result = deepcopy(d_result_base)

                    if self.platform != 'ニコニコチャンネルプラス':
                        result_value = int(result_value) / 10

                        result_value = f"{result_value}%"
                        d_result.text = result_value
                    else:
                        if not cmt.get('question'):
                            if i < (len(results) - 1):
                                result_value = round(result_value['percentage'], 1)
                                sum_result_value += result_value
                            else:
                                result_value = round(100 - sum_result_value, 1)

                            result_value = f"{result_value}%"
                            count_video_questionnaire_user_answers = results[i].get(
                                'count_video_questionnaire_user_answers')

                            if count_video_questionnaire_user_answers is not None:
                                d_result.text = fr"{count_video_questionnaire_user_answers}票/{result_value}"
                            else:
                                d_result.text = fr"{result_value}"
                        else:

                            if result_value['video_questionnaire_result'] is not None:
                                result_value = f"{result_value['video_questionnaire_result']['percentage']}%"
                            else:
                                result_value = '0%'
                            d_result.text = result_value

                    d_result.tag.set_font_size(style['vote']['choice']['font_size'])

                    x_result = x_question + width_text_total

                    y_bottom_left_result = style['vote']['container']['marginV'] + style['vote']['container'][
                        'padding_bottom'] \
                                           + (len(choices) - 1 - i) * (
                                                   height_bg_choice + style['vote']['choice']['bg']['marginV'
                                                                                                    '']) + \
                                           style['vote']['choice']['bg']['paddingV']
                    y_result = HEIGHT - y_bottom_left_result

                    d_result.tag.set_alignment(3)
                    d_result.tag.set_pos(x_result, y_result)

                    self.d_vote.append(d_result)
                    print(f'[VOTE]  [RESULT] {d_result.start} {d_result.end} {d_result.text}')

                    d_bg_result = d_bgs_result[i]
                    d_bg_result.start = d_result.start
                    d_bg_result.end = d_result.end
                    d_bg_result.draw_bg_vote_result(x_bg_question, width_bg_total, result_value)

                    self.d_bg.append(d_bg_result)

                # 投票截至倒计时
                d_countdown = deepcopy(d_bg_question)
                d_countdown.tag.other = ''
                d_countdown.layer = '6'
                d_countdown.start = stamp_to_time(cmt['vpos'])

                d_countdown.name = 'アンケート countdown'

                if not cmt.get('question'):
                    d_countdown.end = stamp_to_time(cmt_result['vpos'])
                else:
                    d_countdown.end = stamp_to_time(round(cmt['elapsed_result_time'] / 10))

                d_countdown.set_default_bg_style(style['vote']['countdown'])
                d_countdown.tag.clip = rf"\clip(0, 0, {x_bg_question + width_bg_total}, {HEIGHT})\t(\clip(0, 0, {x_bg_question}, {HEIGHT}))"
                self.d_bg.append(d_countdown)

    def build_comment_art(self):
        if not self.comment_art:
            return

        single_c_art_index_list = []
        total_length = 0
        for i in range(len(self.comment_art)):
            max_length = 0
            for line in self.comment_art[i]['message'].split('\n'):
                max_length = max(max_length, len(line))

            if i == 0:
                self.ca_cnt += 1

                single_c_art_index_list.append(0)
                total_length = max(total_length, max_length)
                self.comment_art[i]['total_length'] = total_length
            elif abs(int(self.comment_art[i]['vpos']) - int(self.comment_art[i - 1]['vpos'])) < 100:
                # ca由多段弹幕组成，当前弹幕与上一条同属于一个CA
                self.comment_art[i]['vpos'] = self.comment_art[i - 1]['vpos']
                self.comment_art[i]['layer'] = self.comment_art[i]['layer'] + 1
                if max_length > total_length:
                    total_length = max_length
                    for index in single_c_art_index_list:
                        self.comment_art[index]['total_length'] = total_length
                self.comment_art[i]['total_length'] = total_length
                single_c_art_index_list.append(i)
            elif abs(int(self.comment_art[i]['vpos']) - int(self.comment_art[i - 1]['vpos'])) >= 100:

                self.ca_cnt += 1

                total_length = max_length
                self.comment_art[i]['total_length'] = total_length
                single_c_art_index_list = [i]

        for i, c_art in enumerate(self.comment_art):
            max_length = 0
            for line in c_art['message'].split('\n'):
                max_length = max(max_length, len(line))

        for i, cmt in enumerate(self.comment_art):
            d = Dialogue()

            d.layer = str(cmt['layer'])

            d.start = stamp_to_time(cmt['vpos'])
            d.end = stamp_to_time((int(cmt['vpos']) + style['displayed_time'] * 100))
            d.style = self.style_comment_art['Name']

            if cmt.get('name'):
                d.name = cmt.get('name')
            else:
                d.name = cmt.get('user_id')

            line_height = style['comment_art']['font_size']
            command_list = []
            if cmt.get('mail'):
                command_list = cmt.get('mail').split(' ')
                for command in command_list:
                    if command in d.tag.color_command:
                        d.tag.set_color(d.tag.color_command[command])
                    elif re.search('#.{6}', command):
                        d.tag.set_color(command)
                    elif command == 'small':
                        line_height = round(line_height * 0.6)
                        d.tag.set_font_size(line_height)
                    elif command == 'big':
                        line_height = round(line_height * 1.47)
                        d.tag.set_font_size(line_height)
                    elif command == 'mincho':
                        d.tag.set_font_name('Yu Mincho')
                    elif command == 'gothic':
                        d.tag.set_font_name('Yu Gothic')

            c_art = cmt['message'].split('\n')

            width_c_art_total = 0
            for line in c_art:
                width_c_art_total = max(len(line) * style['comment_art']['font_size'], width_c_art_total)

            for j, line in enumerate(c_art):

                d_art_line = deepcopy(d)
                d_art_line.text = line

                if 'ue' in command_list:
                    x = round((WIDTH - cmt['total_length'] * line_height) / 2)
                    y = j * line_height
                    d_art_line.tag.set_pos(x, y)
                else:
                    x1 = WIDTH
                    x2 = -(cmt['total_length'] * style['comment_art']['font_size'])
                    y = j * line_height
                    d_art_line.tag.set_move(x1, x2, y)

                self.d_comment_art.append(d_art_line)

    def build_normal(self):
        line_height = style['font_size'] + style['spacing']

        row_cnt_base = style['row_cnt_base']

        ans = HEIGHT + style['spacing'] - line_height / 2
        ans = ans / line_height
        row_cnt_inserted = math.floor(ans)

        row_cnt = row_cnt_base + row_cnt_inserted

        # 创建一个长度等于弹幕总轨道数的列表，存放各轨道的最新弹幕
        cmt_in_row = [None for _ in range(row_cnt)]

        for cmt in self.normal:
            if not cmt['message']:
                continue
            d = Dialogue()
            d.has_been_moved_down = False
            d.raw = cmt
            d.start = stamp_to_time(cmt['vpos'])
            d.end = stamp_to_time((int(cmt['vpos']) + style['displayed_time'] * 100))
            d.style = self.style_normal['Name']

            name = cmt.get('name')
            if name:
                d.name = name
            else:
                d.name = cmt.get('user_id')

            self.viewer_cnt.append(d.name)

            d.text = cmt['message']

            text_length = len(cmt['message']) * style['font_size']
            speed = (text_length + WIDTH) / (style['displayed_time'] * 100)
            d.speed = speed

            # 调整非会员弹幕的透明度
            if cmt.get('premium') and re.search('(24|25)', cmt.get('premium')):
                d.tag.set_opacity(1 - style['color']['a'] * 0.6)
                d.tag.set_outline_opacity(1 - style['outline_color']['a'] * 0.6)
                # print(cmt)

            # 分配轨道
            row = None
            min_collision = float('inf')  # 无穷大
            # 依次与每条轨道上的最新弹幕进行碰撞检测，找出最大重叠长度最小的轨道作为当前评论的最优轨道
            for i in range(row_cnt):
                c = self.collision(cmt_in_row[i], cmt)  # 与该轨道最新弹幕的最大重叠长度
                # 不会发生碰撞，立即退出检测
                if c <= 0:
                    row = i
                    break
                elif c < min_collision:
                    min_collision = c
                    row = i
            cmt_in_row[row] = cmt

            x1 = WIDTH
            x2 = -text_length
            if row < row_cnt_base:
                y = (style['font_size'] + style['spacing']) * row
            else:
                y = (style['font_size'] + style['spacing']) * (row - row_cnt_base + (1 / 2))

            y = round(y)

            d.tag.set_move(x1, x2, y)

            # 处理command
            if cmt.get('mail'):
                command_list = cmt.get('mail').split(' ')
                d.tag.translate_command(command_list)

            self.d_normal.append(d)

        self.cnt += len(self.d_normal)

        self.avoid_overlapping_with_official_comment()

    def avoid_overlapping_with_official_comment(self):
        if self.d_official:
            for i, d in enumerate(self.d_normal):
                d.vpos_in = time_to_stamp(d.start)
                d.vpos_out = time_to_stamp(d.end)
                speed = d.speed

                x1 = d.tag.x1
                x2 = d.tag.x2
                y = d.tag.y

                if d.vpos_out <= self.d_official[0].vpos_in or d.vpos_in >= self.d_official[-1].vpos_out:
                    continue
                else:
                    for j, d_official in enumerate(self.d_official):
                        ans = d_official.font_size * d_official.text_row_cnt + \
                              style['official']['background'][
                                  'paddingV'] * 2  # 运营评论背景高度
                        height_move_down = ans + style['official']['background']['marginV'] * 2

                        if (y + height_move_down + style['font_size']) > HEIGHT:
                            continue

                        if d.vpos_in < d_official.vpos_in < d.vpos_out or d.vpos_in < d_official.vpos_out < d.vpos_out:
                            d_split_1 = deepcopy(d)
                            if d.vpos_in < d_official.vpos_in < d.vpos_out:
                                """
                                    |運営コメント|
                                |コメント|
                                """

                                d.end = d_official.start
                                d_split_1.start = d_official.start

                                d_distance_traveled_when_official_frame_in = speed * (d_official.vpos_in - d.vpos_in)
                                d_pos_when_official_frame_in = x1 - d_distance_traveled_when_official_frame_in
                                d_pos_when_official_frame_in = round(d_pos_when_official_frame_in)

                                d.tag.set_move(x1, d_pos_when_official_frame_in, y)
                                d_split_1.tag.set_move(d_pos_when_official_frame_in, x2, y + height_move_down)
                                d_split_1.has_been_moved_down = True
                            elif d.vpos_in < d_official.vpos_out < d.vpos_out:
                                """
                                |運営コメント|
                                      |コメント|
                                """

                                d.end = d_official.end
                                d_split_1.start = d_official.end

                                d_distance_traveled_when_official_frame_out = speed * (d_official.vpos_out - d.vpos_in)
                                d_pos_when_official_frame_out = x1 - d_distance_traveled_when_official_frame_out
                                d_pos_when_official_frame_out = round(d_pos_when_official_frame_out)

                                d.tag.set_move(x1, d_pos_when_official_frame_out, y + height_move_down)
                                d_split_1.tag.set_move(d_pos_when_official_frame_out, x2, y)

                                d.has_been_moved_down = True

                            self.d_normal.insert(i + 1, d_split_1)
                            break
                        elif d_official.vpos_in <= d.vpos_in and d.vpos_out <= d_official.vpos_out:
                            """
                            |   運営コメント   |
                                |コメント|
                            """

                            if not d.has_been_moved_down:
                                d.tag.set_move(x1, x2, y + height_move_down)
                            break

    def collision(self, first, second):
        """
        检测两条弹幕处于统一轨道时是否会发生碰撞，返回它们在滚动过程中重叠长度(像素）的最大值
        若这个最大值<=0，说明它们不会发生碰撞
        :param first: 轨道内的最新弹幕
        :param second: 尚未分配轨道的当前弹幕。要求其入镜时间在前者之后，所以需要提前对所有评论按入镜时间排序
        :return: 两者重叠长度的最大值
        """

        def collision_at_start():
            """
            :return: 后者入镜时与前者重叠的长度(像素）
            """
            length_first = len(first['message']) * style['font_size']  # 前者文字长度

            speed_first = (WIDTH + length_first) / (style['displayed_time'] * 100)  # 弹幕滚动速度(像素/0.01s)
            time_delta = second['vpos'] - first['vpos']  # 两条弹幕出现时间点的时间差
            distance_traveled_first = speed_first * time_delta  # 后者开始出现时前者走过的距离(像素）

            return length_first - distance_traveled_first

        def collision_at_end():
            """
            :return: 前者出镜时与后者重叠的长度(像素）
            """

            first_vpos_frame_out = first['vpos'] + style['displayed_time'] * 100
            length_second = len(second['message']) * style['font_size']

            speed_second = (WIDTH + length_second) / (style['displayed_time'] * 100)
            time_delta = first_vpos_frame_out - second['vpos']
            distance_traveled_second = speed_second * time_delta
            return distance_traveled_second - WIDTH

        # 如果当前轨道有过弹幕
        if first:
            return max(collision_at_start(), collision_at_end())
        else:
            return 0


script_path = os.path.split(os.path.realpath(__file__))[0]

with open(f'{script_path}\style.json', 'r', encoding='utf-8') as f_style:
    style = json.load(f_style)

row_cnt_base = style['row_cnt_base']

WIDTH = style['video_width']
HEIGHT = style['video_height']

description = """将部分直播平台的实时评论转换成能以弹幕形式在播放器中显示的ass字幕格式
支持的平台:
    ニコニコチャンネルプラス/Openrec            直接输入直播页面链接
    ASOBISTAGE/ニコニコ生放送/YouTube/Zaiko    需要提前下载评论文件到本地"""
parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-p', '--platform', type=str, required=True,
                    help='''指定直播平台
                    a: ASOBISTAGE
                    n: ニコニコ生放送
                    nchp: ニコニコチャンネルプラス
                    o: Openrec
                    y: YouTube
                    z: Zaiko''')

parser.add_argument('source', type=str,
                    help='''指定评论源
                    输入直播链接 ニコニコチャンネルプラス/Openrec
                    输入本地评论文件路径 ASOBISTAGE/ニコニコ生放送/YouTube/Zaiko''')

parser.add_argument('-mr', '--max_row_cnt', type=int, default=11, help='指定画面中能容纳的最多弹幕轨道数 [默认为11]')
parser.add_argument('-s', '--save', action='store_true', help='保存原始评论文件（Openrec/ニコニコチャンネルプラス） [默认为否]')
parser.add_argument('-t', '--top_viewer', type=int, default=0, help='显示发送弹幕数Top n的观众 [默认n为0 即不显示]')

args = parser.parse_args()

platform = args.platform
if platform == 'a':
    platform = 'ASOBISTAGE'
elif platform == 'n':
    platform = 'ニコニコ生放送'
elif platform == 'nchp':
    platform = 'ニコニコチャンネルプラス'
elif platform == 'o':
    platform = 'Openrec'
elif platform == 'y':
    platform = 'YouTube'
elif platform == 'z':
    platform = 'Zaiko'

source = args.source
row_cnt_base = args.max_row_cnt
style['row_cnt_base'] = row_cnt_base

style['font_size'] = math.floor((HEIGHT + style['spacing']) / style['row_cnt_base'] - style['spacing'])
style['comment_art']['font_size'] = math.floor((HEIGHT / 38) / 0.63)

cmt = Comment()

cmt.save = args.save

cmt.platform = platform
cmt.source = source

ass = cmt.ass()

keep_building = False

print()
print(f"        平台: {cmt.platform}")
print(f"        标题: {cmt.title}")

print(f"      弹幕数: {len(cmt.normal)}")
print(f"  运营评论数: {len(cmt.d_official)}")
print(f"      投票数: {cmt.vote_cnt}")
print(f"CommentArt数: {cmt.ca_cnt}")

viewer_counter = Counter(cmt.viewer_cnt)
print()
print(f"发过弹幕的观众数: {len(viewer_counter)}")
print(f"平均每人发送弹幕: {round(len(cmt.normal) / len(viewer_counter), 1)}条")

top_cnt = args.top_viewer
if top_cnt:
    print(f"发送弹幕数前{top_cnt}的观众:")
    for name, c_cnt in viewer_counter.most_common(top_cnt):
        print(f"{c_cnt:4}条 {name}")

with open(f"{cmt.title}.ass", 'w', encoding='utf_8_sig') as f_out:
    f_out.write(ass)
