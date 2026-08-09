class NetworkDisabledError(RuntimeError):
    pass

class NoNetworkTransport:
    def get_json(self, path, params=None):
        raise NetworkDisabledError("Broker Integration V1 default transport forbids network access.")

class FixtureTransport:
    def __init__(self, responses=None):
        self.responses=dict(responses or {})
        self.calls=[]

    def get_json(self, path, params=None):
        self.calls.append({"method":"GET","path":path,"params":params or {}})
        if path not in self.responses:
            raise KeyError(path)
        return self.responses[path]
