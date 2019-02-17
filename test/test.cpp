#include <cstdio>
#include <cstdint>

// Fake enough of the target environment to get it to build

namespace usse {
    using InstructionResult = uint64_t;
};

namespace boost {
    uint64_t none = -1;
};

using u64 = uint64_t;

#include "../opcodes_gen.h"

usse::InstructionResult vmov_decode(vmov_instruction &op)
{
    printf("Got vmov instruction\n");
    return 1;
}

usse::InstructionResult vmadsi_decode(vmadsi_instruction &op)
{
    printf("Got vmadsi instruction\n");
    return 2;
}

usse::InstructionResult vmad4_decode(vmad4_instruction &op)
{
    printf("Got vmad4 instruction\n");
    return 3;
}

usse::InstructionResult phas_decode(phas_instruction &op)
{
    printf("Got phas instruction\n");
    return 4;
}

usse::InstructionResult spec_decode(spec_instruction &op)
{
    printf("Got spec instruction, category=%llu, special=%llu\n", op.category, op.special);
    return 5;
}

int main()
{
    spec_instruction instr;

    instr.op1 = 0b11111;
    instr.category = 3;
    instr.special = 1;

    usse::InstructionResult result = decode_usse_instruction(instr.instruction);
    printf("Decode result: %llu (expected 5)\n", result);

    return (result == 5) ? 0 : 1;
}
