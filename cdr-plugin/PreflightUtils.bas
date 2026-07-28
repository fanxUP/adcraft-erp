Attribute VB_Name = "PreflightUtils"

Function RunPreflightCheck(sel As ShapeRange, selJson As String) As String
    Dim warnings As String
    Dim count As Long
    Dim i As Long
    Dim sh As Shape
    Dim first As Boolean
    
    warnings = "["
    first = True
    count = sel.Count
    
    ' Check 1: No selection
    If count = 0 Then
        warnings = warnings & AddWarning(True, first, "ERROR", "未选择任何对象", "请先选择要报价的图形对象")
        first = False
    Else
        ' Check 2: Zero-size objects
        For i = 1 To count
            Set sh = sel(i)
            If sh.SizeWidth = 0 Or sh.SizeHeight = 0 Then
                If Not first Then warnings = warnings & ","
                warnings = warnings & AddWarning(False, False, "ERROR", "对象尺寸为0", "第" & i & "个对象宽度或高度为0，请检查")
                first = False
                Exit For
            End If
        Next
        
        ' Check 3: Text not converted to curves
        For i = 1 To count
            Set sh = sel(i)
            If sh.Type = cdrTextShape Then
                If Not first Then warnings = warnings & ","
                warnings = warnings & AddWarning(False, False, "WARN", "文本未转曲", "存在文本对象，建议转曲后再报价")
                first = False
                Exit For
            End If
        Next
        
        ' Check 4: Open curves with area pricing
        For i = 1 To count
            Set sh = sel(i)
            If sh.IsCurve Then
                If Not sh.Curve.Closed Then
                    If Not first Then warnings = warnings & ","
                    warnings = warnings & AddWarning(False, False, "WARN", "存在开放曲线", "选中对象包含未闭合曲线，请注意面积计算方式")
                    first = False
                    Exit For
                End If
            End If
        Next
        
        ' Check 5: Hidden objects
        For i = 1 To count
            Set sh = sel(i)
            If Not sh.IsOnLayer Then
                If Not first Then warnings = warnings & ","
                warnings = warnings & AddWarning(False, False, "INFO", "存在隐藏对象", "选中对象包含隐藏图层上的对象")
                first = False
                Exit For
            End If
        Next
    End If
    
    warnings = warnings & "]"
    RunPreflightCheck = warnings
End Function

Private Function AddWarning(isBlocking As Boolean, isFirst As Boolean, level As String, code As String, msg As String) As String
    Dim w As String
    w = "{"
    w = w & """severity"":""" & level & ""","
    w = w & """code"":""" & code & ""","
    w = w & """message"":""" & Replace(msg, """", "\""") & """"
    w = w & "}"
    AddWarning = w
End Function
