# KiwiOT 优智云家智能门锁组件

这是一个用于 Home Assistant 的 KiwiOT 智能门锁自定义组件。支持智能门锁事件监控、状态显示和用户管理等功能。

为了方便bug反馈，建议使用issue功能进行反馈。或者加qq群(964512589)进行交流。

### v1.1.9 版本更新日志
修复websoket连接失败的问题

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
2. 在HACS中点击"自定义存储库"
3. 添加此仓库地址：`https://github.com/XG520/kiwiot_ws`
4. 类别选择"集成"
5. 点击"添加"
6. 在HACS的集成页面中搜索"KiwiOT"
7. 点击"下载"进行安装
8. 重启Home Assistant

### 方式二：手动安装
1. 下载此仓库的最新版本
2. 将 `custom_components/kiwiot_ws` 文件夹复制到你的Home Assistant配置目录下的 `custom_components` 文件夹中
3. 重启Home Assistant

## 配置说明

通过 Home Assistant 的集成页面添加，需要提供以下信息：
- 手机号（+86开头）
- 密码
- Client ID (抓包获取)
- 是否忽略SSL证书验证（可选）


## 支持的实体类型

- 门锁状态 (sensor.xxx_status)
- 门锁事件 (sensor.xxx_event)
- 用户信息 (sensor.xxx_user_x)
- 图片预览 (camera.xxx_camera)

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
 2. 本插件不保证准确性、可靠性、完整性和及时性
 3. 任何个人或组织均可无需经过通知而自由使用
 4. 作者对任何插件问题概不负责，包括由此产生的任何损失
 6. 请勿将本插件用于商业用途，由此引起的问题与作者无关
 7. 本插件及其更新版权归作者所有
   - **使用本插件默认同意以上条款**
