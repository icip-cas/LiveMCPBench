import colorlog
import logging
import pathlib
import os


def _set_logger(
    exp_dir: pathlib.Path,
    logging_level=logging.INFO,
    logging_level_stdout=logging.INFO,
    Filter=None,
    file_name="experiment.log",
):
    os.makedirs(exp_dir, exist_ok=True)
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-4s%(reset)s %(asctime)s [%(name)s] %(blue)s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    file_formatter = logging.Formatter(
        "%(levelname)-8s %(asctime)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # output logging traces to a log file
    logging.basicConfig(encoding="utf-8")
    file_handler = logging.FileHandler(exp_dir / file_name, encoding="utf-8", mode="w")
    file_handler.setLevel(logging_level)  # same level as console outputs
    file_handler.setFormatter(file_formatter)
    if Filter is not None:
        file_handler.addFilter(Filter())
    # output handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging_level_stdout)
    stream_handler.setFormatter(formatter)
    if Filter is not None:
        stream_handler.addFilter(Filter())
    # setup root logger
    root_logger = logging.getLogger()

    # remove previous stream handlers
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
    root_logger.setLevel(logging_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    if Filter is not None:
        root_logger.addFilter(Filter())
    # setup openai logger (don't go below INFO verbosity)
    openai_logger = logging.getLogger("openai._base_client")
    openai_logger.setLevel(max(logging.INFO, logging_level_stdout))
