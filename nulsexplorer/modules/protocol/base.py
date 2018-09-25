class BaseModuleData:
    def __init__(self, data_dict=None, data=None):
        self._data = dict()

        #if data is not None:
        #    self.parse(data)

        if data_dict is not None:
            self._data = data_dict

    @classmethod
    async def from_buffer(cls, buffer, cursor=0):
        raise NotImplementedError

    @classmethod
    async def to_buffer(cls, data):
        raise NotImplementedError

    async def parse(self, data, cursor=0):
        self._data, cursor = await self.from_buffer(data, cursor=cursor)
        return cursor

    async def serialize(self):
        return await self.to_buffer(self._data)

    @classmethod
    async def from_dict(cls, data):
        c = cls(data_dict=data)

    async def to_dict(self):
        return self._data
