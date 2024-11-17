class Foreground:
    """
    ANSI color codes for text foreground.
    """

    BLACK: str = "\x1b[30m"
    RED: str = "\x1b[31m"
    GREEN: str = "\x1b[32m"
    YELLOW: str = "\x1b[33m"
    BLUE: str = "\x1b[34m"  # This looks like purple
    MAGENTA: str = "\x1b[35m"  # This looks like pink
    CYAN: str = "\x1b[36m"  # This looks like aqua green
    WHITE: str = "\x1b[37m"
    DEFAULT: str = "\x1b[39m"

    BRIGHT_BLACK: str = "\x1b[90m"
    BRIGHT_RED: str = "\x1b[91m"
    BRIGHT_GREEN: str = "\x1b[92m"
    BRIGHT_YELLOW: str = "\x1b[93m"
    BRIGHT_BLUE: str = "\x1b[94m"
    BRIGHT_MAGENTA: str = "\x1b[95m"
    BRIGHT_CYAN: str = "\x1b[96m"
    BRIGHT_WHITE: str = "\x1b[97m"

    @classmethod
    def rgb(cls, r: int, g: int, b: int) -> str:
        return f"\x1b[38;2;{r};{g};{b}m"

    @classmethod
    def black(cls, text: str) -> str:
        return f"{cls.BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def red(cls, text: str) -> str:
        return f"{cls.RED}{text}{cls.DEFAULT}"

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def yellow(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def blue(cls, text: str) -> str:
        return f"{cls.BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def magenta(cls, text: str) -> str:
        return f"{cls.MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def cyan(cls, text: str) -> str:
        return f"{cls.CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def white(cls, text: str) -> str:
        return f"{cls.WHITE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_black(cls, text: str) -> str:
        return f"{cls.BRIGHT_BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def bright_red(cls, text: str) -> str:
        return f"{cls.BRIGHT_RED}{text}{cls.DEFAULT}"

    @classmethod
    def bright_green(cls, text: str) -> str:
        return f"{cls.BRIGHT_GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_yellow(cls, text: str) -> str:
        return f"{cls.BRIGHT_YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def bright_blue(cls, text: str) -> str:
        return f"{cls.BRIGHT_BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_magenta(cls, text: str) -> str:
        return f"{cls.BRIGHT_MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def bright_cyan(cls, text: str) -> str:
        return f"{cls.BRIGHT_CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_white(cls, text: str) -> str:
        return f"{cls.BRIGHT_WHITE}{text}{cls.DEFAULT}"


class Background:
    """
    ANSI color codes for text background.
    """

    BLACK: str = "\x1b[40m"
    RED: str = "\x1b[41m"
    GREEN: str = "\x1b[42m"
    YELLOW: str = "\x1b[43m"
    BLUE: str = "\x1b[44m"
    MAGENTA: str = "\x1b[45m"
    CYAN: str = "\x1b[46m"
    WHITE: str = "\x1b[47m"
    DEFAULT: str = "\x1b[49m"

    BRIGHT_BLACK: str = "\x1b[100m"
    BRIGHT_RED: str = "\x1b[101m"
    BRIGHT_GREEN: str = "\x1b[102m"
    BRIGHT_YELLOW: str = "\x1b[103m"
    BRIGHT_BLUE: str = "\x1b[104m"
    BRIGHT_MAGENTA: str = "\x1b[105m"
    BRIGHT_CYAN: str = "\x1b[106m"
    BRIGHT_WHITE: str = "\x1b[107m"

    @classmethod
    def rgb(cls, r: int, g: int, b: int) -> str:
        return f"\x1b[48;2;{r};{g};{b}m"

    @classmethod
    def black(cls, text: str) -> str:
        return f"{cls.BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def red(cls, text: str) -> str:
        return f"{cls.RED}{text}{cls.DEFAULT}"

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def yellow(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def blue(cls, text: str) -> str:
        return f"{cls.BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def magenta(cls, text: str) -> str:
        return f"{cls.MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def cyan(cls, text: str) -> str:
        return f"{cls.CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def white(cls, text: str) -> str:
        return f"{cls.WHITE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_black(cls, text: str) -> str:
        return f"{cls.BRIGHT_BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def bright_red(cls, text: str) -> str:
        return f"{cls.BRIGHT_RED}{text}{cls.DEFAULT}"

    @classmethod
    def bright_green(cls, text: str) -> str:
        return f"{cls.BRIGHT_GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_yellow(cls, text: str) -> str:
        return f"{cls.BRIGHT_YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def bright_blue(cls, text: str) -> str:
        return f"{cls.BRIGHT_BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_magenta(cls, text: str) -> str:
        return f"{cls.BRIGHT_MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def bright_cyan(cls, text: str) -> str:
        return f"{cls.BRIGHT_CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_white(cls, text: str) -> str:
        return f"{cls.BRIGHT_WHITE}{text}{cls.DEFAULT}"


class Style:
    """
    ANSI style codes for text.
    """

    BOLD: str = "\x1b[1m"
    DIM: str = "\x1b[2m"
    ITALIC: str = "\x1b[3m"
    UNDERLINE: str = "\x1b[4m"
    INVERTED: str = "\x1b[7m"
    HIDDEN: str = "\x1b[8m"

    NORMAL: str = "\x1b[22m"
    STRAIGHT: str = "\x1b[23m"
    NOT_UNDERLINED: str = "\x1b[24m"
    INVERTED_OFF: str = "\x1b[27m"
    REVEAL: str = "\x1b[28m"

    RESET_ALL: str = "\x1b[0m"

    @classmethod
    def bold(cls, text: str) -> str:
        return f"{cls.BOLD}{text}{cls.NORMAL}"

    @classmethod
    def dim(cls, text: str) -> str:
        return f"{cls.DIM}{text}{cls.NORMAL}"

    @classmethod
    def italic(cls, text: str) -> str:
        return f"{cls.ITALIC}{text}{cls.STRAIGHT}"

    @classmethod
    def underline(cls, text: str) -> str:
        return f"{cls.UNDERLINE}{text}{cls.NOT_UNDERLINED}"

    @classmethod
    def inverted(cls, text: str) -> str:
        return f"{cls.INVERTED}{text}{cls.INVERTED_OFF}"

    @classmethod
    def hidden(cls, text: str) -> str:
        return f"{cls.HIDDEN}{text}{cls.REVEAL}"

    @classmethod
    def reset_all(cls, text: str) -> str:
        return f"{text}{cls.RESET_ALL}"
