using System.Security.Cryptography;
using System.Text;

namespace AdCraft.CdrBridge;

public class SecurityHelper
{
    private readonly BridgeConfig _config;

    public SecurityHelper(BridgeConfig config)
    {
        _config = config;
    }

    /// <summary>
    /// Generate HMAC-SHA256 signature for request validation.
    /// </summary>
    public string Sign(string message)
    {
        var keyBytes = Encoding.UTF8.GetBytes(_config.LocalSecretKey);
        var msgBytes = Encoding.UTF8.GetBytes(message);

        using var hmac = new HMACSHA256(keyBytes);
        var hash = hmac.ComputeHash(msgBytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    /// <summary>
    /// Verify HMAC-SHA256 signature.
    /// </summary>
    public bool Verify(string message, string signature)
    {
        var expected = Sign(message);
        return string.Equals(expected, signature, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Generate a unique nonce for each request.
    /// </summary>
    public static string GenerateNonce()
    {
        return Guid.NewGuid().ToString("N")[..16];
    }

    /// <summary>
    /// Current Unix timestamp in seconds.
    /// </summary>
    public static long GetCurrentTimestamp()
    {
        return DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    }

    /// <summary>
    /// Validate timestamp is within tolerance window (5 minutes).
    /// </summary>
    public static bool IsTimestampValid(long timestamp, int toleranceSeconds = 300)
    {
        var now = GetCurrentTimestamp();
        return Math.Abs(now - timestamp) <= toleranceSeconds;
    }

    /// <summary>
    /// Generate idempotency key for a submission.
    /// Combines device code, fingerprint, and timestamp to create a deterministic key.
    /// </summary>
    public static string GenerateIdempotencyKey(string deviceCode, string fingerprint)
    {
        var raw = $"{deviceCode}|{fingerprint}|{DateTime.UtcNow:yyyyMMddHH}";
        using var sha256 = SHA256.Create();
        var hash = sha256.ComputeHash(Encoding.UTF8.GetBytes(raw));
        return "IDEM-" + Convert.ToHexString(hash)[..24];
    }

    /// <summary>
    /// Mask sensitive data for logging (token, passwords).
    /// </summary>
    public static string MaskSensitive(string? value)
    {
        if (string.IsNullOrEmpty(value) || value.Length < 8)
            return "***";
        return value[..4] + "****" + value[^4..];
    }
}
