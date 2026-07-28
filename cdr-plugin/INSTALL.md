# CDR 智能报价插件 - 安装和使用指南

## 适用环境
- Windows 10/11 + CorelDRAW 2019~2024 (64位)
- 内网可访问 ERP 服务器 (192.168.0.102:8000)

## 插件文件清单
```
cdr-plugin/
├── Config.bas              # 配置（ERP地址、设备编号等）
├── GeometryUtils.bas       # 几何数据读取（尺寸、面积、长度）
├── FingerprintUtils.bas    # 图稿指纹生成
├── PreflightUtils.bas      # 预检警告（空选区、未转曲等）
├── ApiClient.bas           # ERP API 通信（登录、提交采集）
├── SmartQuote.bas          # 主入口（读取选区→预检→提交→创建草稿）
└── INSTALL.md              # 本文件
```

## 安装步骤

### 1. 注册设备
在 ERP 后台管理 > 设备管理中，添加设计电脑的设备编码。

### 2. 导入宏
1. 打开 CorelDRAW
2. 菜单：工具 > 宏 > 宏管理器 (Alt+F11)
3. 在宏管理器中，右键 "Global Macros" > "导入宏文件"
4. 依次导入 6 个 .bas 文件
5. 保存工作区

### 3. 配置
编辑 Config.bas 中的：
- `ERP_BASE_URL` — ERP 服务器地址
- `DEVICE_CODE` — 设备编号（需与第 1 步注册的一致）

### 4. 运行
- 在 CorelDRAW 中选择图形
- 工具 > 宏 > 运行宏 > `SmartQuote.SmartQuoteSelection`
- 首次运行输入 ERP 用户名和密码
- 插件自动读取并提交图稿数据

### 5. 在 ERP 中完成报价
- 浏览器打开 ERP 报价工作台
- 在"智能报价"中找到新创建的报价草稿
- 完善客户、产品、材料和工艺信息
- 确认并提交审批

## 宏功能说明

### SmartQuoteSelection（主功能）
1. 读取文档信息（名称、页面）
2. 读取选中对象（数量、包围盒尺寸、面积、曲线长度）
3. 自动换算单位（英寸→毫米）
4. 运行预检（检查空选区、零尺寸、未转曲文本等）
5. 生成图稿指纹
6. 登录 ERP（首次或令牌过期时）
7. 提交图稿数据到 ERP
8. 在浏览器中打开报价草稿

### ShowSelectionInfo（诊断）
弹出对话框显示当前选区的详细信息。

### CheckERPAvailability（诊断）
测试 ERP 服务器连接状态。

## 注意事项
- 插件只读读取数据，不会修改用户图稿
- 首次提交需要输入 ERP 账号密码
- 售价等敏感计算在 ERP 服务端完成
- 如 ERP 不可用，请稍后重试
