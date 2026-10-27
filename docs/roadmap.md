# 路线图（Roadmap）

> 从参考原型到可在普通 OpenWrt 硬件落地的家庭产品化管理层。

## 阶段 P0 — 参考原型（本仓库 `prototype/`）
- [x] 零依赖 Python 演示：注册 → 换密前预约定 → 应用 → 自动重连
- [x] 演示「外部仅持旧握手包者拿不到新密码」
- [x] 演示老设备独立长密码路径
- [ ] 将演示密码学替换为 HKDF + AES-GCM 标注版（当前为 SHA-256 密钥流演示密码）

## 阶段 P1 — OpenWrt 守护进程（最小可用）
- [ ] `enrollment`：设备首次联网建立并存储 `DSecret_i`
- [ ] `distribution`：换密前对已连设备逐台加密下发 `K'`
- [ ] `hostapd_bridge`：将 `K'` 与 `L_i` 写入 `/etc/hostapd.wpa_psk` 并 **热重载**（替代整机重启）
- [ ] `rotation`：周期调度 + epoch 管理

## 阶段 P2 — 2FA 管理平面
- [ ] LuCI 插件：使用者经 2FA 设置/更换 `K` 与轮换策略
- [ ] 审计日志：谁、何时、改了什么

## 阶段 P3 — 老设备与兼容
- [ ] PPSK 管理：为不兼容设备分配/轮换独立长密码 `L_i`
- [ ] 引导 SSID：离线/重置设备的 2FA 重新约定入口

## 阶段 P4 — 加固
- [ ] `DSecret_i` 用 HKDF-SHA256 派生 AES-256-GCM 密钥（替换演示密码）
- [ ] `DSecret_i` 周期性自轮换
- [ ] 撤销与注册表一致性校验
- [ ] `DeviceID` 采用设备身份指纹（抗 MAC 随机化）

## 阶段 P5 — 硬件验证与发布
- [ ] 在 MT798x / IPQ 等 OpenWrt 可刷硬件实测
- [ ] 多 AP（主副路由）场景下 `K'` 一致性同步
- [ ] opkg 打包 + 文档 + 安全披露渠道

## 当前状态

处于 **P0**。下一步建议认领 P1 的 `hostapd_bridge` 与 `distribution` 模块，作为首个可跑的最小实现。
