# 系统架构（Architecture）

## 1. 角色（Roles）

| 角色 | 实体 | 职责 |
|------|------|------|
| **Admin（使用者）** | 人 | 经 2FA 门控设置主密码 `K` 与轮换策略 |
| **Controller（控制器）** | 运行于路由器的守护进程 | 注册设备、换密前预约定、维护 `DSecret` 注册表、热重载 `hostapd` |
| **Enrollee（设备）** | 网内终端 | 首次联网建 `DSecret_i`；换密前接收并本地存 `K'`；用其重连 |
| **AP / hostapd** | 路由器无线子系统 | 执行实际认证，读取 `wpa_psk_file`（主密码 + 老设备独立密码） |

## 2. 三平面分离

```
┌──────────────────────────────────────────────────────────┐
│  管理平面 (Management)  —— 受 2FA 保护                    │
│  Admin ──2FA──▶ Controller.Config (K, 轮换周期)           │
└──────────────────────────────────────────────────────────┘
                           │ 触发轮换
                           ▼
┌──────────────────────────────────────────────────────────┐
│  控制平面 (Control)  —— 换密前预约定 (PRA)               │
│  Controller ──Enc(DSecret_i, K')──▶ 各已连设备            │
│  设备本地存 K'，回 ACK（旧连接作安全通道，化解鸡生蛋）   │
└──────────────────────────────────────────────────────────┘
                           │ 应用 + 热重载
                           ▼
┌──────────────────────────────────────────────────────────┐
│  数据平面 (Data)  —— 实际无线通信                         │
│  设备 ──K'──▶ hostapd (wpa_psk_file)                     │
│  老设备 ──L_i（独立长密码，不参与轮换）──▶ hostapd       │
└──────────────────────────────────────────────────────────┘
```

## 3. Controller 模块划分

```
perikey-controller/
├── enrollment/      # 首次联网：生成/存储 DSecret_i，绑定 DeviceID_i
├── crypto/          # HKDF、AES-GCM 信封加密（见 protocol.md）
├── distribution/    # 换密前对已连设备逐台加密下发 K'（PRA 核心）
├── rotation/        # 周期调度：epoch+1、重算、推送 hostapd
├── admin/           # 2FA 门控的管理 API + Web UI（LuCI 插件）
├── legacy/          # 老设备独立长密码 L_i 的分配与保管
└── hostapd_bridge/  # 写 /etc/hostapd.wpa_psk 并 reload（替代整机重启）
```

## 4. hostapd 集成点

OpenWrt 侧：

```
# /etc/config/wireless
option encryption 'sae-mixed'        # 或 psk2+ccmp；推荐 WPA3-SAE
option wpa_psk_file '/etc/hostapd.wpa_psk'
# 移除单一 option key，改由文件提供
```

`/etc/hostapd.wpa_psk` 由 Controller 生成：

```
<DeviceID_主> <K'_hex>          # 主密码（轮换后的值）
<DeviceID_老1> <L_1_hex>        # 老设备独立长密码
<DeviceID_老2> <L_2_hex>
```

`hostapd` 重载配置即生效，**无需整机重启**（使用者原话的「重启」在实现上等价替换为热重载）。

## 5. 部署形态

- **首选**：OpenWrt 软件包（opkg），守护进程 + LuCI 插件提供 2FA 管理界面。
- **备选**：独立单板（如树莓派）作 Controller，经 SSH/API 改写主路由的 `hostapd` 配置（适用于不可刷 OpenWrt 的主路由）。
- **主副路由场景**：使用者家中为主路由 + 副路由，需保证两者 `K'` 与 `L_i` 一致同步（P5）。
