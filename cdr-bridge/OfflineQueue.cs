using System.Text.Json;
using AdCraft.CdrBridge.Models;

namespace AdCraft.CdrBridge;

public class OfflineQueue
{
    private readonly string _queuePath;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public OfflineQueue(BridgeConfig config)
    {
        _queuePath = config.OfflineQueuePath;
        Directory.CreateDirectory(_queuePath);
    }

    public async Task EnqueueAsync(string payload)
    {
        await _lock.WaitAsync();
        try
        {
            var item = new OfflineQueueItem
            {
                Id = Guid.NewGuid().ToString(),
                CreatedAt = DateTime.UtcNow,
                Payload = payload,
                Status = "pending"
            };

            var filePath = Path.Combine(_queuePath, $"{item.Id}.json");
            var json = JsonSerializer.Serialize(item, new JsonSerializerOptions { WriteIndented = true });
            await File.WriteAllTextAsync(filePath, json);
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task<List<OfflineQueueItem>> GetPendingItemsAsync()
    {
        await _lock.WaitAsync();
        try
        {
            var items = new List<OfflineQueueItem>();
            if (!Directory.Exists(_queuePath))
                return items;

            foreach (var file in Directory.GetFiles(_queuePath, "*.json"))
            {
                try
                {
                    var json = await File.ReadAllTextAsync(file);
                    var item = JsonSerializer.Deserialize<OfflineQueueItem>(json);
                    if (item != null && item.Status == "pending")
                        items.Add(item);
                }
                catch { /* skip corrupt files */ }
            }

            return items.OrderBy(i => i.CreatedAt).ToList();
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task UpdateStatusAsync(string itemId, string status, string? errorMessage = null)
    {
        await _lock.WaitAsync();
        try
        {
            var filePath = Path.Combine(_queuePath, $"{itemId}.json");
            if (!File.Exists(filePath)) return;

            var json = await File.ReadAllTextAsync(filePath);
            var item = JsonSerializer.Deserialize<OfflineQueueItem>(json);
            if (item == null) return;

            item.Status = status;
            item.ErrorMessage = errorMessage;
            item.RetryCount++;

            json = JsonSerializer.Serialize(item, new JsonSerializerOptions { WriteIndented = true });
            await File.WriteAllTextAsync(filePath, json);
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task<int> GetPendingCountAsync()
    {
        var items = await GetPendingItemsAsync();
        return items.Count;
    }
}
