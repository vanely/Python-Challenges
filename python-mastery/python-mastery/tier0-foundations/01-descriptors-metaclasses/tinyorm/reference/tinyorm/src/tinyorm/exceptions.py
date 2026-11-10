class TinyOrmError(Exception):
    pass


class ValidationError(TinyOrmError):
    pass


class DoesNotExist(TinyOrmError):
    pass


class MultipleObjectsReturned(TinyOrmError):
    pass
