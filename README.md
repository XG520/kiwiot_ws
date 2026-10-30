# KiwiOT 优智云家智能门锁组件

这是一个用于 Home Assistant 的 KiwiOT 智能门锁自定义组件。支持智能门锁事件监控、状态显示和用户管理等功能。

为了方便bug反馈，建议使用issue功能进行反馈。或者加qq群(964512589)进行交流。

### v1.1.18 版本更新日志
- 卸载集成时停止 WebSocket 任务，修复实体删除不彻底

### v1.1.17 版本更新日志
- 统一 device_info（带 name），修复部分实体 ID 不一致

### v1.1.16 版本更新日志
- 缩短实体 ID：设备名去掉家庭名前缀，用户实体名去掉设备名（设 has_entity_name）

### v1.1.15 版本更新日志
- 门锁事件实体新增「欢迎词」属性（含括号取括号前、无括号取主人、空则空）
- camera 实体「事件时间/created_at」转北京时间，与其他实体对齐

### v1.1.14 版本更新日志
- WebSocket 定期重新订阅，防止订阅静默失效
- 断连重连后补拉最新事件，弥补断连期间丢事件

### v1.1.13 版本更新日志
- config flow 添加时校验账号密码
- 支持重新配置（齿轮按钮 options flow），手机号默认 +86，密码/Client ID 字段隐藏

### v1.1.12 版本更新日志
- 新增指静脉冻结（LOCK_FINGER_VEIN_FRONZEN）、主动监控（ACTIVE_MONITOR）事件映射

### v1.1.11 版本更新日志
- 补全指静脉（FINGER_VEIN）开锁方式映射
- 修复缓存清理的阻塞文件操作（避免阻塞 HA 事件循环）

### v1.1.10 版本更新日志
修复 WebSocket 连接失败的问题

## 功能特点
- 支持远程开锁
- 实时监控门锁状态变化
- 支持多种开锁方式识别和显示
- 提供详细的事件记录和状态属性
- 支持用户管理和别名显示
- 支持图片预览

## 安装指引

### 方式一：HACS一键安装（推荐）
1. 确保已经安装了 [HACS](https://hacs.xyz/)
1. 在HACS中点击"自定义存储库"
1. 添加此仓库地址：`https://github.com/lxg20082008/kiwiot_ws`
1. 类别选择"集成"
1. 点击"添加"
1. 在HACS的集成页面中搜索"KiwiOT"
1. 点击"下载"进行安装
1. 重启Home Assistant

### 方式二：手动安装
1. 下载此仓库的最新版本
1. 将 `custom_components/kiwiot_ws` 文件夹复制到你的Home Assistant配置目录下的 `custom_components` 文件夹中
1. 重启Home Assistant

## 配置说明

通过 Home Assistant 的集成页面添加，需要提供以下信息：
- 手机号（+86开头）
- 密码
- Client ID (抓包获取)
- 是否忽略SSL证书验证（可选）


## 支持的实体类型

- 家庭信息 (sensor.xxx_info)
- 门锁状态 (sensor.xxx_status)
- 门锁事件 (sensor.xxx_event)
- 用户别名 (text.xxx_user_x)
- 远程开锁密码 (text.xxx_password_input)
- 远程开锁数据 (text.xxx_unlock_data_input)
- 确认开锁 (button.xxx_password_confirm)
- 最近一次图像事件 (camera.xxx_camera)

## 使用方法

### 图像预览（摄像头实体）
摄像头实体会自动获取最近一次门锁事件抓拍的图片，可直接在 Lovelace 仪表盘中使用：

**Picture Glance 卡片（推荐）：**

```yaml
type: picture-glance
camera_image: camera.xxx_zui_jin_yi_ci_tu_xiang_shi_jian
entities:
  - entity: sensor.xxx_men_suo_zhuang_tai
```

**Picture Entity 卡片：**

```yaml
type: picture-entity
entity: camera.xxx_zui_jin_yi_ci_tu_xiang_shi_jian
show_entity_picture: true
```

> 注意：摄像头显示的是**最近一次带抓拍图片**的事件。如果两次开门之间没有触发拍照（如单纯指纹开锁无抓拍），图片不会更新。按门铃、有人徘徊等事件通常会触发抓拍。

### 远程开锁
1. 在 **远程开锁密码**（`text.xxx_yuan_cheng_kai_suo_mi_ma`）中输入优智云家 APP 的安全密码
1. 在 **远程开锁数据**（`text.xxx_yuan_cheng_kai_suo_shu_ju`）中填入开锁数据
1. 点击 **确认开锁**（`button.xxx_que_ren_kai_suo`）按钮执行

> **开锁数据（unlock_data）抓包方法**：电脑网页登录优智云家控制台（`go.kiwik.cn`）→ 按 F12 打开开发者工具 → 在刚登录的网页中操作一次远程开门 → 在 WebSocket 消息里找 `name` 值为 `Ctrl` 的那条，其 payload 末端的 `data` 字段就是开锁数据。

### 用户别名
- **用户别名**（`text.xxx_user_x`）实体可直接修改用户显示名称，最长 16 个字符
- 修改后门锁事件中将显示自定义别名，便于识别开锁人

> 注意区分「用户别名」和「友好名称」：
> - **用户别名** = 实体的 state（值），存优智云家云端，门锁事件用它；改法是改值（text 实体可直接编辑）或用 `text.set_value`。
> - **友好名称**（friendly_name）= HA 实体显示名（默认「XXX User N」），在「实体设置 → 名称」里改，只影响 HA 显示，不影响门锁事件。

**欢迎词**：门锁事件实体带「欢迎词」属性，用于开门欢迎语自动化（配合别名格式 `YY(XX手指)`）：

| 别名情况 | 欢迎词 | 播报 |
| --- | --- | --- |
| 含 `(` | `(` 前的 YY | 欢迎 YY 回家 |
| 空 | 空 | 欢迎回家 |
| 无 `(` | 主人 | 欢迎主人回家 |

## 注意事项

- 需要稳定的网络连接
- 建议定期检查更新以获得最新功能和修复
- 如遇到问题，请通过此地址：https://bbs.hassbian.com/forum.php?mod=viewthread&tid=27837&page=5#pid661852 教程开启日志模式，提供更多调试信息

## 赞赏支持
如果您觉得这个项目对您有帮助，欢迎打赏支持，这将鼓励我继续维护和改进该项目！

<table>
  <tr>
    <td align="center">微信赏码</td>
    <td align="center">支付宝赏码</td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/wechat.png" alt="微信赞赏码" width="200"/></td>
    <td align="center"><img src="docs/images/alipay.jpg" alt="支付宝赞赏码" width="200"/></td>
  </tr>
</table>

## 免责声明 
 1. 本插件仅用于学习研究，禁止用于商业用途
 1. 本插件不保证准确性、可靠性、完整性和及时性
 1. 任何个人或组织均可无需经过通知而自由使用
 1. 作者对任何插件问题概不负责，包括由此产生的任何损失
 1. 请勿将本插件用于商业用途，由此引起的问题与作者无关
 1. 本插件及其更新版权归作者所有
- **使用本插件默认同意以上条款**
