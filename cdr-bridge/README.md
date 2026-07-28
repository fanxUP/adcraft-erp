# AdCraft CDR Bridge — 本地桥接服务

## 简介
Windows 本地桥接服务，负责：
- 接收 CDR 插件发送的图稿数据
- 校验数据格式和签名
- 转发到 ERP 报价系统
- ERP 离线时暂存数据到本地队列
- 恢复连接后自动提交

## 系统要求
- Windows 10/11 或 Windows Server 2019+
- .NET 8 Runtime
- 内网可访问 ERP 服务器 (192.168.0.102:8000)

## 安装

### 1. 安装 .NET 8 Runtime
从 https://dotnet.microsoft.com/download/dotnet/8.0 下载安装

### 2. 部署桥接程序
将编译后的 `AdCraftCdrBridge` 文件夹复制到 `C:\Program Files\AdCraft\CdrBridge\`

### 3. 配置文件
编辑 `appsettings.json`:
```json
{
  "Bridge": {
    "ListenPort": 9527,
    "ListenAddress": "127.0.0.1",
    "ErpBaseUrl": "http://192.168.0.102:8000/api/v1",
    "DeviceCode": "CDR-DESKTOP-001",
    "DeviceName": "设计部-主设计机",
    "OfflineQueuePath": "C:\\ProgramData\\AdCraft\\CdrBridge\\offline"
  }
}
```

### 4. 配置凭据
创建 `C:\Program Files\AdCraft\CdrBridge\.credentials` 文件：
```
your_erp_username
your_erp_password
```

### 5. 注册为 Windows 服务（推荐）
```cmd
sc create AdCraftCdrBridge binPath="C:\Program Files\AdCraft\CdrBridge\AdCraftCdrBridge.exe"
sc start AdCraftCdrBridge
```

### 6. 或直接运行
```cmd
cd C:\Program Files\AdCraft\CdrBridge\
AdCraftCdrBridge.exe
```

## 本地 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /local/v1/status | GET | 桥接服务状态 |
| /local/v1/captures/validate | POST | 校验插件数据格式 |
| /local/v1/captures/submit | POST | 提交图稿数据到 ERP |

## 日志
日志文件位于: `C:\ProgramData\AdCraft\CdrBridge\logs\`
