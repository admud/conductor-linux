"""Terminal color utilities."""


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def c(text: str, color: str) -> str:
    """
    Colorize text with ANSI color code.

    Args:
        text: Text to colorize
        color: Color code from Colors class

    Returns:
        Colorized text string
    """
    return f"{color}{text}{Colors.ENDC}"
