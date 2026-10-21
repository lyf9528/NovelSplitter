"""小说拆分核心逻辑：读取 txt/epub，按大小或按章节拆分。"""

import re
from pathlib import Path

DEFAULT_CHAPTER_PATTERN = (
    r"^\s*(第[0-9零一二三四五六七八九十百千两]+[章节卷回部集篇][^\n]{0,50}"
    r"|序[章言曲]?|楔子|引子|序言|前言|尾声|后记|终章"
    r"|番外[^\n]{0,30}"
    r"|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+[^\n]{0,50})\s*$"
)


def read_txt(path: str) -> str:
    """读取 txt，自动尝试常见编码（utf-8 / gb18030 / big5 / utf-16）。"""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def extract_epub_text(path: str) -> str:
    """从 epub 中提取纯文本（按书脊顺序拼接各章节）。"""
    from bs4 import BeautifulSoup
    from ebooklib import epub

    book = epub.read_epub(path)
    parts = []
    for spine_id, _linear in book.spine:
        item = book.get_item_with_id(spine_id)
        if item is None or isinstance(item, epub.EpubNav):
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text("\n")
        if text.strip():
            parts.append(text.strip())
    if not parts:
        raise ValueError("未能从 EPUB 中提取到正文内容")
    return "\n\n".join(parts)


def load_novel(path: str) -> str:
    """根据扩展名加载小说全文。"""
    ext = Path(path).suffix.lower()
    if ext == ".txt":
        return read_txt(path)
    if ext == ".epub":
        return extract_epub_text(path)
    raise ValueError(f"不支持的文件格式: {ext}")


def split_by_size(text: str, max_bytes: int) -> list[str]:
    """按字节数拆分（以 UTF-8 编码计算），优先在换行处截断。

    每个分片编码为 UTF-8 后不超过 max_bytes。
    """
    if max_bytes <= 0:
        raise ValueError("拆分大小必须大于 0")

    chunks = []
    buf = []
    buf_bytes = 0

    for line in text.splitlines(keepends=True):
        line_bytes = len(line.encode("utf-8"))
        if buf_bytes + line_bytes > max_bytes:
            if buf:
                chunks.append("".join(buf))
                buf, buf_bytes = [], 0
            # 单行就超过限制：按字节硬切（保证不截断字符）
            while line_bytes > max_bytes:
                piece, line = _cut_to_bytes(line, max_bytes)
                chunks.append(piece)
                line_bytes = len(line.encode("utf-8"))
        buf.append(line)
        buf_bytes += line_bytes

    if buf:
        chunks.append("".join(buf))
    return chunks


def _cut_to_bytes(s: str, max_bytes: int) -> tuple[str, str]:
    """把字符串切成 (不超过 max_bytes 的前缀, 剩余部分)，不截断字符。"""
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s, ""
    cut = encoded[:max_bytes]
    # 回退到完整字符边界（UTF-8 续字节形如 10xxxxxx）
    while cut and (cut[-1] & 0b1100_0000) == 0b1000_0000:
        cut = cut[:-1]
    # 去掉可能被截断的多字节字符头部
    head = cut.decode("utf-8", errors="ignore")
    return head, s[len(head):]


def split_by_chapter(text: str, pattern: str = DEFAULT_CHAPTER_PATTERN) -> list[tuple[str, str]]:
    """按章节标题正则拆分，返回 [(标题, 内容)]。首个标题前的正文记为“卷首”。"""
    regex = re.compile(pattern, re.MULTILINE)
    matches = list(regex.finditer(text))
    if not matches:
        raise ValueError("未匹配到任何章节标题，可尝试调整章节正则")

    chapters = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        chapters.append(("卷首", text[: matches[0].start()].strip()))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters.append((title, text[m.start():end].strip()))
    return chapters


def sanitize_filename(name: str, max_len: int = 60) -> str:
    """清理文件名中的 Windows 非法字符。"""
    name = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name).strip().strip(".")
    return (name[:max_len] or "untitled")


def split_novel(
    input_path: str,
    output_dir: str,
    mode: str = "size",
    size_value: float = 100,
    size_unit: str = "KB",
    chapter_pattern: str = DEFAULT_CHAPTER_PATTERN,
    chapters_per_file: int = 1,
    progress=None,
) -> list[str]:
    """执行拆分，返回生成的文件路径列表。

    mode: "size" 按大小拆分 | "chapter" 按章节拆分
    chapters_per_file: 按章节拆分时，每个输出文件合并多少章（1 = 每章一个文件）
    progress: 可选回调 progress(current, total, message)
    """
    if progress:
        progress(0, 1, "正在读取文件...")
    text = load_novel(input_path)

    base = sanitize_filename(Path(input_path).stem)
    out_dir = Path(output_dir) / base
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    if mode == "size":
        unit_factor = {"B": 1, "KB": 1024, "MB": 1024 * 1024}[size_unit]
        max_bytes = int(size_value * unit_factor)
        chunks = split_by_size(text, max_bytes)
        total = len(chunks)
        digits = max(4, len(str(total)))
        for i, chunk in enumerate(chunks, 1):
            out_path = out_dir / f"{base}_{i:0{digits}d}.txt"
            out_path.write_text(chunk, encoding="utf-8", newline="")
            written.append(str(out_path))
            if progress:
                progress(i, total, f"写入 {out_path.name}")
    else:
        chapters = split_by_chapter(text, chapter_pattern)
        per_file = max(1, int(chapters_per_file))
        groups = [chapters[i:i + per_file] for i in range(0, len(chapters), per_file)]
        total = len(groups)
        digits = max(3, len(str(total)))
        for i, group in enumerate(groups, 1):
            first, last = group[0], group[-1]
            content = "\n\n".join(c for _t, c in group)
            name = f"{i:0{digits}d}_{sanitize_filename(first[0])}"
            if len(group) > 1:
                name += f"-{sanitize_filename(last[0])}"
            out_path = out_dir / f"{name}.txt"
            out_path.write_text(content, encoding="utf-8", newline="")
            written.append(str(out_path))
            if progress:
                progress(i, total, f"写入 {out_path.name}")

    return written
