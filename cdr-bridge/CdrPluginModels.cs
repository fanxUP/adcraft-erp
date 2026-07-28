using System.Text.Json.Serialization;

namespace AdCraft.CdrBridge.Models;

public class CaptureSubmission
{
    [JsonPropertyName("device_code")]
    public string DeviceCode { get; set; } = "";

    [JsonPropertyName("document")]
    public DocumentInfo? Document { get; set; }

    [JsonPropertyName("selection")]
    public SelectionInfo? Selection { get; set; }

    [JsonPropertyName("drawing_fingerprint")]
    public string DrawingFingerprint { get; set; } = "";

    [JsonPropertyName("warnings")]
    public List<PreflightWarning> Warnings { get; set; } = new();

    [JsonPropertyName("timestamp")]
    public long Timestamp { get; set; }

    [JsonPropertyName("nonce")]
    public string Nonce { get; set; } = "";

    [JsonPropertyName("signature")]
    public string Signature { get; set; } = "";

    [JsonPropertyName("idempotency_key")]
    public string IdempotencyKey { get; set; } = "";
}

public class DocumentInfo
{
    [JsonPropertyName("document_name")]
    public string DocumentName { get; set; } = "";

    [JsonPropertyName("page_count")]
    public int PageCount { get; set; }

    [JsonPropertyName("active_page_index")]
    public int ActivePageIndex { get; set; }

    [JsonPropertyName("active_page_name")]
    public string ActivePageName { get; set; } = "";
}

public class SelectionInfo
{
    [JsonPropertyName("selection_count")]
    public int SelectionCount { get; set; }

    [JsonPropertyName("bounding_box")]
    public BoundingBoxInfo? BoundingBox { get; set; }

    [JsonPropertyName("total_curve_length_mm")]
    public double TotalCurveLengthMm { get; set; }

    [JsonPropertyName("closed_curve_area_mm2")]
    public double ClosedCurveAreaMm2 { get; set; }

    [JsonPropertyName("text_object_count")]
    public int TextObjectCount { get; set; }

    [JsonPropertyName("bitmap_object_count")]
    public int BitmapObjectCount { get; set; }

    [JsonPropertyName("group_count")]
    public int GroupCount { get; set; }
}

public class BoundingBoxInfo
{
    [JsonPropertyName("width_mm")]
    public double WidthMm { get; set; }

    [JsonPropertyName("height_mm")]
    public double HeightMm { get; set; }

    [JsonPropertyName("left_mm")]
    public double LeftMm { get; set; }

    [JsonPropertyName("bottom_mm")]
    public double BottomMm { get; set; }
}

public class PreflightWarning
{
    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("code")]
    public string Code { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

public class ErpAuthResponse
{
    [JsonPropertyName("access_token")]
    public string AccessToken { get; set; } = "";

    [JsonPropertyName("token_type")]
    public string TokenType { get; set; } = "bearer";
}

public class ErpCaptureResponse
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("session_code")]
    public string SessionCode { get; set; } = "";

    [JsonPropertyName("document_name")]
    public string DocumentName { get; set; } = "";

    [JsonPropertyName("drawing_fingerprint")]
    public string DrawingFingerprint { get; set; } = "";
}

public class OfflineQueueItem
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public int RetryCount { get; set; }
    public string Payload { get; set; } = "";
    public string Status { get; set; } = "pending"; // pending | submitting | completed | failed
    public string? ErrorMessage { get; set; }
}
