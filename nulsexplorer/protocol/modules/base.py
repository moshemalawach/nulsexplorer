class BaseModuleData:
    def __init__(self, data_dict=None, data=None):
        self._data = dict()

        if data is not None:
            self.parse(data)

        if data_dict is not None:
            self._data = data_dict

    @classmethod
    def from_buffer(cls, buffer, cursor=0):
        raise NotImplementedError

    @classmethod
    def to_buffer(cls, data):
        raise NotImplementedError

    def parse(self, data, cursor=0):
        self._data, cursor = self.from_buffer(data, cursor=cursor)
        return cursor

    def serialize(self):
        return self.to_buffer(self._data)

    @classmethod
    def from_dict(cls, data):
        return cls(data_dict=data)

    def to_dict(self):
        return self._data
