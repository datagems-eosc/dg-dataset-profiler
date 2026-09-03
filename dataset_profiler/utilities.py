import codecs
import re
import uuid
from pathlib import Path
from random import sample
from typing import Union

import pandas.api.types as ptypes

# Bytes read per iteration while sniffing a file's encoding.
_ENCODING_PROBE_CHUNK = 1 << 20  # 1 MiB

# Preferred encoding. "utf-8-sig" is plain UTF-8 except that it strips a
# leading byte-order mark, which would otherwise be decoded as three junk
# characters welded onto the first column name.
PREFERRED_ENCODING = "utf-8-sig"

# Tried in order for files that are not valid UTF-8. cp1252 comes first because
# most such files are Windows/Excel exports: it agrees with Latin-1 everywhere
# except 0x80-0x9F, where Latin-1 yields unusable C1 control characters and
# cp1252 yields the punctuation actually meant (en-dashes, curly quotes). It can
# still fail on five undefined bytes, so Latin-1 -- which maps every byte
# 0x00-0xFF and therefore never raises -- remains the last resort.
FALLBACK_ENCODINGS = ("cp1252", "ISO-8859-1")


def resolve_encoding(file_path: Union[str, Path]) -> str:
    """Return the encoding a text file should be read with.

    Returns ``PREFERRED_ENCODING`` when the file decodes cleanly as UTF-8,
    otherwise the first of ``FALLBACK_ENCODINGS`` that decodes it. The last
    fallback never raises, so this always returns something.

    The file is scanned in full rather than sampled. A prefix probe is cheaper
    but can be wrong: a file that is ASCII for its first megabytes and Latin-1
    thereafter would be reported as UTF-8, and the decode would then blow up
    mid-stream, half-way through a profiling pass. Scanning the bytes is far
    cheaper than the two pandas passes that follow, so correctness wins here.

    Decoding is incremental, so peak memory stays at one chunk regardless of
    file size.

    An unreadable file reports the fallback rather than raising; callers open
    the file immediately afterwards and surface a better error than this can.
    """
    for encoding in (PREFERRED_ENCODING, *FALLBACK_ENCODINGS):
        decoder = codecs.getincrementaldecoder(encoding)()
        try:
            with open(file_path, "rb") as handle:
                while chunk := handle.read(_ENCODING_PROBE_CHUNK):
                    decoder.decode(chunk)
                decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            continue
        except OSError:
            break
        return encoding
    return FALLBACK_ENCODINGS[-1]


def find_column_type_in_csv(column):
    # Case of explicit type
    if ptypes.is_integer_dtype(column):
        return "sc:Integer"
    elif ptypes.is_float_dtype(column):
        return "sc:Float"
    elif ptypes.is_datetime64_dtype(column):
        return "sc:Date"

    # Case of implicit type
    type_regexes = {
        "float": re.compile(r"^\d+\.\d+$"),
        "int": re.compile(r"^\d+$"),
        "date": re.compile(r"^\d\d\d\d-\d\d-\d\d$"),
    }
    type_appearances = {
        "float": 0,
        "int": 0,
        "date": 0,
    }

    # Pick three random rows
    num_rows = len(column)
    r1, r2, r3 = sample(range(0, num_rows), 3)
    picked_indices = [r1, r2, r3]

    # For each row update the appearances dictionary if value is accepted by the regex
    for index in picked_indices:
        for type, regex in type_regexes.items():
            value = column.iloc[index]
            if regex.match(str(value)) is not None:
                type_appearances[type] += 1
                continue

    if (
        type_appearances["float"] == 0
        and type_appearances["int"] == 0
        and type_appearances["date"] == 0
    ):
        return "sc:Text"
    else:
        result_type = max(type_appearances, key=type_appearances.get)  # type: ignore

        match result_type:
            case "float":
                return "sc:Float"
            case "int":
                return "sc:Integer"
            case "date":
                return "sc:Date"


def find_column_type_in_db(db_type):
    match db_type:
        case "INTEGER":
            return "sc:Integer"
        case "FLOAT", "DOUBLE PRECISION":
            return "sc:Float"
        case "DATE":
            return "sc:Date"
        case "TEXT":
            return "sc:Text"


def get_file_objects(distribution_path):
    path = Path(distribution_path)

    file_objects = [
        {"path": item.name, "id": str(uuid.uuid4())}
        for item in path.iterdir()
        if item.is_file()
    ]

    file_sets = [
        {"path": item.name, "id": str(uuid.uuid4())}
        for item in path.iterdir()
        if item.is_dir()
    ]

    return file_objects, file_sets
