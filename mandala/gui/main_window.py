"""Main module for Mandala."""

from __future__ import annotations

import inspect
import os
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, TextIO

import send2trash
from PySide6.QtCore import QDir, QPoint, QSettings, QSize, Qt, QThreadPool, QTimer, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QWidget,
)

from ..config.constants import (
    BYTES_IN_GIGABYTE,
    BYTES_IN_KILOBYTE,
    BYTES_IN_MEGABYTE,
    SECONDS_IN_MINUTE,
)
from ..core.config_validator import FileValidator
from ..core.mandala_config import MandalaConfig
from ..core.mandala_state import MandalaState
from ..gui.components import (
    DblRangeFilterWidget,
    DualListWidget,
    ExecutionWidget,
    FileCountWidget,
    FilenameSettingsWidget,
    FolderCreatorWidget,
    PathSelectorWidget,
    RangeFilterWidget,
    SidebarWidget,
    TrashSettingsWidget,
)
from ..gui.workers import RunMandalaWorker, WorkerSignals
from ..utilities.utils import convert_byte_to_size, convert_string_to_list, strtobool

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


@dataclass(slots=True)
class MandalaMainGui(QWidget):
    """Main application window for Mandala."""

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.was_enabled_map = {}

        self.threadpool = QThreadPool()
        self.worker = RunMandalaWorker(self)
        self.worker.setAutoDelete(False)

        self.state = MandalaState()

        self.log: TextIO = None
        self.log_temp: TextIO = None

        self.setup_components()
        self.setup_layout()
        self.setup_gui_signals()

        self.timer = QTimer(singleShot=False, timerType=Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_timer)

        self.settings = QSettings()
        self.restore_global_settings()
        self.restore_gui(self.settings)

        self.is_stop_pushed = False
        self.config = self.get_configuration()

        self.setWindowTitle("Mandala: Copy random files")

    def setup_gui_signals(self) -> None:
        """Set up signals for the worker thread."""
        self.signals = WorkerSignals()
        self.signals.count_signal.connect(lambda: self.ui_sect_exec.progbar_main.setValue(self.state.count))
        self.signals.time_signal.connect(self.reset_stall_timer_display)
        self.signals.log_signal.connect(lambda s: self.ui_sect_exec.textbrowser_log.append(s))
        self.signals.finished_signal.connect(lambda: self.timer.stop())

    def setup_components(self) -> None:
        """Set up the main UI components."""
        # Init setup components
        self.ui_root = PathSelectorWidget(title="Root", items=[QDir.rootPath()], parent=self)
        self.ui_dest = PathSelectorWidget(title="Destination", items=[QDir.homePath()], parent=self)
        self.ui_file_count = FileCountWidget(title="File Count", parent=self)
        self.ui_folders = FolderCreatorWidget(title="Create Folders", parent=self)
        self.ui_filenames = FilenameSettingsWidget(title="Filenames", parent=self)
        self.ui_trash = TrashSettingsWidget(title="Trash", parent=self)

        # Init filter components
        self.ui_keywords = DualListWidget(title="Keywords", parent=self)
        self.ui_extensions = DualListWidget(title="Extensions", parent=self)
        self.ui_filesize = DblRangeFilterWidget(title="Size", suffix_options=("B", "KB", "MB", "GB"), parent=self)
        self.ui_duration = DblRangeFilterWidget(title="Duration", suffix_options=("s", "m"), parent=self)
        self.ui_weight = RangeFilterWidget(title="Weight", parent=self)

        # Init sidebar and run components
        self.ui_sect_sidebar = SidebarWidget(parent=self)
        self.ui_sect_exec = ExecutionWidget(parent=self)

        # Connections
        self.ui_sect_exec.start_requested.connect(self.start_mandala_on_push)
        self.ui_sect_exec.stop_requested.connect(self.stop_mandala_on_push)

        self.ui_sect_sidebar.root_open_requested.connect(lambda: os.startfile(self.ui_root.current_path()))
        self.ui_sect_sidebar.dest_open_requested.connect(lambda: os.startfile(self.ui_dest.current_path()))
        self.ui_sect_sidebar.save_requested.connect(self.save_config)
        self.ui_sect_sidebar.load_requested.connect(self.load_config)
        self.ui_sect_sidebar.default_requested.connect(lambda: self.save_gui(self.settings))
        self.ui_sect_sidebar.reset_requested.connect(lambda: self.restore_gui(self.settings))

    def setup_layout(self) -> None:
        """Set up the main UI layouts."""
        # Layout setup components
        ui_sect_setup = QWidget()
        l_setup = QGridLayout(ui_sect_setup)
        l_setup.addWidget(self.ui_root, 0, 0, 1, 6)
        l_setup.addWidget(self.ui_dest, 1, 0, 1, 6)
        l_setup.addWidget(self.ui_file_count, 2, 0, 1, 6)
        l_setup.addWidget(self.ui_folders, 3, 0, 1, 2)
        l_setup.addWidget(self.ui_filenames, 3, 2, 1, 2)
        l_setup.addWidget(self.ui_trash, 3, 4, 1, 2)

        # Layout filter components
        ui_sect_filter = QWidget()
        l_filter = QGridLayout(ui_sect_filter)
        l_filter.addWidget(self.ui_keywords, 0, 0, 1, 3)
        l_filter.addWidget(self.ui_extensions, 1, 0, 1, 3)
        l_filter.addWidget(self.ui_filesize, 2, 0)
        l_filter.addWidget(self.ui_duration, 2, 1)
        l_filter.addWidget(self.ui_weight, 2, 2)

        # Main layout
        layout = QGridLayout(self)
        layout.addWidget(ui_sect_setup, 0, 0)
        layout.addWidget(ui_sect_filter, 1, 0)
        layout.addWidget(self.ui_sect_sidebar, 0, 1, 2, 1)
        layout.addWidget(self.ui_sect_exec, 2, 0, 1, 2)

    ###########################################
    ################# METHODS #################
    ###########################################

    ### RUN METHODS ###

    def get_configuration(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        # File Size Variables
        size_unit = self.ui_filesize.combo.currentText()
        min_size = self.ui_filesize.min_spin.value()
        max_size = self.ui_filesize.max_spin.value()
        if size_unit == "KB":
            min_size *= BYTES_IN_KILOBYTE
            max_size *= BYTES_IN_KILOBYTE
        elif size_unit == "MB":
            min_size *= BYTES_IN_MEGABYTE
            max_size *= BYTES_IN_MEGABYTE
        elif size_unit == "GB":
            min_size *= BYTES_IN_GIGABYTE
            max_size *= BYTES_IN_GIGABYTE

        # File Duration Variables
        min_duration = self.ui_duration.min_spin.value()
        max_duration = self.ui_duration.max_spin.value()
        if self.ui_duration.combo.currentText() == "m":
            min_duration *= SECONDS_IN_MINUTE
            max_duration *= SECONDS_IN_MINUTE

        root_path = Path(self.ui_root.current_path())
        return MandalaConfig(
            root=root_path,
            root_absolute=root_path.resolve(),
            dest=Path(self.ui_dest.current_path()),
            num_files=self.ui_file_count.spin_fixed.value(),
            keywords=(
                convert_string_to_list(self.ui_keywords.include_edit.text())
                if self.ui_keywords.include_groupbox.isChecked()
                else []
            ),
            not_keywords=(
                convert_string_to_list(self.ui_keywords.exclude_edit.text())
                if self.ui_keywords.exclude_groupbox.isChecked()
                else []
            ),
            extensions=(
                convert_string_to_list(self.ui_extensions.include_edit.text())
                if self.ui_extensions.include_groupbox.isChecked()
                else []
            ),
            not_extensions=(
                convert_string_to_list(self.ui_extensions.exclude_edit.text())
                if self.ui_extensions.exclude_groupbox.isChecked()
                else []
            ),
            limit_size=self.ui_filesize.isChecked(),
            min_size=round(min_size, 2),
            max_size=round(max_size, 2),
            limit_duration=self.ui_duration.isChecked(),
            min_duration=min_duration,
            max_duration=max_duration,
            weight_top=self.ui_weight.min_spin.value(),
            weight_bottom=self.ui_weight.max_spin.value(),
            create_folders=self.ui_folders.isChecked(),
            folder_name=self.ui_folders.lineedit_folder_name.text(),
            unique_folders=self.ui_folders.chk_unique_folders.isChecked(),
            num_folders=self.ui_folders.spinbox_folder_count.value() if self.ui_folders.isChecked() else 1,
            index_files=self.ui_filenames.radio_index.isChecked() if self.ui_filenames.isChecked() else False,
            rename_files=self.ui_filenames.radio_rename.isChecked() if self.ui_filenames.isChecked() else False,
            rename_name=self.ui_filenames.lineedit_rename.text() if self.ui_filenames.isChecked() else "",
            trash_empty_folders=self.ui_trash.chk_empty_folders.isChecked() if self.ui_trash.isChecked() else False,
            trash_source_files=self.ui_trash.chk_valid_files.isChecked() if self.ui_trash.isChecked() else False,
            trash_invalid_files=self.ui_trash.chk_invalid_files.isChecked() if self.ui_trash.isChecked() else False,
            log_invalid=self.ui_sect_sidebar.chk_invalid.isChecked(),
            stall_time_limit=self.ui_sect_exec.dblspin_stall.value(),
        )

    def run_mandala(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.is_stop_pushed:
                break

            self.process_folder()

        self.stop_mandala()

    def get_file_count_for_run(self) -> int:
        """Get the number of files to process for the current run."""
        if self.ui_file_count.groupbox_rand.isChecked():
            return random.randint(self.ui_file_count.spin_min_rand.value(), self.ui_file_count.spin_max_rand.value())
        return self.config.num_files

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        root_absolute = self.config.root_absolute

        self.state.reset_for_folder(root_absolute, unique_folders=self.config.unique_folders)

        top_weight_mark = Path()
        curr_dest = self.create_folders(self.config.dest)

        temp_log_file = Path(self.log.name + ".tmp")
        self.log_temp = temp_log_file.open("a", encoding="utf-8")

        main_path = self.config.root

        # File Count
        num_files = self.get_file_count_for_run()
        self.ui_sect_exec.progbar_main.setRange(0, num_files)

        for curr_file in range(num_files):
            if self.is_stop_pushed:
                break

            if self.state.touched_folders[root_absolute] and self.is_timed_out():
                break

            main_path = self.process_file(main_path, top_weight_mark, curr_file, curr_dest)

        self.end_folder_actions(curr_dest)

    def process_file(self, main_path: Path, top_mark: Path, curr_file: int, curr_dest: Path) -> Path:
        """Process a single file for copying."""
        while not self.state.touched_folders[self.config.root_absolute] and not self.is_timed_out():
            if self.is_stop_pushed:
                return main_path

            main_path_absolute = main_path.resolve()
            # Try to get main path
            try:
                if not self.state.path_cache.setdefault(main_path_absolute, []):
                    self.state.path_cache[main_path_absolute] = list(main_path.iterdir())
            except PermissionError:
                self.state.touched_folders[main_path_absolute] = True
                main_path = self.config.root
                continue

            # If folder is empty
            if len(self.state.path_cache[main_path_absolute]) == 0:
                self.state.touched_folders[main_path_absolute] = True
                if self.config.trash_empty_folders:
                    send2trash.send2trash(str(main_path_absolute))
                main_path = self.config.root
            # If the folder is not empty
            else:
                # Chooses random path and stores absolute path
                random_path = Path(random.choice(self.state.path_cache[main_path_absolute]))
                random_path_absolute = random_path.resolve()
                # If touched, try again:
                if self.state.touched_files[random_path_absolute] or self.state.touched_folders[random_path_absolute]:
                    self.touch_folder_if_all_files_touched(
                        self.state.path_cache[main_path_absolute], main_path_absolute
                    )
                    main_path = self.config.root
                elif random_path.is_dir():
                    main_path, top_mark = self.handle_random_path_is_dir(
                        random_path, random_path_absolute, main_path, top_mark
                    )
                elif random_path.is_file():
                    # Touch the file and get size
                    self.state.touched_files[random_path_absolute] = True
                    random_path_size = Path(random_path).stat().st_size
                    random_path_relative = Path(os.path.relpath(random_path, self.config.root))
                    # If file is valid
                    if self.file_validator.is_valid(random_path, random_path_size) and self.copy_files_to_target(
                        curr_file, random_path, curr_dest, random_path_size
                    ):
                        self.handle_log(random_path_relative, curr_file)
                        self.state.bytes_in_current_folder += random_path_size
                        self.state.count += 1
                        self.signals.count_signal.emit()
                        self.state.start_stall_time = perf_counter()
                        self.signals.time_signal.emit()
                        if self.config.trash_source_files:
                            send2trash.send2trash(str(random_path_absolute))

                        self.handle_weights(top_mark, main_path_absolute)
                        main_path = self.config.root
                        break

                    # If file is invalid
                    self.handle_invalid_file(random_path_relative, random_path_absolute)
                    main_path = self.config.root
        return main_path

    def handle_log(self, random_path: Path, curr_file: int) -> None:
        """Handle logging of valid files."""
        msg = f"{curr_file + 1}: {random_path}"
        if self.state.is_append_log:
            self.log_temp.write(f"{msg}\n")
        else:
            self.log.write(f"{msg}\n")
        self.signals.log_signal.emit(msg)

    def handle_invalid_file(self, random_path: Path, random_path_absolute: Path) -> None:
        """Handle invalid files by logging and trashing if necessary."""
        count = self.state.count
        if self.config.log_invalid:
            prefix = "**"
            if count >= 100:
                prefix = "***"
            elif count >= 1000:
                prefix = "****"
            self.signals.log_signal.emit(f"{prefix}: {random_path}")
        if self.config.trash_invalid_files:
            send2trash.send2trash(random_path_absolute)

    def handle_weights(self, top_mark: Path, bottom_mark: Path) -> None:
        """Handle weight assignments for folders."""
        weight_top = self.config.weight_top
        weight_bottom = self.config.weight_bottom
        weighted_counts = self.state.weighted_counts
        touched_folders = self.state.touched_folders
        touched_by_weight = self.state.touched_by_weight

        if weight_top > 0:
            weighted_counts[top_mark] += 1
            if weighted_counts[top_mark] == weight_top:
                touched_folders[top_mark] = True
                touched_by_weight[top_mark] = True

        if weight_bottom > 0:
            weighted_counts[bottom_mark] += 1
            if weighted_counts[bottom_mark] == weight_bottom:
                touched_folders[bottom_mark] = True
                touched_by_weight[bottom_mark] = True

    def handle_random_path_is_dir(
        self, random_path: Path, random_path_absolute: Path, main_path: Path, top_weight_mark: Path
    ) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        try:
            os.chdir(random_path)
            main_path = Path.cwd()
            if self.config.weight_top > 0 and Path(random_path_absolute).parent == self.config.root:
                top_weight_mark = random_path_absolute
        except PermissionError:
            self.state.touched_folders[random_path_absolute] = True
            main_path = self.config.root
        return main_path, top_weight_mark

    def end_folder_actions(self, curr_dest: Path) -> None:
        """Create and write log at the end of folder."""
        self.log_temp.close()
        self.log.close()
        self.signals.log_signal.emit(self.write_status_log(curr_dest))

        # Terminates the program if no files were collected
        if self.state.count == 0:
            create_folders = self.config.create_folders
            if create_folders:
                shutil.rmtree(curr_dest)
            elif not (create_folders or self.state.is_append_log):
                Path(self.log.name).unlink()

    def copy_files_to_target(self, file_num: int, source: Path, dest: Path, source_size: int) -> bool | None:
        """Copy files to the target destination with appropriate naming."""
        source_absolute = source.resolve()
        source_name = source.name
        try:
            if self.config.index_files:
                shutil.copy(source_absolute, dest / f"{file_num + 1}.{source_name}")
            elif self.config.rename_files:
                rename_name = self.config.rename_name
                if not (dest / f"{rename_name} {file_num + 1}{source.suffix}").exists():
                    shutil.copy(source_absolute, dest / f"{rename_name} {file_num + 1}{source.suffix}")
                else:
                    x = 1
                    while (dest / f"{rename_name} {file_num + x}{source.suffix}").exists():
                        x += 1
                    shutil.copy(source_absolute, dest / f"{rename_name} {file_num + x}{source.suffix}")
            else:
                x = 2
                while (dest / f"{source_name}").exists():
                    if source_size == (dest / f"{source_name}").stat().st_size:
                        return False
                    source_name = source.stem + f" ({x})" + source.suffix
                    x += 1
                shutil.copy(source_absolute, dest / f"{source_name}")
        except PermissionError:
            return False

        return True

    def create_folders(self, dest: Path) -> Path:
        """Create folders in the destination if specified."""
        final_dest = dest
        log_path = Path(final_dest / f"!{final_dest.name}_log.txt")

        if not self.config.create_folders:
            self.state.is_append_log = log_path.exists()
            self.log = log_path.open("a", encoding="utf-8")
        else:
            folder_name = self.config.folder_name
            try:
                Path(f"{final_dest}/{folder_name}").mkdir()
                final_dest = final_dest / f"{folder_name}"
                self.log = (final_dest / f"!{folder_name}_log.txt").open("a", encoding="utf-8")
            except FileExistsError:
                for x in range(len(list(final_dest.iterdir()))):
                    try:
                        Path(f"{final_dest}/{folder_name} {x + 2}").mkdir()
                        final_dest = final_dest / f"{folder_name} {x + 2}"
                        self.log = (final_dest / f"!{folder_name} {x + 2}_log.txt").open("a", encoding="utf-8")
                        break
                    except FileExistsError:
                        continue
        return final_dest

    def touch_folder_if_all_files_touched(self, list_of_paths: list[Path], absolute_path: Path) -> None:
        """Mark folder as touched if all files inside are touched."""
        for file_folder in list_of_paths:
            path = file_folder.resolve()
            if self.state.touched_files[path] or self.state.touched_folders[path]:
                pass
            else:
                return
        self.state.touched_folders[absolute_path] = True

    ### PROGRESS & TIMER METHODS ###

    def is_timed_out(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.config.stall_time_limit

    def stop_mandala(self) -> None:
        """Stop mandala process and reset UI elements."""
        self.signals.finished_signal.emit()

        self.log_temp.close()
        self.log.close()

        self.ui_sect_exec.btn_start.setEnabled(True)
        self.ui_sect_exec.btn_stop.setEnabled(False)
        self.ui_sect_exec.label_stall.setText(f"{self.config.stall_time_limit}0 s")

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ("stop_btn", "log_block"):
                obj.setEnabled(self.was_enabled_map[name])

    ### LOG METHODS ###

    def write_status_log(self, curr_dest: Path) -> str:
        """Write the status log at the end of each folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)
        timed_out = self.is_timed_out()
        all_searched = self.state.touched_folders[self.config.root_absolute]
        num_files = self.config.num_files

        count = self.state.count
        create_folders = self.config.create_folders

        if count == num_files:
            status = f"SUCCESS: {count}/{num_files} files copied"
        elif self.is_stop_pushed:
            status = f"STOPPED: {count}/{num_files} files copied"
        elif count == 0 and create_folders and (timed_out or all_searched):
            reason = "timed out" if timed_out else "all files searched"
            status = f"NO FILES FOUND: {reason} | folder deleted"
        elif all_searched:
            status = f"ALL FILES SEARCHED: {count}/{num_files} files copied"
        elif timed_out:
            status = f"TIMED OUT: {count}/{num_files} files copied"
        else:
            status = "FINISHED"

        _extensions = self.config.extensions
        _keywords = self.config.keywords
        ext_str = ", ".join([f".{e}" for e in _extensions]) if _extensions else "All"
        kw_str = ", ".join([f'"{k}"' for k in _keywords]) if _keywords else "All"

        report = (
            "------------------------------------------------------------------------\n"
            f"{status}\n"
            "------------------------------------------------------------------------\n"
            f"Date:             {datetime.now(tz=UTC).strftime('%B %d, %Y')}\n"
            f"Time:             {datetime.now(tz=UTC).strftime('%I:%M:%S%p')}\n"
            f"Start:            {self.config.root}\n"
            f"Destination:      {curr_dest}\n"
            f"Extensions:       {ext_str}\n"
            f"Keywords:         {kw_str}\n"
            f"Total size:       {convert_byte_to_size(self.state.bytes_in_current_folder)}\n"
            f"Total runtime:    {runtime}s\n"
            "------------------------------------------------------------------------"
        )
        self.prepend_status_to_log(report)
        return report

    def prepend_status_to_log(self, status: str) -> None:
        """Prepend the status to the log file."""
        log_path = Path(self.log.name)
        temp_log_path = Path(self.log_temp.name)

        if self.state.is_append_log:
            with temp_log_path.open(encoding="utf-8") as content, log_path.open("a", encoding="utf-8") as out:
                out.write(status + "\n")
                shutil.copyfileobj(content, out)
            temp_log_path.unlink()
        else:
            with log_path.open(encoding="utf-8") as existing, temp_log_path.open("w", encoding="utf-8") as out:
                out.write(status + "\n")
                shutil.copyfileobj(existing, out)
            log_path.unlink()
            temp_log_path.rename(self.log.name)

    #############################
    ########### SLOTS ###########
    #############################

    ### PROGRESS & TIMER SLOTS ###

    @Slot()
    def reset_stall_timer_display(self) -> None:
        """Reset the stall time progress bar and counter display."""
        self.ui_sect_exec.progbar_stall.setValue(self.ui_sect_exec.progbar_stall.maximum())
        self.ui_sect_exec.label_stall.setText(f"{self.ui_sect_exec.progbar_stall.value() / 100} s")

    @Slot()
    def update_timer(self) -> None:
        """Update the stall time progress bar and counter."""
        self.ui_sect_exec.progbar_stall.setValue(self.ui_sect_exec.progbar_stall.value() - 1)
        self.ui_sect_exec.label_stall.setText(f"{self.ui_sect_exec.progbar_stall.value() / 100} s")

    @Slot()
    def start_mandala_on_push(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            self.config = self.get_configuration()
        except ValueError:
            self.ui_sect_exec.textbrowser_log.append("Error: Invalid configuration")
            return

        self.file_validator = FileValidator(self.config)

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ("stop_btn", "log_block"):
                self.was_enabled_map[name] = obj.isEnabled()
                obj.setEnabled(False)

        self.ui_sect_exec.progbar_main.reset()
        self.ui_sect_exec.progbar_stall.setRange(0, int(self.config.stall_time_limit * 100))
        self.ui_sect_exec.progbar_stall.setValue(self.ui_sect_exec.progbar_stall.maximum())
        self.ui_sect_exec.label_stall.setText(f"{self.config.stall_time_limit}0 s")

        self.timer.start(10)
        self.ui_sect_exec.btn_start.setEnabled(False)
        self.ui_sect_exec.btn_stop.setEnabled(True)

        self.threadpool.globalInstance().start(self.worker)

    @Slot()
    def stop_mandala_on_push(self) -> None:
        """Stop the mandala process."""
        self.is_stop_pushed = True

    ### SETTINGS SLOTS AND METHODS ###

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Close event to save settings."""
        self.save_global_settings()
        super().closeEvent(event)

    def save_global_settings(self) -> None:
        """Save GUI settings to registry."""
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("show_invalid", self.ui_sect_sidebar.chk_invalid.isChecked())

    def restore_global_settings(self) -> None:
        """Restore GUI settings from registry."""
        size = self.settings.value("size", QSize(500, 500))
        if isinstance(size, QSize):
            self.resize(QSize(size))

        pos = self.settings.value("pos", QPoint(60, 60))
        if isinstance(pos, QPoint):
            self.move(pos)

        val = self.settings.value("show_invalid")
        if val is not None:
            self.ui_sect_sidebar.chk_invalid.setChecked(strtobool(val))

    @Slot()
    def save_config(self) -> None:
        """Save GUI settings to registry."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Config", "config.ini", "Config (*.ini)")
        if path:
            self.save_gui(QSettings(path, QSettings.Format.IniFormat))
            self.setWindowTitle(f"Mandala: Copy random files ({Path(path).stem})")

    @Slot()
    def load_config(self) -> None:
        """Load GUI settings from registry."""
        path, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "Config (*.ini)")
        if path:
            self.restore_gui(QSettings(path, QSettings.Format.IniFormat))
            self.setWindowTitle(f"Mandala: Copy random files ({Path(path).stem})")

    @Slot()
    def save_gui(self, settings: QSettings) -> None:
        """Save GUI settings to registry."""
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QComboBox):
                settings.setValue(name, [obj.itemText(i) for i in range(obj.count())])
                settings.setValue(f"current{name}", obj.currentText())
            elif isinstance(obj, QLineEdit):
                settings.setValue(name, obj.text())
            elif isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                settings.setValue(name, obj.value())
            elif isinstance(obj, (QCheckBox, QRadioButton)):
                settings.setValue(name, obj.isChecked())

    @Slot()
    def restore_gui(self, settings: QSettings) -> None:
        """Restore GUI settings from registry."""
        for name, obj in inspect.getmembers(self):
            if (val := settings.value(name)) is None:
                continue

            if isinstance(obj, QComboBox):
                obj.addItems(val)
                curr = settings.value(f"current{name}")
                if curr:
                    if obj.findText(curr) == -1:
                        obj.addItem(curr)
                    obj.setCurrentIndex(obj.findText(curr))
            elif isinstance(obj, QLineEdit):
                obj.setText(val)
            elif isinstance(obj, QSpinBox):
                obj.setValue(int(val))
            elif isinstance(obj, QDoubleSpinBox):
                obj.setValue(float(val))
            elif isinstance(obj, (QCheckBox, QRadioButton)):
                obj.setChecked(strtobool(val) if isinstance(val, str) else bool(val))
