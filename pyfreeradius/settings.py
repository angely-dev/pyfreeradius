from pydantic import BaseModel


class RadTables(BaseModel):
    radcheck: str = "radcheck"
    radreply: str = "radreply"
    radgroupcheck: str = "radgroupcheck"
    radgroupreply: str = "radgroupreply"
    radusergroup: str = "radusergroup"
    nas: str = "nas"
