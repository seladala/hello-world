# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
from .compiler import AssembledProgram, AssemblyError, assemble
from .inspector import disassemble
from .executor import Machine, MachineFault

__all__ = ["AssembledProgram", "AssemblyError", "Machine", "MachineFault", "assemble", "disassemble"]
