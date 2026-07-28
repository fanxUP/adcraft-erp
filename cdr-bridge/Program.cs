using AdCraft.CdrBridge;

Console.WriteLine(@"");
Console.WriteLine(@"  ╔═══════════════════════════════════════╗");
Console.WriteLine(@"  ║    AdCraft CDR Bridge v1.0.0        ║");
Console.WriteLine(@"  ║    CDR 智能报价本地桥接服务          ║");
Console.WriteLine(@"  ╚═══════════════════════════════════════╝");
Console.WriteLine(@"");

var config = BridgeConfig.Load();
var service = new CdrBridgeService(config);

Console.CancelKeyPress += (sender, args) =>
{
    args.Cancel = true;
    Console.WriteLine("正在停止服务...");
    service.Stop();
    Environment.Exit(0);
};

try
{
    await service.StartAsync();
}
catch (Exception ex)
{
    Console.Error.WriteLine($"启动失败: {ex.Message}");
    Console.Error.WriteLine(ex.StackTrace);
    Environment.Exit(1);
}
