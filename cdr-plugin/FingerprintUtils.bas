Attribute VB_Name = "FingerprintUtils"

Function GenerateFingerprint(docInfo As String, selInfo As String) As String
    ' Simplified fingerprint: combine document + selection key properties
    ' In MVP, use string hash; in production, use SHA256 via .NET bridge
    Dim raw As String
    raw = docInfo & "|" & selInfo
    GenerateFingerprint = "FP_" & CStr(HashString(raw))
End Function

Private Function HashString(text As String) As Long
    ' Simple hash for MVP — production should use SHA256 via local bridge
    Dim i As Long
    Dim hash As Long
    hash = 5381
    For i = 1 To Len(text)
        hash = ((hash * 33) + AscW(Mid(text, i, 1))) And &H7FFFFFFF
    Next
    HashString = hash
End Function
