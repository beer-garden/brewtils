from brewtils import command, parameter


class Commands(object):
    @parameter(
        key="line_start",
        type="Integer",
        description="Line to begin reading log file",
        multi=False,
        display_name="Start Line",
        optional=False,
        default=0,
        choices=None,
        model=None,
        nullable=False,
    )
    @parameter(
        key="line_end",
        type="Integer",
        description="Line to stop reading log file",
        multi=False,
        display_name="End Line",
        optional=False,
        default=50,
        choices=None,
        model=None,
        nullable=False,
    )
    @command(
        description="Auto-Generated helper command to aid in viewing remote logs. "
        "If logs are written to a file."
    )
    def _read_log(self, line_start=0, line_end=50):

        import itertools
        import logging

        def _find_logger_basefilename(logger):
            """Finds the logger base filename(s) currently there is only one
            """
            log_file = None
            parent = logger.parent
            if parent.__class__.__name__ == "RootLogger":
                # this is where the file name lives
                for h in parent.handlers:
                    if hasattr(h, "baseFilename"):
                        log_file = h.baseFilename
                        break
            else:
                log_file = _find_logger_basefilename(parent)

            return log_file

        log_file = _find_logger_basefilename(logging.getLogger(__name__))
        if log_file:
            raw_logs = []
            try:
                with open(log_file, "r") as text_file:
                    for line in itertools.islice(text_file, line_start, line_end):
                        raw_logs.append(line)
                return raw_logs
            except IOError as e:
                return [
                    "Unable to read Log file",
                    "I/O error({0}): {1}".format(e.errno, e.strerror),
                ]

        return [
            "Unable to determine Logger Handler base Filename. "
            "Please check with the System Adminstrator to verify plugin is writing "
            "to log file."
        ]
