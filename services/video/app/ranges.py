"""RFC 7233 single-range parsing."""
from hotstar_common.errors import AppError


class RangeNotSatisfiable(AppError):
    status_code, code = 416, "range_not_satisfiable"


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Return inclusive (start, end) for a satisfiable single range, None when no/ignorable header."""
    if not header or not header.lower().startswith("bytes="):
        return None
    spec = header[6:].split(",")[0].strip()
    if "-" not in spec:
        return None
    first, _, last = spec.partition("-")
    try:
        if first == "":  # suffix range: last N bytes
            n = int(last)
            if n <= 0:
                raise RangeNotSatisfiable("Unsatisfiable range")
            return max(size - n, 0), size - 1
        start = int(first)
        end = int(last) if last else size - 1
    except ValueError:
        return None
    if start >= size or start > end:
        raise RangeNotSatisfiable("Unsatisfiable range")
    return start, min(end, size - 1)
