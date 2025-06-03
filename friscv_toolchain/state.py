class State:
    def __init__(
            self,
            core: int | None = None,
            pc: str | None = None,
            inst: str | None = None,
            disasm: str | None = None,
            regs: dict[int, str] = {},
            stores: list[tuple[str, str]] = []
        ) -> None:
        self.core = core
        self.pc = pc
        self.inst = inst
        self.disasm = disasm
        self.regs = regs
        self.stores = stores