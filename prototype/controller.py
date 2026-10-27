# controller.py —— 模拟路由器侧 Controller（PeriKey 参考原型）
#
# 演示：注册(DSecret) -> 使用者 2FA 设新密 -> 换密前预约定(PRA) -> 应用 -> 设备自动重连

from crypto_core import derive_key, encrypt, gen_password


class Controller:
    def __init__(self):
        self.registry = {}      # device_id -> {dsecret, legacy, L, epoch}
        self.connected = set()  # 当前在线 device_id（PRA 仅对这些设备下发）
        self.current_k = None   # hostapd 当前使用的主密码
        self.epoch = 0
        self.pending_k = None   # 待切换的新密码

    # ---- 阶段0：注册 ----
    def enroll(self, device, legacy=False):
        self.registry[device.device_id] = {
            "dsecret": device.dsecret,
            "legacy": legacy,
            "L": None,
            "epoch": 0,
        }
        self.connected.add(device.device_id)
        if legacy:
            self.assign_legacy(device)

    def assign_legacy(self, device):
        """为老设备分配独立长密码 L_i（不参与主密码轮换）。"""
        L = gen_password(40)  # 很长 -> 抬高单台破解成本
        self.registry[device.device_id]["L"] = L
        device.legacy_l = L
        return L

    # ---- 阶段1：使用者经 2FA 设置新密码 ----
    def admin_set(self, new_k: str, tfa_ok: bool = True):
        if not tfa_ok:
            raise PermissionError("2FA 校验失败，拒绝改密")
        self.pending_k = new_k

    # ---- 阶段2：换密前预约定（PRA 核心）----
    def pre_rotation_agreement(self, encrypt_enabled: bool = True):
        """对每台在线设备，用其 DSecret 加密下发 pending_k。
        encrypt_enabled=False 模拟“未注册设备走明文下发”的弱化路径。"""
        deliveries = {}
        for did in list(self.connected):
            if self.registry[did]["legacy"]:
                continue  # 老设备不参与主密码轮换，维持独立长密码 L_i
            dsecret = self.registry[did]["dsecret"]
            if encrypt_enabled:
                key = derive_key(dsecret)
                ct = encrypt(key, self.pending_k.encode())
                deliveries[did] = ("cipher", ct)
            else:
                # 弱化路径：明文（仍处在已加密的 WiFi 会话内）
                deliveries[did] = ("plain", self.pending_k)
        return deliveries

    # ---- 阶段3：应用（热重载/重启）----
    def apply(self):
        self.current_k = self.pending_k
        self.epoch += 1

    # ---- 设备接入校验 ----
    def authenticate(self, device) -> bool:
        if device.legacy:
            return device.cur_k == self.registry[device.device_id]["L"]
        return device.cur_k == self.current_k
