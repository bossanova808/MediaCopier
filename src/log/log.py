# import logging
# from rich.logging import RichHandler
# from rich.traceback import install
# install(show_locals=True)
#
# FORMAT = "%(message)s"
# logging.basicConfig(
#     level="NOTSET",
#     format="%(message)s",
#     datefmt="[%X]",
#     handlers=[RichHandler(rich_tracebacks=True)]
# )
#
# log = logging.getLogger("rich")
# # log.info("Initialised logging")
#
# import os
# import logging
# from console.console import console
# from rich.logging import RichHandler
#
#
# def set_up_logging():
#
#     # the handler determines where the logs go: stdout/file
#     shell_handler = RichHandler(level=logging.DEBUG, log_time_format="%Y-%m-%d %H:%M:%S")
#     file_handler = logging.FileHandler("results/mediacopier.log", mode='w', encoding='utf-8')
#
#     # the formatter determines what our logs will look like
#     fmt_shell = '%(message)s'
#     fmt_file = '%(asctime)s %(levelname)-8s %(message)s'
#     #
#     shell_formatter = logging.Formatter(fmt_shell)
#     file_formatter = logging.Formatter(fmt_file, datefmt='%Y-%m-%d %H:%M:%S')
#     #
#     # # here we hook everything together
#     shell_handler.setFormatter(shell_formatter)
#     file_handler.setFormatter(file_formatter)
#
#     logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S',
#                         level=logging.DEBUG,
#                         handlers=[shell_handler, file_handler])
#
#     logging.info('Logging initialised')
