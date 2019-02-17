#
# Code generator for opcodes
# Copyright 2019 Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

import yaml
import string
import sys
import argparse


# Need Python 3.6 or newer for stable insertion order dicts
assert sys.version_info >= (3, 6), 'Needs Python 3.6 or newer'


funcdefs = []
matchers = []
maskdefs = []
structdefs = []

parser = argparse.ArgumentParser(description='Generate opcode decoder code from YAML')
parser.add_argument('yamlfile', type=str, help='Path to opcodes.yaml')
parser.add_argument('outfile', type=str, help='Output filename (.h)')

args = parser.parse_args()

d = yaml.load(open(args.yamlfile))

def get_comment(props):
    if 'match' in props:
        return f' // always 0b{props["match"]}'
    return ''

for k, v in d.items():
    members = []
    offset = 64
    for member in v['members']:
        for mk, mv in member.items():
            if isinstance(mv, str):
                # Literal binary match
                mv = {'count': len(mv), 'match': mv}
            elif isinstance(mv, int):
                # Simple bit field
                mv = {'count': mv}

            if 'argtype' not in mv:
                mv['argtype'] = f'Imm{mv["count"]}'

            if 'offset' in mv:
                # Re-adjust offset and potentially insert DONTCARE bits
                new_offset = mv['offset'] + mv['count']
                assert new_offset <= offset, f'Offset {new_offset} must be less or equal to current offset {offset}'
                dontcare_bits = offset - new_offset
                if dontcare_bits != 0:
                    members.append(('DONTCARE', 64-offset, {'count': dontcare_bits, 'argtype': f'Imm{dontcare_bits}'}))
                    offset = new_offset

            members.append((mk, 64-offset, mv))
            offset -= mv['count']

    # Insert DONTCARE bits at the end (if any)
    if offset > 0:
        dontcare_bits = offset
        members.append(('DONTCARE', 64-offset, {'count': dontcare_bits, 'argtype': f'Imm{dontcare_bits}'}))
        offset = 0

    assert offset == 0, f'Definition of {k} does not fit in 64 bits'

    FUNC = f'{k.lower()}_decode'
    STRUCT = f'{k.lower()}_instruction'

    funcdefs.append(f'usse::InstructionResult {FUNC}({STRUCT} &op);')

    fields = '\n'.join(f'        u64 {name if name != "DONTCARE" else "_dontcare"+str(idx)} : {props["count"]};{get_comment(props)}'
                       for idx, (name, offset, props) in enumerate(reversed(members)))
    structdefs.append(f'union {STRUCT} {{\n    u64 instruction;\n    struct {{\n{fields}\n    }};\n}};')

    # Create match string and assign bit characters
    matchstr = ''
    for name, offset, props in members:
        count = props['count']
        if name == 'DONTCARE':
            matchstr += '?' * count
        elif 'match' in props:
            # Literal bit pattern match
            matchstr += props['match']
        else:
            matchstr += 'x' * count

    mask = ''.join('1' if c in '01' else '0' for c in matchstr)
    match = ''.join(c if c in '01' else '0' for c in matchstr)

    VAR_MASK = f'{k}_MASK'
    VAR_MATCH = f'{k}_MATCH'

    maskdefs.append(f'constexpr const u64 {VAR_MASK:20s} = 0b{mask}ULL;\nconstexpr const u64 {VAR_MATCH:20s} = 0b{match}ULL;')

    matchers.append(f'    if ((instr & {VAR_MASK}) == {VAR_MATCH}) {{\n        return {FUNC}(({STRUCT} &)(u64 &)instr);\n    }}')



def dump(fp):
    for maskdef in maskdefs:
        print(maskdef, file=fp)
        print('', file=fp)

    for structdef in structdefs:
        print(structdef, file=fp)
        print('\n', file=fp)

    for funcdef in funcdefs:
        print(funcdef, file=fp)

    print('', file=fp)

    print('usse::InstructionResult decode_usse_instruction(u64 instr) {', file=fp)
    for matcher in matchers:
        print(matcher, file=fp)
    print('    return boost::none;', file=fp)
    print('}', file=fp)


dump(open(args.outfile, 'w'))
