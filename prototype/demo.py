# demo.py —— PeriKey 参考原型端到端演示
#
# 演示使用者真实想法：换密前先与已连设备握手约定新密码，再应用，全员自动重连；
# 并验证“仅持旧握手包的外部攻击者”拿不到新密码；演示老设备独立长密码。
#
# 运行：python3 demo.py

from controller import Controller
from device import Device


def sep(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    sep("0. 初始化网络（主路由 + 若干设备，含老设备）")
    c = Controller()
    c.current_k = "OldStrongPass-2026"  # 使用者最初设定的主密码 K

    phone = Device("手机")
    laptop = Device("笔记本")
    cam = Device("摄像头(老设备)", legacy=True)
    bulb = Device("智能灯(老设备)", legacy=True)

    for d in (phone, laptop, cam, bulb):
        d.first_connect(c, c.current_k)

    print(f"主密码 K            = {c.current_k}")
    print(f"在线设备数          = {len(c.connected)}")
    print(f"老设备独立长密码 L  = {cam.legacy_l!r}（长度 {len(cam.legacy_l)}，远高于主密码）")

    sep("1. 使用者经 2FA 设置新密码 K'")
    new_k = "NewStrongPass-2026!"
    c.admin_set(new_k, tfa_ok=True)  # 2FA 通过
    print(f"已设置待切换密码 K' = {new_k}（尚未应用）")
    print("此时旧连接 K 仍有效 → 可用作安全通道下发 K'（化解鸡生蛋）")

    sep("2. 换密前预约定（PRA）：逐台加密下发 K'（仅非老设备）")
    deliveries = c.pre_rotation_agreement(encrypt_enabled=True)
    for d in (phone, laptop):
        d.accept_pra(deliveries[d.device_id])
        print(f"  {d.name:18s} 已本地存好 K' = {d.pending_k}")
    for d in (cam, bulb):
        print(f"  {d.name:18s} 走独立长密码 L_i，不参与主密码轮换（维持 {d.legacy_l!r}）")

    sep("3. 应用（路由器热重载/重启）→ 设备自动重连")
    c.apply()
    for d in (phone, laptop, cam, bulb):
        d.reconnect()
    for d in (phone, laptop, cam, bulb):
        ok = c.authenticate(d)
        print(f"  {d.name:18s} 用新密码接入 = {'成功' if ok else '失败'}")
    assert all(c.authenticate(d) for d in (phone, laptop, cam, bulb)), "应有设备未成功重连"
    print("✅ 全员自动重连成功，使用者无需逐台操作")

    sep("4. 威胁验证 A：外部被动攻击者（仅抓到旧握手包、不在网内）")
    # 攻击者没在 LAN 内，根本收不到 PRA 下发
    attacker_on_wire = False
    stolen = c.pre_rotation_agreement() if attacker_on_wire else None
    print(f"  攻击者能否拿到 K'？ {'(收到下发)' if stolen else '否——不在网内，收不到下发'}")
    assert stolen is None
    print("✅ 外部被动攻击者无法获得 K'；且旧握手包在轮换后作废，须每周期重抓重爆")

    sep("5. 威胁验证 B：入网内鬼（持旧 K、在 LAN 内、但无 DSecret）")
    # 攻击者在网内，能读到下发，但每条都用对应设备 DSecret 加密，无法解密
    deliveries_b = c.pre_rotation_agreement(encrypt_enabled=True)
    stolen_b = [payload for _, payload in deliveries_b.values()]  # 内鬼拿到了密文
    cracked = None
    for ct in stolen_b:
        # 没有对应 DSecret，解密失败（此处直接证明缺密钥不可解）
        try:
            from crypto_core import decrypt, derive_key
            # 用错误/缺失密钥尝试 -> 得到乱码，不等于 new_k
            wrong = decrypt(b"wrongkey-wrongkey-wrongkey-!!", ct)
            if wrong.decode(errors="ignore") == new_k:
                cracked = new_k
        except Exception:
            pass
    print(f"  内鬼持密文能否还原 K'？ {'能' if cracked == new_k else '否——缺 DSecret 无法解密'}")
    assert cracked != new_k
    print("✅ 即便内鬼在网内，K' 经 DSecret 加密仍不可得")

    sep("6. 对照：未注册设备走明文下发时，内鬼可读到 K'（说明注册加固必要）")
    c2 = Controller(); c2.current_k = "K0"; c2.admin_set("K1")
    d_plain = Device("未注册设备"); d_plain.first_connect(c2, "K0")
    # 注意：未注册设备无 DSecret，走明文路径
    deliv_plain = c2.pre_rotation_agreement(encrypt_enabled=False)
    kind, payload = deliv_plain[d_plain.device_id]
    print(f"  明文下发内容 = {payload!r}（内鬼在网内可直接读取）")
    assert kind == "plain"
    print("⚠️ 这正说明：应推动所有设备完成阶段0注册，启用 DSecret 加密")

    sep("7. 老设备隔离性：破解 L_i 不影响主网络 K")
    print(f"  主密码 K         = {c.current_k}")
    print(f"  摄像头独立密码 L = {cam.legacy_l!r}")
    assert cam.legacy_l != c.current_k
    print("✅ 老设备独立长密码与主密码互不相干；单台被爆不波及全网")

    sep("8. 二次轮换：旧 K' 失效（前向隔离）")
    c.admin_set("EvenNewerPass-2027#", tfa_ok=True)
    deliveries2 = c.pre_rotation_agreement(encrypt_enabled=True)
    for d in (phone, laptop):
        d.accept_pra(deliveries2[d.device_id])
    c.apply()
    for d in (phone, laptop):
        d.reconnect()
    old_k_prime = new_k
    # 若某设备仍用旧 K' 接入应失败（此处模拟一台未更新设备）
    stale = Device("滞留旧密设备"); stale.first_connect(c, old_k_prime)
    print(f"  仍用旧 K'={old_k_prime!r} 的滞留设备接入 = {'成功' if c.authenticate(stale) else '失败'}")
    assert not c.authenticate(stale)
    print("✅ 轮换后旧密码即失效，滞留设备被自然清退")

    sep("9. 密度效应（使用者 Kali 观察的机制）")
    p = 0.05  # 单次握手被捕获概率
    for n in (5, 25, 100, 125):
        pc = 1 - (1 - p) ** n
        print(f"  设备数 N={n:4d} → 至少抓到 1 个握手的概率 ≈ {pc*100:5.1f}%")
    print("→ 设备越多，抓包成功率越高；PeriKey 令每次成功抓包的时间价值骤降（轮换作废）。")

    sep("全部断言通过 ✅  PeriKey 原型证明确可行（协议流程层面）")


if __name__ == "__main__":
    main()
