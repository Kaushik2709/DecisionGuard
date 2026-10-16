class GuardError(Exception):
    def __reduce__(self) -> tuple[type["GuardError"], tuple[str, str]]:
        return type(self), (self.code, self.message)

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise GuardError(code, message)
