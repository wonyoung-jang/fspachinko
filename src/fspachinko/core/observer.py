"""Abstract interface for Observer pattern."""

from abc import ABC, abstractmethod


class Observer(ABC):
    """Interface for Observer."""

    @abstractmethod
    def on_start_process(self, ndir_to_create: int) -> None:
        """Call when starting a run of the engine.

        Emit total number of directories to create or 1 if no directories are to be created.
        """

    @abstractmethod
    def on_directory_start(self, idx: int, nfiles_to_process: int) -> None:
        """Call when starting to process a directory.

        Emit current directory index and number of files to transferred into the directory.
        """

    @abstractmethod
    def on_file_transferred(self, count: int) -> None:
        """Call when a file is transferred.

        Emit current count of transferred files in the current directory.
        """

    @abstractmethod
    def on_finished(self) -> None:
        """Call when processing is finished."""
