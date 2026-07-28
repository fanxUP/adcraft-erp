Attribute VB_Name = "ApiClient"

Private Function CreateHttpRequest() As Object
    ' Use WinHttpRequest which is more reliable on Windows
    On Error Resume Next
    Set CreateHttpRequest = CreateObject("WinHttp.WinHttpRequest.5.1")
    If CreateHttpRequest Is Nothing Then
        Set CreateHttpRequest = CreateObject("MSXML2.XMLHTTP")
    End If
    On Error GoTo 0
End Function

Function LoginAndGetToken(username As String, password As String) As String
    Dim http As Object
    Dim url As String
    Dim body As String
    Dim resp As String
    
    Set http = CreateHttpRequest
    If http Is Nothing Then
        LoginAndGetToken = ""
        Exit Function
    End If
    
    url = Config.ERP_BASE_URL & "/auth/login"
    body = "{""username"":""" & username & """,""password"":""" & password & """}"
    
    http.Open "POST", url, False
    http.SetRequestHeader "Content-Type", "application/json"
    http.SetTimeouts 5000, 5000, 5000, Config.API_TIMEOUT_SECONDS * 1000
    http.Send body
    
    If http.Status = 200 Then
        resp = http.ResponseText
        ' Simple JSON parse for MVP — extract access_token
        LoginAndGetToken = ExtractJSONValue(resp, "access_token")
    Else
        LoginAndGetToken = ""
    End If
End Function

Function SubmitCapture(token As String, docJson As String, selJson As String, fingerprint As String, preflightJson As String) As String
    Dim http As Object
    Dim url As String
    Dim body As String
    
    Set http = CreateHttpRequest
    If http Is Nothing Then
        SubmitCapture = ""
        Exit Function
    End If
    
    url = Config.ERP_BASE_URL & "/cdr/captures"
    
    ' Build the JSON payload
    body = "{"
    body = body & """device_code"":""" & Config.DEVICE_CODE & ""","
    body = body & """document"":" & docJson & ","
    body = body & """selection"":" & selJson & ","
    body = body & """drawing_fingerprint"":""" & fingerprint & ""","
    body = body & """warnings"":" & preflightJson
    body = body & "}"
    
    http.Open "POST", url, False
    http.SetRequestHeader "Content-Type", "application/json"
    http.SetRequestHeader "Authorization", "Bearer " & token
    http.SetTimeouts 5000, 5000, 5000, Config.API_TIMEOUT_SECONDS * 1000
    http.Send body
    
    If http.Status = 200 Or http.Status = 201 Then
        SubmitCapture = http.ResponseText
    Else
        SubmitCapture = "{""error"":""" & http.Status & ":" & http.StatusText & """}"
    End If
End Function

Function ExtractJSONValue(jsonText As String, key As String) As String
    ' Simple JSON value extractor for MVP (no external dependencies)
    ' Finds "key":"value" or "key":value patterns
    Dim searchKey As String
    Dim startPos As Long
    Dim endPos As Long
    Dim charAfter As String
    
    searchKey = """" & key & """:"
    startPos = InStr(jsonText, searchKey)
    
    If startPos = 0 Then
        ExtractJSONValue = ""
        Exit Function
    End If
    
    startPos = startPos + Len(searchKey)
    
    ' Skip whitespace
    Do While Mid(jsonText, startPos, 1) = " " Or Mid(jsonText, startPos, 1) = vbTab
        startPos = startPos + 1
    Loop
    
    charAfter = Mid(jsonText, startPos, 1)
    
    If charAfter = """" Then
        ' String value
        startPos = startPos + 1
        endPos = startPos
        Do While Mid(jsonText, endPos, 1) <> """" Or Mid(jsonText, endPos - 1, 1) = "\"
            endPos = endPos + 1
        Loop
        ExtractJSONValue = Mid(jsonText, startPos, endPos - startPos)
    ElseIf charAfter = "{" Or charAfter = "[" Then
        ' Object or array — find matching close
        Dim depth As Long
        depth = 1
        endPos = startPos + 1
        Do While depth > 0 And endPos <= Len(jsonText)
            Dim c As String
            c = Mid(jsonText, endPos, 1)
            If c = "{" Or c = "[" Then depth = depth + 1
            If c = "}" Or c = "]" Then depth = depth - 1
            endPos = endPos + 1
        Loop
        ExtractJSONValue = Mid(jsonText, startPos, endPos - startPos - 1)
    Else
        ' Number or boolean
        endPos = startPos
        Do While endPos <= Len(jsonText) And InStr("0123456789.-Ee", Mid(jsonText, endPos, 1)) > 0
            endPos = endPos + 1
        Loop
        ExtractJSONValue = Trim(Mid(jsonText, startPos, endPos - startPos))
    End If
End Function
