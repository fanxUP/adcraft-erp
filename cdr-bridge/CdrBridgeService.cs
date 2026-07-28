using System.Net;
using System.Text;
using System.Text.Json;
using AdCraft.CdrBridge.Models;

namespace AdCraft.CdrBridge;

public class CdrBridgeService : IDisposable
{
    private readonly BridgeConfig _config;
    private readonly SecurityHelper _security;
    private readonly OfflineQueue _queue;
    private readonly HttpClient _httpClient;
    private readonly HttpListener _listener;
    private CancellationTokenSource? _cts;
    private bool _running;
    private string? _accessToken;
    private DateTime _tokenExpiry = DateTime.MinValue;
    private readonly ILogger? _logger;

    // Simple console logger for MVP
    public interface ILogger
    {
        void Info(string msg);
        void Warn(string msg);
        void Error(string msg, Exception? ex = null);
    }

    private class ConsoleLogger : ILogger
    {
        public void Info(string msg) => Console.WriteLine($"[INFO] {DateTime.Now:HH:mm:ss} {msg}");
        public void Warn(string msg) => Console.WriteLine($"[WARN] {DateTime.Now:HH:mm:ss} {msg}");
        public void Error(string msg, Exception? ex = null)
        {
            Console.Error.WriteLine($"[ERROR] {DateTime.Now:HH:mm:ss} {msg}");
            if (ex != null) Console.Error.WriteLine($"  {ex.Message}");
        }
    }

    public CdrBridgeService(BridgeConfig config)
    {
        _config = config;
        _security = new SecurityHelper(config);
        _queue = new OfflineQueue(config);
        _logger = new ConsoleLogger();

        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(_config.ErpBaseUrl),
            Timeout = TimeSpan.FromSeconds(30)
        };

        _listener = new HttpListener();
        _listener.Prefixes.Add($"http://{_config.ListenAddress}:{_config.ListenPort}/");
    }

    public async Task StartAsync()
    {
        _cts = new CancellationTokenSource();
        _listener.Start();
        _running = true;

        _logger!.Info($"桥接服务启动于 http://{_config.ListenAddress}:{_config.ListenPort}");
        _logger!.Info($"ERP 地址: {_config.ErpBaseUrl}");
        _logger!.Info($"设备编码: {_config.DeviceCode}");

        _ = HealthCheckLoopAsync(_cts.Token);
        _ = ProcessOfflineQueueLoopAsync(_cts.Token);

        await Task.Run(() => ListenLoopAsync(_cts.Token));
    }

    public void Stop()
    {
        _running = false;
        _cts?.Cancel();
        _listener.Stop();
        _logger?.Info("桥接服务已停止");
    }

    private async Task ListenLoopAsync(CancellationToken ct)
    {
        while (_running && !ct.IsCancellationRequested)
        {
            try
            {
                var context = await _listener.GetContextAsync();
                _ = HandleRequestAsync(context);
            }
            catch (ObjectDisposedException) { break; }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                _logger?.Error("监听异常", ex);
            }
        }
    }

    private async Task HandleRequestAsync(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        try
        {
            switch (request.Url?.AbsolutePath)
            {
                case "/local/v1/status":
                    await HandleStatusRequest(response);
                    break;

                case "/local/v1/captures/validate":
                    await HandleValidateRequest(request, response);
                    break;

                case "/local/v1/captures/submit":
                    await HandleSubmitRequest(request, response);
                    break;

                default:
                    await WriteJsonResponse(response, 404, new { error = "endpoint_not_found", message = "接口不存在" });
                    break;
            }
        }
        catch (Exception ex)
        {
            _logger?.Error("请求处理异常", ex);
            await WriteJsonResponse(response, 500, new { error = "internal_error", message = "桥接服务内部错误" });
        }
    }

    private async Task HandleStatusRequest(HttpListenerResponse response)
    {
        var pendingCount = await _queue.GetPendingCountAsync();
        var erpOnline = await CheckErpConnectionAsync();

        await WriteJsonResponse(response, 200, new
        {
            version = "1.0.0",
            device_code = _config.DeviceCode,
            device_name = _config.DeviceName,
            erp_connected = erpOnline,
            erp_url = _config.ErpBaseUrl,
            logged_in = !string.IsNullOrEmpty(_accessToken),
            authenticated = !string.IsNullOrEmpty(_accessToken),
            pending_submissions = pendingCount,
            uptime = (DateTime.UtcNow - _startTime).TotalSeconds
        });
    }

    private readonly DateTime _startTime = DateTime.UtcNow;

    private async Task HandleValidateRequest(HttpListenerRequest request, HttpListenerResponse response)
    {
        var body = await ReadBodyAsync(request);
        if (string.IsNullOrEmpty(body))
        {
            await WriteJsonResponse(response, 400, new { error = "empty_body", message = "请求体为空" });
            return;
        }

        // Validate JSON format
        try
        {
            var submission = JsonSerializer.Deserialize<CaptureSubmission>(body);
            if (submission == null)
            {
                await WriteJsonResponse(response, 400, new { error = "invalid_json", message = "JSON 解析失败" });
                return;
            }

            var errors = new List<string>();
            if (string.IsNullOrEmpty(submission.DeviceCode))
                errors.Add("device_code 不能为空");
            if (submission.Selection == null)
                errors.Add("selection 不能为空");

            await WriteJsonResponse(response, errors.Count > 0 ? 400 : 200, new
            {
                valid = errors.Count == 0,
                errors,
                warnings = new[] { "验证通过，数据格式正确" }
            });
        }
        catch (JsonException ex)
        {
            await WriteJsonResponse(response, 400, new { error = "invalid_json", message = $"JSON 格式错误: {ex.Message}" });
        }
    }

    private async Task HandleSubmitRequest(HttpListenerRequest request, HttpListenerResponse response)
    {
        var body = await ReadBodyAsync(request);
        if (string.IsNullOrEmpty(body))
        {
            await WriteJsonResponse(response, 400, new { error = "empty_body", message = "请求体为空" });
            return;
        }

        try
        {
            var submission = JsonSerializer.Deserialize<CaptureSubmission>(body);
            if (submission == null)
            {
                await WriteJsonResponse(response, 400, new { error = "invalid_json", message = "JSON 解析失败" });
                return;
            }

            // Verify signature if provided
            if (!string.IsNullOrEmpty(submission.Signature))
            {
                var messageToVerify = $"{submission.DeviceCode}|{submission.Timestamp}|{submission.Nonce}|{body}";
                if (!_security.Verify(messageToVerify, submission.Signature))
                {
                    await WriteJsonResponse(response, 401, new { error = "invalid_signature", message = "签名验证失败" });
                    return;
                }
            }

            // Generate idempotency key if not provided
            if (string.IsNullOrEmpty(submission.IdempotencyKey))
            {
                submission.IdempotencyKey = SecurityHelper.GenerateIdempotencyKey(
                    submission.DeviceCode, submission.DrawingFingerprint);
            }

            // Try to submit to ERP
            var erpResult = await SubmitToErpAsync(submission);

            if (erpResult.Success)
            {
                await WriteJsonResponse(response, 200, new
                {
                    success = true,
                    capture_id = erpResult.CaptureId,
                    session_code = erpResult.SessionCode,
                    message = "图稿数据已提交到 ERP"
                });
            }
            else
            {
                // Save to offline queue
                await _queue.EnqueueAsync(body);
                _logger?.Warn($"ERP 不可达，已保存到离线队列。错误: {erpResult.Error}");

                await WriteJsonResponse(response, 202, new
                {
                    success = false,
                    queued = true,
                    message = "ERP 暂时不可达，数据已保存到本地队列，恢复连接后将自动提交",
                    pending_count = await _queue.GetPendingCountAsync()
                });
            }
        }
        catch (JsonException ex)
        {
            await WriteJsonResponse(response, 400, new { error = "invalid_json", message = $"JSON 格式错误: {ex.Message}" });
        }
    }

    private async Task<(bool Success, string? CaptureId, string? SessionCode, string? Error)> SubmitToErpAsync(CaptureSubmission submission)
    {
        try
        {
            // Ensure token is valid
            if (!await EnsureTokenAsync())
            {
                return (false, null, null, "ERP 登录失败");
            }

            // Submit capture to ERP
            var payload = JsonSerializer.Serialize(new
            {
                device_code = submission.DeviceCode,
                document = submission.Document,
                selection = submission.Selection,
                drawing_fingerprint = submission.DrawingFingerprint,
                warnings = submission.Warnings,
                idempotency_key = submission.IdempotencyKey
            });

            var httpContent = new StringContent(payload, Encoding.UTF8, "application/json");
            var httpRequest = new HttpRequestMessage(HttpMethod.Post, "/api/v1/cdr/captures")
            {
                Content = httpContent
            };
            httpRequest.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _accessToken);

            var httpResponse = await _httpClient.SendAsync(httpRequest);

            if (httpResponse.IsSuccessStatusCode)
            {
                var responseBody = await httpResponse.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<JsonElement>(responseBody);

                var data = result.TryGetProperty("data", out var d) ? d : result;
                var captureId = data.TryGetProperty("id", out var id) ? id.GetString() : "";
                var sessionCode = data.TryGetProperty("session_code", out var sc) ? sc.GetString() : "";

                return (true, captureId, sessionCode, null);
            }

            var errorBody = await httpResponse.Content.ReadAsStringAsync();
            return (false, null, null, $"ERP 返回 {(int)httpResponse.StatusCode}: {errorBody}");
        }
        catch (HttpRequestException ex)
        {
            return (false, null, null, $"网络错误: {ex.Message}");
        }
        catch (TaskCanceledException)
        {
            return (false, null, null, "请求超时");
        }
    }

    private async Task<bool> EnsureTokenAsync()
    {
        if (!string.IsNullOrEmpty(_accessToken) && DateTime.UtcNow < _tokenExpiry)
            return true;

        try
        {
            // Try to read credentials from stored config
            var credPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".credentials");
            string? username = null, password = null;

            if (File.Exists(credPath))
            {
                var lines = await File.ReadAllLinesAsync(credPath);
                if (lines.Length >= 2)
                {
                    username = lines[0].Trim();
                    password = lines[1].Trim();
                }
            }

            // For MVP: prompt for credentials via console or use stored ones
            // In production: store encrypted tokens instead of passwords
            if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
            {
                _logger?.Warn("未配置 ERP 凭据，请在首次使用时通过插件登录");
                return false;
            }

            var loginPayload = JsonSerializer.Serialize(new { username, password });
            var loginContent = new StringContent(loginPayload, Encoding.UTF8, "application/json");
            var loginResponse = await _httpClient.PostAsync("/api/v1/auth/login", loginContent);

            if (loginResponse.IsSuccessStatusCode)
            {
                var body = await loginResponse.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<ErpAuthResponse>(body);
                if (result != null && !string.IsNullOrEmpty(result.AccessToken))
                {
                    _accessToken = result.AccessToken;
                    _tokenExpiry = DateTime.UtcNow.AddHours(23);
                    return true;
                }
            }

            _logger?.Error($"ERP 登录失败: {loginResponse.StatusCode}");
            return false;
        }
        catch (Exception ex)
        {
            _logger?.Error("ERP 登录异常", ex);
            return false;
        }
    }

    private async Task<bool> CheckErpConnectionAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/api/v1/cdr/quotes?page=1&page_size=1");
            return response.IsSuccessStatusCode || response.StatusCode == HttpStatusCode.Unauthorized;
        }
        catch
        {
            return false;
        }
    }

    private async Task ProcessOfflineQueueLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(TimeSpan.FromSeconds(30), ct);
                await ProcessOfflineQueueAsync();
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                _logger?.Error("离线队列处理异常", ex);
            }
        }
    }

    private async Task ProcessOfflineQueueAsync()
    {
        var pendingItems = await _queue.GetPendingItemsAsync();
        if (pendingItems.Count == 0) return;

        _logger?.Info($"处理离线队列: {pendingItems.Count} 个待提交项");

        foreach (var item in pendingItems)
        {
            try
            {
                await _queue.UpdateStatusAsync(item.Id, "submitting");

                var submission = JsonSerializer.Deserialize<CaptureSubmission>(item.Payload);
                if (submission == null)
                {
                    await _queue.UpdateStatusAsync(item.Id, "failed", "无效的数据格式");
                    continue;
                }

                var result = await SubmitToErpAsync(submission);
                if (result.Success)
                {
                    await _queue.UpdateStatusAsync(item.Id, "completed");
                    _logger?.Info($"离线提交成功: {result.CaptureId}");
                }
                else if (item.RetryCount >= _config.MaxRetryCount)
                {
                    await _queue.UpdateStatusAsync(item.Id, "failed", $"重试 {_config.MaxRetryCount} 次后失败: {result.Error}");
                    _logger?.Warn($"离线提交失败(已达最大重试): {result.Error}");
                }
                else
                {
                    await _queue.UpdateStatusAsync(item.Id, "pending", result.Error);
                }
            }
            catch (Exception ex)
            {
                await _queue.UpdateStatusAsync(item.Id, "pending", ex.Message);
            }
        }
    }

    private async Task HealthCheckLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(TimeSpan.FromSeconds(_config.HealthCheckIntervalSeconds), ct);
                var online = await CheckErpConnectionAsync();
                _logger?.Info($"ERP 健康检查: {(online ? "在线 ✅" : "离线 ❌")}");
            }
            catch (OperationCanceledException) { break; }
            catch { /* ignore health check errors */ }
        }
    }

    private static async Task<string> ReadBodyAsync(HttpListenerRequest request)
    {
        using var reader = new StreamReader(request.InputStream, request.ContentEncoding);
        return await reader.ReadToEndAsync();
    }

    private static async Task WriteJsonResponse(HttpListenerResponse response, int statusCode, object data)
    {
        response.StatusCode = statusCode;
        response.ContentType = "application/json; charset=utf-8";
        var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            WriteIndented = false
        });
        var buffer = Encoding.UTF8.GetBytes(json);
        response.ContentLength64 = buffer.Length;
        await response.OutputStream.WriteAsync(buffer);
        response.OutputStream.Close();
    }

    public void Dispose()
    {
        _httpClient.Dispose();
        _cts?.Cancel();
        _cts?.Dispose();
        ((IDisposable)_listener).Dispose();
    }
}
