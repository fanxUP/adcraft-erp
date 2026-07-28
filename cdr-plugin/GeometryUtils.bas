Attribute VB_Name = "GeometryUtils"

Function GetSelectionInfo(sel As ShapeRange) As String
    Dim json As String
    Dim count As Long
    Dim bbox As Object
    Dim totalCurveLength As Double
    Dim totalArea As Double
    Dim textCount As Long, bitmapCount As Long, groupCount As Long
    Dim i As Long
    Dim sh As Shape
    
    count = sel.Count
    If count = 0 Then
        GetSelectionInfo = "{}"
        Exit Function
    End If
    
    Set bbox = sel.BoundingBox
    totalCurveLength = 0
    totalArea = 0
    textCount = 0
    bitmapCount = 0
    groupCount = 0
    
    For i = 1 To count
        Set sh = sel(i)
        If sh.Type = cdrTextShape Then textCount = textCount + 1
        If sh.Type = cdrBitmapShape Then bitmapCount = bitmapCount + 1
        If sh.Type = cdrGroupShape Then groupCount = groupCount + 1
        If sh.IsCurve Then
            totalCurveLength = totalCurveLength + sh.Curve.Length
            If sh.Curve.Closed Then
                totalArea = totalArea + sh.Curve.Area
            End If
        End If
    Next
    
    json = "{"
    json = json & """selection_count"":" & count & ","
    json = json & """bounding_box"":{"
    json = json & """width_mm"":""" & FormatNumber(ConvertToMM(bbox.Width), 3) & ""","
    json = json & """height_mm"":""" & FormatNumber(ConvertToMM(bbox.Height), 3) & ""","
    json = json & """left_mm"":""" & FormatNumber(ConvertToMM(bbox.Left), 3) & ""","
    json = json & """bottom_mm"":""" & FormatNumber(ConvertToMM(bbox.Bottom), 3)
    json = json & "},"
    json = json & """total_curve_length_mm"":""" & FormatNumber(totalCurveLength, 3) & ""","
    json = json & """closed_curve_area_mm2"":""" & FormatNumber(totalArea, 3) & ""","
    json = json & """text_object_count"":" & textCount & ","
    json = json & """bitmap_object_count"":" & bitmapCount & ","
    json = json & """group_count"":" & groupCount
    json = json & "}"
    
    GetSelectionInfo = json
End Function

Function ConvertToMM(value As Double) As Double
    Dim doc As Document
    Set doc = ActiveDocument
    Select Case doc.DocumentUnits
        Case cdrInch: ConvertToMM = value * 25.4
        Case cdrCm: ConvertToMM = value * 10
        Case cdrMeter: ConvertToMM = value * 1000
        Case Else: ConvertToMM = value
    End Select
End Function

Function GetDocumentInfo() As String
    Dim doc As Document
    Dim json As String
    Set doc = ActiveDocument
    
    If doc Is Nothing Then
        GetDocumentInfo = "{}"
        Exit Function
    End If
    
    json = "{"
    json = json & """document_name"":""" & EscapeJSON(doc.FullName) & ""","
    json = json & """page_count"":" & doc.Pages.Count & ","
    json = json & """active_page_index"":" & doc.ActivePage.Index & ","
    json = json & """active_page_name"":""" & EscapeJSON(doc.ActivePage.Name) & """"
    json = json & "}"
    GetDocumentInfo = json
End Function

Function EscapeJSON(text As String) As String
    Dim result As String
    result = Replace(text, "\", "\\")
    result = Replace(result, """", "\""")
    result = Replace(result, vbCrLf, "\n")
    result = Replace(result, vbCr, "\n")
    result = Replace(result, vbLf, "\n")
    EscapeJSON = result
End Function
