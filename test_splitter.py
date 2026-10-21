"""功能自测：生成样例 txt/epub，验证按大小与按章节拆分。"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from splitter import split_novel, read_txt

TMP = Path(__file__).parent / "_test_tmp"
shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir()

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)


# ---------- 1. 生成样例 txt（含章节标题，中文内容）----------
chapters_text = []
for i in range(1, 21):
    body = ("这是一段测试正文，用来模拟小说内容。" * 200 + "\n") * 5
    chapters_text.append(f"第{i}章 测试章节标题{i}\n\n{body}")
sample_txt = TMP / "样例小说.txt"
sample_txt.write_text("书名：样例小说\n作者：测试\n\n" + "\n".join(chapters_text), encoding="utf-8")
size = sample_txt.stat().st_size
print(f"样例 txt 大小: {size} bytes ({size/1024:.1f} KB)")

# ---------- 2. 按大小拆分 ----------
files = split_novel(str(sample_txt), str(TMP / "out_size"), mode="size", size_value=50, size_unit="KB")
limit = 50 * 1024
check("按大小拆分: 生成多个文件", len(files) > 1, f"({len(files)} 个)")
check("按大小拆分: 每个文件 <= 50KB", all(Path(f).stat().st_size <= limit for f in files),
      f"(max={max(Path(f).stat().st_size for f in files)})")
reassembled = "".join(Path(f).read_text(encoding="utf-8") for f in files)
original = read_txt(str(sample_txt))
check("按大小拆分: 拼接还原内容一致", reassembled.replace("\r\n", "\n") == original.replace("\r\n", "\n"))

# ---------- 3. 按章节拆分 ----------
files = split_novel(str(sample_txt), str(TMP / "out_chapter"), mode="chapter")
check("按章节拆分: 20章+卷首 = 21个文件", len(files) == 21, f"(实际 {len(files)} 个)")
check("按章节拆分: 文件名含章节标题", any("第10章" in Path(f).name for f in files))

# ---------- 3b. 按章节拆分: 每5章合并为一个文件 ----------
files = split_novel(str(sample_txt), str(TMP / "out_chapter5"), mode="chapter", chapters_per_file=5)
# 21 个章节（含卷首）每 5 个一组 = 5 组（5+5+5+5+1）
check("每5章合并: 5个文件", len(files) == 5, f"(实际 {len(files)} 个)")
merged = Path(files[0]).read_text(encoding="utf-8")
check("每5章合并: 首文件含卷首+第1~4章",
      "卷首" not in merged and "第1章" in merged and "第4章" in merged and "第5章" not in merged)
check("每5章合并: 文件名带章节范围", any("-" in Path(f).stem.split("_", 1)[1] for f in files))

# ---------- 4. GBK 编码 txt ----------
gbk_txt = TMP / "gbk小说.txt"
gbk_txt.write_bytes(("第一章 开始\n\n" + "中文内容测试。" * 500 + "\n\n第二章 继续\n\n" + "更多内容。" * 500).encode("gbk"))
files = split_novel(str(gbk_txt), str(TMP / "out_gbk"), mode="chapter")
content = Path(files[0]).read_text(encoding="utf-8")
check("GBK 编码: 正确读取", "中文内容测试" in content)

# ---------- 5. 样例 EPUB ----------
from ebooklib import epub

book = epub.EpubBook()
book.set_identifier("test123")
book.set_title("EPUB样例")
book.set_language("zh")
book.add_author("测试")
epub_chapters = []
for i in range(1, 6):
    c = epub.EpubHtml(title=f"第{i}章", file_name=f"chap_{i}.xhtml", lang="zh")
    c.content = f"<html><body><h1>第{i}章 EPUB章节</h1><p>{'EPUB正文内容测试。' * 300}</p></body></html>"
    book.add_item(c)
    epub_chapters.append(c)
book.toc = epub_chapters
book.spine = ["nav"] + epub_chapters
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())
epub_path = TMP / "样例.epub"
epub.write_epub(str(epub_path), book)

files = split_novel(str(epub_path), str(TMP / "out_epub_chapter"), mode="chapter")
check("EPUB 按章节拆分: 5章", len(files) == 5, f"(实际 {len(files)} 个)")
content = Path(files[0]).read_text(encoding="utf-8")
check("EPUB 内容提取正确", "EPUB正文内容测试" in content)

files = split_novel(str(epub_path), str(TMP / "out_epub_size"), mode="size", size_value=10, size_unit="KB")
check("EPUB 按大小拆分", len(files) >= 1 and all(Path(f).stat().st_size <= 10 * 1024 for f in files),
      f"({len(files)} 个)")

print()
if failures:
    print(f"失败 {len(failures)} 项: {failures}")
    sys.exit(1)
print("全部测试通过！")
