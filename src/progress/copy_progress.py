from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TaskID, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, \
    TimeElapsedColumn, TransferSpeedColumn
from rich.layout import Layout


class CopyProgress:
    """
    Class to encapsulate the progress displays we use once we finally get to the copying stage.
    """

    group: Group
    layout: Layout

    overall: Progress
    overall_task: TaskID
    current_library_task: TaskID

    current_file: Progress
    current_file_task: TaskID
    current_file_name: str = ""

    progress_panel: Panel
    current_file_panel: Panel

    panel_width: int = 120

    def __init__(self):

        self.overall = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(pulse_style='', bar_width=80),
            TaskProgressColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
        )

        self.current_library = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(pulse_style='', bar_width=80),
            TaskProgressColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
        )

        self.current_file = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(pulse_style='', bar_width=80),
            TransferSpeedColumn(),
            "•",
            TaskProgressColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
        )

        progress_group = Group(
            self.overall,
            self.current_library
        )
        self.progress_panel = Panel(progress_group, title="Progress", width=self.panel_width)

        self.current_filename = Text("File: ")
        panel_group = Group(
            self.current_filename,
            self.current_file
        )
        self.current_file_panel = Panel(panel_group, title="Current File", width=self.panel_width)

        self.layout = Layout()
        self.layout.split_column(
            Layout(self.progress_panel, name="upper", size=4),
            Layout(self.current_file_panel, name="lower", size=4)
        )

    def prep_overall_progress(self, size_overall: int):
        self.overall_task = self.overall.add_task("Overall".ljust(10), total=size_overall)

    def prep_library_progress(self, library_type: str, size_library: int):
        self.current_library_task = self.overall.add_task(library_type.ljust(10), total=size_library)

    def prep_current_file_progress(self, name_current_file, size_current_file: int):
        self.current_file_task = self.current_file.add_task("Copying".ljust(10), total=size_current_file)
        group = Group(
            # Limit the filename length here so it doesn't get chopped off...
            f"{name_current_file[:100]} ({size_current_file/1024/1024/1024:.2f} GB)",
            self.current_file
        )
        panel = Panel(group, title="Current File", width=self.panel_width)
        self.layout["lower"].update(panel)

    def update_overall_and_library_progress(self, advance: int):
        self.overall.update(self.overall_task, advance=advance)
        self.overall.update(self.current_library_task, advance=advance)

    # Callback, so needs to have this signature
    # noinspection PyUnusedLocal
    def update_current_file_progress(self, bytes_since_last_update, total_bytes_copied, size):
        self.current_file.update(self.current_file_task, advance=bytes_since_last_update)
        self.overall.update(self.overall_task, advance=bytes_since_last_update)
        self.overall.update(self.current_library_task, advance=bytes_since_last_update)

    def complete_current_library(self):
        self.overall.remove_task(self.current_library_task)

    def complete_current_file(self):
        self.current_file.remove_task(self.current_file_task)
