import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fit_ctf.components.logger.logger_interface import LoggerInterface

if TYPE_CHECKING:
    import fit_ctf.ctf_base as ctf_base


class DefaultLogger(LoggerInterface):
    class LoggerNameMissing(BaseException):
        pass

    logger_format = "[%(asctime)s] - %(levelname)s: %(message)s"

    def __init__(self, ctf_base: "ctf_base.CTFBase", **kwargs):
        super().__init__(ctf_base, **kwargs)
        self.get_or_create_logger(__name__, False)
        self.get_or_create_logger(f"{__name__}_print", False, "")

    def _logger_check(self, **kwargs) -> logging.Logger:
        logger_name = kwargs.pop("logger_name", __name__)
        return self.get_or_create_logger(logger_name=logger_name, **kwargs)

    def info(self, msg: str, **kwargs):
        self._logger_check(**kwargs).info(msg)

    def error(self, msg: str, **kwargs):
        self._logger_check(**kwargs).error(msg)

    def warning(self, msg: str, **kwargs):
        self._logger_check(**kwargs).warning(msg)

    def critical(self, msg: str, **kwargs):
        self._logger_check(**kwargs).critical(msg)

    def debug(self, msg: str, **kwargs):
        self._logger_check(**kwargs).debug(msg)

    def print(self, msg: str, **kwargs):
        self.get_or_create_logger(f"{__name__}_print").info(msg)

    def get_or_create_logger(
        self,
        logger_name: str,
        is_file: bool = True,
        format: str | None = None,
        level=logging.INFO,
    ) -> logging.Logger:
        """Get an existing or create a new logger.

        :param logger_name: Identification name of the logger.
        :type logger_name: str
        :param is_file: This flag is only meant to be used if the logger does not exist.
            If set to `True` the new logger will write to a file; otherwise to STDOUT,
            defaults to True.
        :type is_file: bool, optional
        :return: Found or a new logger.
        :rtype: logging.Logger
        """

        def setup_logger(
            name: str,
            handler: logging.Handler,
            level=logging.INFO,
            format: str | None = None,
        ) -> logging.Logger:
            if format is None:
                handler.setFormatter(logging.Formatter(self.logger_format))
            else:
                handler.setFormatter(logging.Formatter(format))

            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.addHandler(handler)

            return logger

        # logger not defined
        if logger_name not in logging.Logger.manager.loggerDict.keys():
            # create handler based on the `is_file` condition
            handler = (
                logging.FileHandler(
                    Path(os.getenv("LOG_DEST", "./")) / f"{logger_name}.log"
                )
                if is_file
                else logging.StreamHandler(sys.stdout)
            )
            return setup_logger(logger_name, handler, level, format)
        return logging.getLogger(logger_name)
