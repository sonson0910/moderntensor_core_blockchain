from mt_aptos.network.app.model.base_model import BaseModel


class User(BaseModel):
    net_uid: int
    addr: str
    hot_key: str
    reg_key: str
    role: int
    reg_name: str
