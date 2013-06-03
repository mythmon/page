from datetime import datetime, timedelta

from parsley import makeGrammar, ParseError


grammar = (
    r"""
    message = byte{4} compression o_str:msg_id (object+):objects
              -> (msg_id, objects)

    compression = ~"\x01" byte
    type = "chr" | "int" | "lon" | "str" | "tim" | "buf" | "ptr" | "htb"
         | "hda" | "inf" | "inl" | "arr"
    typed_object :t = !(self.apply('o_' + ''.join(t))[0])
    object = <type>:t typed_object(t)

    o_chr = byte
    o_int = int4
    o_lon = int1:l <byte{l}>:bs -> int(bs)

    o_str = len_str
    o_buf = len_str
    len_str = "\xFF\xFF\xFF\xFF" -> None
            | int4:l <byte{l}>:bs -> bs

    o_ptr = "\x01" null -> None
          | int1:l <byte{l}>:bs -> int(bs, 16)
    o_tim = int1:l byte{l}:bs -> ascii_to_datetime(''.join(bs))

    o_htb = type:t1 type:t2 int4:l (hash_item(t1, t2){l}):items -> dict(items)
    hash_item :t1 :t2 = typed_object(t1):k typed_object(t2):v -> (k, v)

    o_hda = hpath:path hkeys:keys int4:count
            !(parse_hdata(self, path, keys, count))
    hpath = o_str:path -> path.split('/')
    hkeys = int4:l
            hkey:first ("," hkey)*:rest
            -> [first] + rest
    hkey = <(~":" anything)+>:key ":" <type>:t-> (key, t)

    o_inf = o_str:k o_str:v -> k, v

    o_inl = o_str:k int1:l infolist_item{l}:items -> (k, list(items))
    infolist_item = int1:l infolist_vars{l}:vs -> dict(vs)
    infolist_vars = o_str:k type:t typed_object(t):v -> (k, v)

    o_arr = type:t int4:l typed_object(t){l}:os -> list(os)

    int1 = byte:b -> ord(b)
    int4 = byte{4}:bs -> bytes_to_int(bs)
    bool = byte:b -> bool(ord(b))
    byte = anything
    null = anything:x ?(x == "\x00")
    """)


def bytes_to_int(bs):
    """Parses a byte string into a little endian, unsigned integer."""
    acc = 0
    for b in bs:
        acc <<= 8
        acc |= ord(b)
    return acc


def ascii_to_datetime(seconds_str):
    seconds = int(seconds_str)
    return datetime(1970, 1, 1) + timedelta(seconds=seconds)


def parse_hdata(grammar, path, keys, length):
    hdata = {
        'path': path,
        'keys': keys,
        'values': [],
    }

    for _ in range(length):
        val = {
            '_pointers': [],
        }

        for p in path:
            pointer, _ = grammar.apply('o_ptr')
            val['_pointers'].append((p, pointer))

        for name, t in keys:
            val[name], _ = grammar.apply('o_' + t)

        hdata['values'].append(val)

    return hdata


RelayParser = makeGrammar(grammar, {
    'bytes_to_int': bytes_to_int,
    'ascii_to_datetime': ascii_to_datetime,
    'parse_hdata': parse_hdata,
}, name='RelayParser')


def parse_message(data):
    try:
        return RelayParser(data).message()
    except ParseError as e:
        with open('crash_report.bin', 'w') as f:
            f.write(data)
        with open('crash_report', 'w') as f:
            f.write(str(e))

        raise SyntaxError('Error parsing weechat message.')
