"""db: connection pool wrapper for the sample project."""
POOL_SIZE=8
class ConnectionPool:
    def __init__(self,dsn:str,size:int=POOL_SIZE):
        self.dsn=dsn;self.size=size;self._connections=[]
    def acquire(self):
        if not self._connections:return self._connect()
        return self._connections.pop()
    def release(self,conn):
        if len(self._connections)<self.size:self._connections.append(conn)
    def _connect(self):return {'dsn':self.dsn,'closed':False}
