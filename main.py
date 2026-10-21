"""NovelSplitter — 小说拆分工具（txt / epub → txt）。"""

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from splitter import DEFAULT_CHAPTER_PATTERN, split_novel


class SplitWorker(QThread):
    """后台拆分线程，避免界面卡死。"""

    progress = Signal(int, int, str)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, kwargs, parent=None):
        super().__init__(parent)
        self._kwargs = kwargs

    def run(self):
        try:
            files = split_novel(progress=self._on_progress, **self._kwargs)
            self.finished_ok.emit(files)
        except Exception:
            self.failed.emit(traceback.format_exc())

    def _on_progress(self, cur, total, msg):
        self.progress.emit(cur, total, msg)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小说拆分工具 NovelSplitter")
        self.resize(640, 520)
        self._worker = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ---- 文件选择 ----
        file_group = QGroupBox("文件")
        file_form = QFormLayout(file_group)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("选择要拆分的 .txt 或 .epub 小说文件")
        btn_input = QPushButton("浏览…")
        btn_input.clicked.connect(self._pick_input)
        row = QHBoxLayout()
        row.addWidget(self.input_edit, 1)
        row.addWidget(btn_input)
        file_form.addRow("小说文件：", row)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("拆分结果的输出目录")
        btn_output = QPushButton("浏览…")
        btn_output.clicked.connect(self._pick_output)
        row = QHBoxLayout()
        row.addWidget(self.output_edit, 1)
        row.addWidget(btn_output)
        file_form.addRow("输出目录：", row)

        root.addWidget(file_group)

        # ---- 拆分设置 ----
        mode_group = QGroupBox("拆分方式")
        mode_layout = QVBoxLayout(mode_group)

        self.radio_size = QRadioButton("按大小拆分")
        self.radio_size.setChecked(True)
        self.radio_chapter = QRadioButton("按章节拆分")
        mode_layout.addWidget(self.radio_size)

        size_row = QHBoxLayout()
        size_row.addSpacing(24)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(1, 10 * 1024 * 1024)
        self.size_spin.setValue(100)
        self.size_spin.setDecimals(0)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["KB", "MB", "B"])
        size_row.addWidget(QLabel("每个文件不超过："))
        size_row.addWidget(self.size_spin)
        size_row.addWidget(self.unit_combo)
        size_row.addStretch(1)
        mode_layout.addLayout(size_row)

        mode_layout.addWidget(self.radio_chapter)
        chapter_row = QHBoxLayout()
        chapter_row.addSpacing(24)
        self.pattern_edit = QLineEdit(DEFAULT_CHAPTER_PATTERN)
        chapter_row.addWidget(QLabel("章节正则："))
        chapter_row.addWidget(self.pattern_edit, 1)
        mode_layout.addLayout(chapter_row)

        per_file_row = QHBoxLayout()
        per_file_row.addSpacing(24)
        self.chapters_per_file_spin = QSpinBox()
        self.chapters_per_file_spin.setRange(1, 100000)
        self.chapters_per_file_spin.setValue(1)
        per_file_row.addWidget(QLabel("每个文件合并："))
        per_file_row.addWidget(self.chapters_per_file_spin)
        per_file_row.addWidget(QLabel("章（1 = 每章一个文件）"))
        per_file_row.addStretch(1)
        mode_layout.addLayout(per_file_row)

        root.addWidget(mode_group)

        self.radio_size.toggled.connect(self._update_mode_ui)
        self._update_mode_ui()

        # ---- 进度与日志 ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        # ---- 操作按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_start = QPushButton("开始拆分")
        self.btn_start.setMinimumWidth(120)
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)
        root.addLayout(btn_row)

    def _update_mode_ui(self):
        by_size = self.radio_size.isChecked()
        self.size_spin.setEnabled(by_size)
        self.unit_combo.setEnabled(by_size)
        self.pattern_edit.setEnabled(not by_size)
        self.chapters_per_file_spin.setEnabled(not by_size)

    def _pick_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择小说文件", "", "小说文件 (*.txt *.epub);;所有文件 (*)"
        )
        if path:
            self.input_edit.setText(path)
            if not self.output_edit.text():
                self.output_edit.setText(str(Path(path).parent))

    def _pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_edit.setText(path)

    def _log(self, msg):
        self.log.appendPlainText(msg)

    def _start(self):
        input_path = self.input_edit.text().strip()
        output_dir = self.output_edit.text().strip()
        if not input_path or not Path(input_path).is_file():
            QMessageBox.warning(self, "提示", "请选择有效的小说文件（.txt / .epub）")
            return
        if not output_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            return

        kwargs = dict(
            input_path=input_path,
            output_dir=output_dir,
            mode="size" if self.radio_size.isChecked() else "chapter",
            size_value=self.size_spin.value(),
            size_unit=self.unit_combo.currentText(),
            chapter_pattern=self.pattern_edit.text(),
            chapters_per_file=self.chapters_per_file_spin.value(),
        )

        self.btn_start.setEnabled(False)
        self.log.clear()
        self.progress_bar.setValue(0)
        self._log(f"开始拆分：{input_path}")

        self._worker = SplitWorker(kwargs, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, cur, total, msg):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(cur)
        self._log(msg)

    def _on_done(self, files):
        self.btn_start.setEnabled(True)
        self._log(f"\n完成！共生成 {len(files)} 个文件。")
        QMessageBox.information(self, "完成", f"拆分完成，共生成 {len(files)} 个文件。")

    def _on_failed(self, err):
        self.btn_start.setEnabled(True)
        self._log(err)
        last_line = err.strip().splitlines()[-1] if err.strip() else "未知错误"
        QMessageBox.critical(self, "拆分失败", last_line)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
