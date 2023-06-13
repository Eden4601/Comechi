Comechi
===
简介
---
Comechi能够将部分平台的直播评论转换成ass格式字幕文件，使用本地播放器加载得到的文件后评论会以弹幕的形式显示。

目前支持的平台有：ASOBISTAGE / ニコニコ生放送 / ニコニコチャンネルプラス / Openrec / YouTube / Zaiko



安装
---
1. 安装Python 3.8及以上的版本
2. 安装requests库
3. 将comechi.py与style.json下载到本地并确保它们处于相同路径
4. 将comechi.py所在路径添加进系统环境变量的PATH里


使用方法
---
1. 在目标文件夹的地址栏内输入cmd，回车
2. 在呼出的命令行窗口内按下方格式输入命令
```comechi.py -p 平台 评论源```

关于评论源，ニコニコチャンネルプラス和Openrec这两个平台只需要输入直播页面链接即可。
其余的平台则需要使用诸如[NiconamaCommentViewer](https://www.posite-c.com/application/ncv/)、[Chat Downloader](https://github.com/xenova/chat-downloader)等工具提前将评论下载到本地再输入其路径（可通过把文件直接拖入命令行窗口完成输入）。

**用例1:**  ```comechi.py -p o "https://www.openrec.tv/live/gkrpk1v94z5"```
**用例2:** ```comechi.py -p n "ncvLog_lv340851288-アリーナ.xml" -mr 15```
**参数说明:**
*-p o/n:* 指定直播平台为Openrec/ニコニコ生放送
*-mr 15:* 将画面内可容纳的最多弹幕行数调整为15行。弹幕数较多的时候可以使用此参数缓解弹幕过于密集的情况

除此之外还可以通过修改*style.json*里的值来改变部分弹幕样式


命令行参数
---
```
usage: new_comechi.py [-h] -p PLATFORM [-mr MAX_ROW_CNT] [-s] [-t TOP_VIEWER] source

positional arguments:
  source                评论源
                                            输入直播链接 ニコニコチャンネルプラス/Openrec
                                            输入本地评论文件路径 ASOBISTAGE/ニコニコ生放送/YouTube/Zaiko

optional arguments:
  -h, --help            show this help message and exit
  -p PLATFORM, --platform PLATFORM
                        直播平台
                                            a: ASOBISTAGE
                                            n: ニコニコ生放送
                                            nchp: ニコニコチャンネルプラス
                                            o: Openrec
                                            y: YouTube
                                            z: Zaiko
  -mr MAX_ROW_CNT, --max_row_cnt MAX_ROW_CNT
                        画面中能容纳的最多弹幕轨道数 [默认为11]
  -s, --save            保存原始评论文件（Openrec/ニコニコチャンネルプラス） [默认为否]
  -t TOP_VIEWER, --top_viewer TOP_VIEWER
                        显示发送弹幕数Top n的观众 [默认n为0 即不显示]
```
