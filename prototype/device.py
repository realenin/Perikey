# device.py —— 模拟网内设备（Enrollee，PeriKey 参考原型）

from crypto_core import gen_dsecret, derive_key, decrypt, gen_password


class Device:
    def __init__(self, name: str, legacy: bool = False):
        self.name = name
        self.legacy = legacy
        self.dsecret = None
        self.device_id = "dev-" + gen_password(4)
        self.epoch = 0
        self.cur_k = None        # 当前用于接入的密码
        self.pending_k = None    # PRA 收到的待切换密码
        self.legacy_l = None     # 老设备独立长密码

    # ---- 阶段0：首次联网（使用者输入密码）----
    def first_connect(self, controller, network_k: str):
        self.cur_k = network_k
        self.dsecret = gen_dsecret()
        controller.enroll(self, legacy=self.legacy)
        if self.legacy:
            # 老设备用独立长密码接入，而不用主密码
            self.cur_k = self.legacy_l
        return self.dsecret

    # ---- 阶段2：接收预约定 ----
    def accept_pra(self, delivery):
        kind, payload = delivery
        if kind == "cipher":
            key = derive_key(self.dsecret)
            self.pending_k = decrypt(key, payload).decode()
        else:  # plain
            self.pending_k = payload
        return self.pending_k

    # ---- 阶段4：路由器应用后自动重连 ----
    def reconnect(self):
        if self.legacy:
            return  # 老设备维持独立长密码 L_i，不随主密码轮换
        if self.pending_k:
            self.cur_k = self.pending_k
            self.pending_k = None
