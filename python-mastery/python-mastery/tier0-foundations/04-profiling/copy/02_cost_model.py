"""0.4 — CPython cost model, demonstrated. Numbers vary by machine; the *ratios* are the lesson."""
import timeit
from dataclasses import dataclass

N = 200_000
data = list(range(N))


def bench(label: str, stmt: str, setup: str = "", number: int = 20) -> float:
    g = {**globals()}
    t = min(timeit.repeat(stmt, setup, globals=g, number=number, repeat=3)) / number
    print(f"  {label:<48} {t * 1e3:8.2f} ms")
    return t


print("== loop forms ==")
bench("for + append", "out=[]\nfor x in data: out.append(x*2)")
bench("for + bound append", "out=[]\nap=out.append\nfor x in data: ap(x*2)")
bench("list comprehension", "[x*2 for x in data]")
bench("map + lambda", "list(map(lambda x: x*2, data))")
bench("numpy vectorised", "arr*2", "import numpy as np\narr=np.arange(N)")

print("== call overhead ==")
bench("inline x*2 in loop", "for x in data: y=x*2")
bench("call f(x) in loop", "for x in data: y=f(x)", "def f(x): return x*2")
bench("method call in loop", "for x in data: y=o.f(x)",
      "class O:\n def f(self,x): return x*2\no=O()")

print("== lookups ==")
bench("global name in loop", "for x in data: y=N")
bench("local name in loop", "n=N\nfor x in data: y=n")
bench("attr lookup in loop", "for x in data: y=o.v", "class O: v=1\no=O()")
bench("attr hoisted", "v=o.v\nfor x in data: y=v", "class O: v=1\no=O()")

print("== membership ==")
bench("x in list (300)", "for x in data[:20000]: x in L", "L=list(range(300))")
bench("x in set  (300)", "for x in data[:20000]: x in S", "S=set(range(300))")

print("== strings ==")
bench("+= in loop (10k)", "s=''\nfor i in range(10000): s+=str(i)", number=50)
bench("''.join (10k)", "''.join(str(i) for i in range(10000))", number=50)
bench("f-string", "for x in data: s=f'{x}-{x}'")
bench("% format", "for x in data: s='%d-%d'%(x,x)")

print("== allocation ==")


@dataclass
class P:
    x: int
    y: int


@dataclass(slots=True)
class PS:
    x: int
    y: int


bench("tuple per element", "for x in data: t=(x,x)")
bench("dict per element", "for x in data: d={'x':x,'y':x}")
bench("dataclass per element", "for x in data: p=P(x,x)")
bench("slots dataclass per element", "for x in data: p=PS(x,x)")
import sys
print(f"  sizeof P: {sys.getsizeof(P(1,1)) + sys.getsizeof(P(1,1).__dict__)} B   PS: {sys.getsizeof(PS(1,1))} B")

print("== specialisation (3.11+): monomorphic vs polymorphic call site ==")
bench("monomorphic ints", "for x in data: y=x+1")
bench("polymorphic int/float alternating", "for x in mixed: y=x+1",
      "mixed=[i if i%2 else float(i) for i in data]")

print("== generator vs list in sum ==")
bench("sum(list comp)", "sum([x*x for x in data])")
bench("sum(gen expr)", "sum(x*x for x in data)")
