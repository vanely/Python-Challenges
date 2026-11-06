"""T2 w1 — reading bytecode. Run and read alongside the dis opcode table."""
import dis
import sys

print(sys.version_info[:2])


def loop(xs: list[int]) -> int:
    total = 0
    for x in xs:
        total += x
    return total


print("=== simple loop: LOAD_FAST / FOR_ITER / BINARY_OP / JUMP_BACKWARD ===")
dis.dis(loop)


def make_adder(n: int):  # type: ignore[no-untyped-def]
    def add(x: int) -> int:
        return x + n                        # n is a free variable -> LOAD_DEREF
    return add


print("=== closure: MAKE_CELL / LOAD_DEREF / MAKE_FUNCTION with closure ===")
dis.dis(make_adder)


def comp(xs: list[int]) -> list[int]:
    return [x * 2 for x in xs]             # 3.12+: inlined (PEP 709) — no nested code object


print("=== comprehension (3.12: inlined; 3.11: separate <listcomp> code object + CALL) ===")
dis.dis(comp)


class C:
    def __init__(self) -> None:
        self.attr = 1                       # instance attribute -> LOAD_ATTR_INSTANCE_VALUE when warm

    def m(self, x: int) -> int:
        return self.attr + x


print("=== method call site: LOAD_ATTR (method flag) + CALL, with inline CACHE slots ===")


def call_site(c: C) -> int:
    return c.m(1)


dis.dis(call_site, show_caches=True)

print("=== adaptive specialisation: same function before and after warm-up ===")


def hot(o: C) -> int:
    return o.attr + o.m(2)


print("-- cold --")
dis.dis(hot, adaptive=True)
for _ in range(2000):                      # the site specialises after a few executions
    hot(C())
print("-- warm: look for *_INSTANCE_VALUE / *_ADD_INT / CALL_PY_EXACT_ARGS etc. --")
dis.dis(hot, adaptive=True)

print("=== stack effect: annotate ops by hand, then check with dis.stack_effect ===")
for ins in dis.get_instructions(loop):
    eff = dis.stack_effect(ins.opcode, ins.arg) if ins.opcode >= dis.HAVE_ARGUMENT else dis.stack_effect(ins.opcode)
    print(f"  {ins.offset:3} {ins.opname:<22} {str(ins.argrepr):<10} stack{eff:+d}")

print("=== code object attributes ===")
co = loop.__code__
print(co.co_varnames, co.co_consts, co.co_stacksize, co.co_flags, len(co.co_code))
print("line table:", list(co.co_lines())[:4])
