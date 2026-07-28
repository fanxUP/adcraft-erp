namespace AdCraft.CdrBridge;

public class BridgeConfig
{
    public int ListenPort { get; set; } = 9527;
    public string ListenAddress { get; set; } = "127.0.0.1";
    public string ErpBaseUrl { get; set; } = "http://192.168.0.102:8000/api/v1";
    public string DeviceCode { get; set; } = "CDR-DESKTOP-001";
    public string DeviceName { get; set; } = "设计部-主设计机";
    public string LocalSecretKey { get; set; } = "";
    public string LogLevel { get; set; } = "Information";
    public string OfflineQueuePath { get; set; } = @"C:\ProgramData\AdCraft\CdrBridge\offline";
    public int MaxRetryCount { get; set; } = 3;
    public int HealthCheckIntervalSeconds { get; set; } = 60;

    public static BridgeConfig Load()
    {
        var config = new BridgeConfig();
        var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "appsettings.json");
        if (File.Exists(configPath))
        {
            var json = File.ReadAllText(configPath);
            var section = System.Text.Json.JsonSerializer.Deserialize<System.Text.Json.JsonElement>(json);
            if (section.TryGetProperty("Bridge", out var bridge))
            {
                if (bridge.TryGetProperty("ListenPort", out var port)) config.ListenPort = port.GetInt32();
                if (bridge.TryGetProperty("ListenAddress", out var addr)) config.ListenAddress = addr.GetString()!;
                if (bridge.TryGetProperty("ErpBaseUrl", out var erp)) config.ErpBaseUrl = erp.GetString()!;
                if (bridge.TryGetProperty("DeviceCode", out var dc)) config.DeviceCode = dc.GetString()!;
                if (bridge.TryGetProperty("DeviceName", out var dn)) config.DeviceName = dn.GetString()!;
                if (bridge.TryGetProperty("LocalSecretKey", out var key)) config.LocalSecretKey = key.GetString()!;
                if (bridge.TryGetProperty("OfflineQueuePath", out var path)) config.OfflineQueuePath = path.GetString()!;
            }
        }

        // Auto-generate secret key if not set
        if (string.IsNullOrEmpty(config.LocalSecretKey))
        {
            config.LocalSecretKey = Guid.NewGuid().ToString("N")[..32];
        }

        return config;
    }
}
