from skoolkittest import SkoolKitTestCase, as_dword
from skoolkit.tape import SkoolKitError, parse_pzx, write_pzx, write_tap

def get_pzx_blocks(fname):
    blocks = []
    with open(fname, 'rb') as f:
        pzx = f.read()
    i = 0
    while i < len(pzx):
        block_id = ''.join(chr(b) for b in pzx[i:i + 4])
        i += 4
        block_len = pzx[i] + 256 * pzx[i + 1] + 65536 * pzx[i + 2] + 16777216 * pzx[i + 3]
        i += 4
        blocks.append((block_id, tuple(pzx[i:i + block_len])))
        i += block_len
    return blocks

def get_tap_blocks(fname):
    blocks = []
    with open(fname, 'rb') as f:
        tap = f.read()
    i = 0
    while i + 1 < len(tap):
        block_len = tap[i] + 256 * tap[i + 1]
        blocks.append(list(tap[i + 2:i + 2 + block_len]))
        i += block_len + 2
    return blocks

def to_pzx_data(data):
    bits = 0x80000000 + len(data) * 8
    return (
        *as_dword(bits), # Polarity and bit count
        177, 3,          # Tail pulse (945)
        2, 2,            # p0, p1
        87, 3, 87, 3,    # s0 (855, 855)
        174, 6, 174, 6,  # s1 (1710, 1710)
        *data            # Data
    )

class PZXTest(SkoolKitTestCase):
    def _get_pzxt(self):
        return bytearray((
            80, 90, 88, 84, # PZXT
            2, 0, 0, 0,     # Block length (2)
            1, 0,           # Major/minor version number
        ))

    def test_pzx_file_too_short(self):
        pzx = b'PZXT'
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'Not a PZX file')

    def test_pzxt_block_missing_data(self):
        pzx = bytes((
            80, 90, 88, 84, # PZXT
            5, 0, 0, 0,     # Block length (5)
            0, 0            # 2 bytes instead of 5
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PZXT block missing 3 byte(s)')

    def test_pzxt_block_too_short(self):
        pzx = bytes((
            80, 90, 88, 84, # PZXT
            1, 0, 0, 0,     # Block length (1)
            0
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PZXT block length (1) is too small')

    def test_data_block_missing_data(self):
        pzx = self._get_pzxt()
        pzx.extend((
            68, 65, 84, 65, # DATA
            5, 0, 0, 0,     # Block length (5)
            0               # 1 byte instead of 5
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'DATA block missing 4 byte(s)')

    def test_data_block_too_short(self):
        pzx = self._get_pzxt()
        pzx.extend((
            68, 65, 84, 65, # DATA
            7, 0, 0, 0,     # Block length (7)
            1, 0, 0, 0,     # count
            0, 0,           # tail
            2               # p0
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'DATA block length (7) is too small')

    def test_data_block_missing_data_in_s0_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            68, 65, 84, 65, # DATA
            11, 0, 0, 0,    # Block length (11)
            1, 0, 0, 0,     # count
            0, 0,           # tail
            2,              # p0
            2,              # p1
            1, 0, 1         # s0 (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'DATA block missing 1 byte(s) in s0 field')

    def test_data_block_missing_data_in_s1_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            68, 65, 84, 65, # DATA
            15, 0, 0, 0,    # Block length (15)
            1, 0, 0, 0,     # count
            0, 0,           # tail
            2,              # p0
            2,              # p1
            1, 0, 1, 0,     # s0
            2, 0, 2         # s1 (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'DATA block missing 1 byte(s) in s1 field')

    def test_data_block_missing_data_in_data_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            68, 65, 84, 65, # DATA
            17, 0, 0, 0,    # Block length (17)
            16, 0, 0, 0,    # count
            0, 0,           # tail
            2,              # p0
            2,              # p1
            1, 0, 1, 0,     # s0
            2, 0, 2, 0,     # s1
            0               # data (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'DATA block missing 1 byte(s) in data field')

    def test_puls_block_missing_data(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 85, 76, 83, # PULS
            5, 0, 0, 0,     # Block length (5)
            0, 0, 0         # 3 bytes instead of 5
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PULS block missing 2 byte(s)')

    def test_puls_block_missing_data_in_count_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 85, 76, 83, # PULS
            1, 0, 0, 0,     # Block length (1)
            0               # count (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PULS block missing 1 byte(s) in count/duration1 field')

    def test_puls_block_missing_data_in_duration1_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 85, 76, 83, # PULS
            3, 0, 0, 0,     # Block length (3)
            1, 128,         # count
            0               # duration1 (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PULS block missing 1 byte(s) in duration1 field')

    def test_puls_block_missing_data_in_duration2_field(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 85, 76, 83, # PULS
            5, 0, 0, 0,     # Block length (5)
            1, 128,         # count
            1, 128,         # duration1
            0               # duration2 (1 byte short)
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PULS block missing 1 byte(s) in duration2 field')

    def test_paus_block_missing_data(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 65, 85, 83, # PAUS
            5, 0, 0, 0,     # Block length (5)
            0, 0            # 2 bytes instead of 5
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PAUS block missing 3 byte(s)')

    def test_paus_block_too_short(self):
        pzx = self._get_pzxt()
        pzx.extend((
            80, 65, 85, 83, # PAUS
            3, 0, 0, 0,     # Block length (3)
            0, 0, 0
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'PAUS block length (3) is too small')

    def test_stop_block_missing_data(self):
        pzx = self._get_pzxt()
        pzx.extend((
            83, 84, 79, 80, # STOP
            5, 0, 0, 0,     # Block length (5)
            0, 0, 0, 0      # 4 bytes instead of 5
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'STOP block missing 1 byte(s)')

    def test_stop_block_too_short(self):
        pzx = self._get_pzxt()
        pzx.extend((
            83, 84, 79, 80, # STOP
            1, 0, 0, 0,     # Block length (1)
            0
        ))
        with self.assertRaises(SkoolKitError) as cm:
            parse_pzx(pzx)
        self.assertEqual(cm.exception.args[0], 'STOP block length (1) is too small')

class TapeWriteTest(SkoolKitTestCase):
    def test_write_pzx(self):
        blocks = ([0, 1, 2], [255, 4, 5, 6, 7], [255, 8, 9, 10])
        pzxfile = 'test_write_pzx.pzx'
        write_pzx(pzxfile, blocks)
        pzx_blocks = get_pzx_blocks(pzxfile)
        puls_long = (127, 159, 120, 8, 155, 2, 223, 2)
        puls_short = (151, 140, 120, 8, 155, 2, 223, 2)
        paus = (224, 103, 53, 0) # 3500000 T-states
        exp_blocks = (
            ('PZXT', (1, 0)),
            ('PULS', puls_long),
            ('DATA', to_pzx_data(blocks[0])),
            ('PAUS', paus),
            ('PULS', puls_short),
            ('DATA', to_pzx_data(blocks[1])),
            ('PAUS', paus),
            ('PULS', puls_short),
            ('DATA', to_pzx_data(blocks[2]))
        )
        self.assertEqual(len(pzx_blocks), len(exp_blocks))
        for (exp_id, exp_data), (block_id, data) in zip(exp_blocks, pzx_blocks):
            self.assertEqual(block_id, exp_id)
            self.assertEqual(exp_data, data)

    def test_write_tap(self):
        blocks = ([0, 1, 2], [3, 4, 5, 6, 7])
        tapfile = 'test_write_tap.tap'
        write_tap(tapfile, blocks)
        tap_blocks = get_tap_blocks(tapfile)
        self.assertEqual(len(tap_blocks), len(blocks))
        self.assertEqual(blocks[0], tap_blocks[0])
        self.assertEqual(blocks[1], tap_blocks[1])
