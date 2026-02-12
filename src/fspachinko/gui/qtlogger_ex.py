"""Qt logging handler example from Python Documentation.

https://docs.python.org/3/howto/logging-cookbook.html#a-qt-gui-for-logging
"""

import logging
import random
import sys
import time
from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# Signals need to be contained in a QObject or subclass in order to be correctly
# initialized.
class Signaller(QObject):
    """A QObject subclass to hold the signal for logging."""

    signal = Signal(str, logging.LogRecord)


# Output to a Qt GUI is only supposed to happen on the main thread. So, this
# handler is designed to take a slot function which is set up to run in the main
# thread. In this example, the function takes a string argument which is a
# formatted log message, and the log record which generated it. The formatted
# string is just a convenience - you could format a string for output any way
# you like in the slot function itself.
#
# You specify the slot function to do whatever GUI updates you want. The handler
# doesn't know or care about specific UI elements.
class QtHandler(logging.Handler):
    """A logging handler that emits signals to a Qt slot."""

    def __init__(self, slotfunc: Callable, *args: int | str, **kwargs: object) -> None:
        """Initialize the handler and connect the signal to the provided slot function."""
        super().__init__(*args, **kwargs)
        self.signaller = Signaller()
        self.signaller.signal.connect(slotfunc)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the signal."""
        s = self.format(record)
        self.signaller.signal.emit(s, record)


# This example uses QThreads, which means that the threads at the Python level
# are named something like "Dummy-1". The function below gets the Qt name of the
# current thread.
def ctname() -> str:
    """Get the name of the current Qt thread."""
    return QThread.currentThread().objectName()


# Used to generate random levels for logging.
LEVELS = (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL)


# This worker class represents work that is done in a thread separate to the
# main thread. The way the thread is kicked off to do work is via a button press
# that connects to a slot in the worker.
#
# Because the default threadName value in the LogRecord isn't much use, we add
# a qThreadName which contains the QThread name as computed above, and pass that
# value in an "extra" dictionary which is used to update the LogRecord with the
# QThread name.
#
# This example worker just outputs messages sequentially, interspersed with
# random delays of the order of a few seconds.
class Worker(QObject):
    """Represents a worker that does work in a separate thread and logs messages."""

    @Slot()
    def start(self) -> None:
        """Start the worker and log messages with random delays."""
        extra = {"qThreadName": ctname()}
        logger.debug("Started work", extra=extra)
        i = 1
        # Let the thread run until interrupted. This allows reasonably clean
        # thread termination.
        while not QThread.currentThread().isInterruptionRequested():
            delay = 0.5 + random.random() * 2
            time.sleep(delay)
            try:
                if random.random() < 0.1:
                    msg = "Exception raised: %d" % i  # noqa: UP031
                    raise ValueError(msg)  # noqa: TRY301
                level = random.choice(LEVELS)
                logger.log(level, "Message after delay of %3.1f: %d", delay, i, extra=extra)
            except ValueError:
                logger.exception("Failed: %s", extra=extra)
            i += 1


# Implement a simple UI for this cookbook example. This contains:
# * A read-only text edit window which holds formatted log messages
# * A button to start work and log stuff in a separate thread
# * A button to log something from the main thread
# * A button to clear the log window
class Window(QWidget):
    """Window class for the Qt logging example."""

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: "black",
        logging.INFO: "blue",
        logging.WARNING: "orange",
        logging.ERROR: "red",
        logging.CRITICAL: "purple",
    }

    def __init__(self, app: QApplication) -> None:
        """Initialize the window and its widgets."""
        super().__init__()
        self.app = app
        self.textedit = te = QPlainTextEdit(self)
        # Set whatever the default monospace font is for the platform
        f = QFont("nosuchfont")
        f.setStyleHint(f.StyleHint.Monospace)
        te.setFont(f)
        te.setReadOnly(True)

        qpb = QPushButton
        self.work_button = qpb("Start background work", self)
        self.log_button = qpb("Log a message at a random level", self)
        self.clear_button = qpb("Clear log window", self)
        self.handler = h = QtHandler(self.update_status)
        # Remember to use qThreadName rather than threadName in the format string.
        fs = "%(asctime)s %(qThreadName)-12s %(levelname)-8s %(message)s"
        formatter = logging.Formatter(fs)
        h.setFormatter(formatter)
        logger.addHandler(h)
        # Set up to terminate the QThread when we exit
        app.aboutToQuit.connect(self.force_quit)

        # Lay out all the widgets
        layout = QVBoxLayout(self)
        layout.addWidget(te)
        layout.addWidget(self.work_button)
        layout.addWidget(self.log_button)
        layout.addWidget(self.clear_button)
        self.setFixedSize(900, 400)

        # Connect the non-worker slots and signals
        self.log_button.clicked.connect(self.manual_update)
        self.clear_button.clicked.connect(self.clear_display)

        # Start a new worker thread and connect the slots for the worker
        self.start_thread()
        self.work_button.clicked.connect(self.worker.start)
        # Once started, the button should be disabled
        self.work_button.clicked.connect(lambda: self.work_button.setEnabled(False))

    def start_thread(self) -> None:
        """Start the worker thread and move the worker object to it."""
        self.worker = Worker()
        self.worker_thread = QThread()
        self.worker.setObjectName("Worker")
        self.worker_thread.setObjectName("WorkerThread")  # for qThreadName
        self.worker.moveToThread(self.worker_thread)
        # This will start an event loop in the worker thread
        self.worker_thread.start()

    def kill_thread(self) -> None:
        """Request the worker thread to stop and wait for it to finish."""
        # Just tell the worker to stop, then tell it to quit and wait for that
        # to happen
        self.worker_thread.requestInterruption()
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        else:
            print("worker has already exited.")

    def force_quit(self) -> None:
        """Force the worker thread to quit when the application is closing."""
        # For use when the window is closed
        if self.worker_thread.isRunning():
            self.kill_thread()

    # The functions below update the UI and run in the main thread because
    # that's where the slots are set up
    @Slot(str, logging.LogRecord)
    def update_status(self, status: str, record: logging.LogRecord) -> None:
        """Update the log display with the given status message and log record."""
        color = self.COLORS.get(record.levelno, "black")
        s = f'<pre><font color="{color}">{status}</font></pre>'
        self.textedit.appendHtml(s)

    @Slot()
    def manual_update(self) -> None:
        """Log a message at a random level from the main thread."""
        # This function uses the formatted message passed in, but also uses
        # information from the record to format the message in an appropriate
        # color according to its severity (level).
        level = random.choice(LEVELS)
        extra = {"qThreadName": ctname()}
        logger.log(level, "Manually logged!", extra=extra)

    @Slot()
    def clear_display(self) -> None:
        """Clear the log display."""
        self.textedit.clear()


def main() -> None:
    """Run main function."""
    QThread.currentThread().setObjectName("MainThread")
    logging.getLogger().setLevel(logging.DEBUG)
    app = QApplication(sys.argv)
    example = Window(app)
    example.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
