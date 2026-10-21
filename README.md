# NovelSplitter 小说拆分工具

一个简单好用的 Windows 桌面工具，用于将长篇 **TXT / EPUB** 小说拆分成多个小文件，方便导入阅读器、手机或设备分批阅读。

## 功能特性

- 📖 **支持两种格式**
  - TXT：自动识别 UTF-8 / GBK / Big5 / UTF-16 编码
  - EPUB：自动按书脊顺序提取正文（跳过导航页），转换为纯文本
- ✂️ **按大小拆分**：自定义每个文件的最大体积（B / KB / MB），智能在换行处截断，不切断句子和汉字
- 📑 **按章节拆分**：内置正则自动识别「第X章」「序章」「楔子」「番外」「Chapter X」等标题，支持自定义正则
- 📦 **章节合并**：可设置每 N 章合并为一个文件（例如每 10 章一个文件）
- 🖥️ **图形界面**：后台线程拆分不卡界面，实时进度条与日志

## 使用方法

### 直接使用（无需安装 Python）

从 [Releases](../../releases) 下载 `NovelSplitter.exe`，双击运行：

1. 点击「浏览…」选择要拆分的 `.txt` 或 `.epub` 文件
2. 选择输出目录（默认为小说所在目录）
3. 选择拆分方式：
   - **按大小拆分**：设置每个文件的最大体积和单位
   - **按章节拆分**：可调整章节正则、设置每个文件合并的章节数
4. 点击「开始拆分」，结果保存在 `输出目录\书名\` 下

### 从源码运行

```bash
# 创建虚拟环境（推荐 uv，也可用 python -m venv）
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# 启动
.venv/Scripts/python.exe main.py
```

## 打包 exe

双击 `build.bat`，或手动执行：

```bash
.venv/Scripts/pyinstaller.exe --noconfirm --onefile --windowed --name NovelSplitter main.py
```

产物位于 `dist\NovelSplitter.exe`（约 51MB 单文件，可拷贝到任意 Windows 机器使用）。

## 运行测试

```bash
.venv/Scripts/python.exe test_splitter.py
```

测试覆盖：大小拆分不超限、内容还原一致、章节识别、章节合并、GBK 编码、EPUB 提取等 12 项用例。

## 项目结构

```
NovelSplitter/
├── main.py            # PySide6 图形界面
├── splitter.py        # 核心拆分逻辑（读取 / 拆分 / 输出）
├── test_splitter.py   # 功能自测脚本
├── build.bat          # 一键打包脚本
└── requirements.txt   # 依赖清单
```

## 技术栈

- [PySide6](https://doc.qt.io/qtforpython/) — 图形界面
- [ebooklib](https://github.com/aerkalov/ebooklib) + [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) — EPUB 解析
- [PyInstaller](https://pyinstaller.org/) — 打包为单文件 exe

## License

MIT
