Attribute VB_Name = "SmartQuote"
'===========================================================
' AdCraft CDR 智能报价插件 - 主模块 (MVP)
' 使用 VBA GMS，只读读取选区图形数据，提交到 ERP 报价
'===========================================================

Public g_CurrentToken As String
Public g_LoggedIn As Boolean

' ── 初始化/反初始化 ──────────────────────────────────────────

Public Sub InitializePlugin()
    ' Called on document open or plugin load
    ' Currently no-op for MVP; future: add menu/toolbar
    g_LoggedIn = False
    g_CurrentToken = ""
End Sub

' ── 主入口：读取选区并报价 ──────────────────────────────────

Public Sub SmartQuoteSelection()
    Dim doc As Document
    Dim sel As ShapeRange
    Dim docInfo As String
    Dim selInfo As String
    Dim fingerprint As String
    Dim preflightJson As String
    
    Set doc = ActiveDocument
    If doc Is Nothing Then
        MsgBox "请先打开一个 CDR 文档", vbExclamation, DOCKER_TITLE
        Exit Sub
    End If
    
    On Error GoTo ErrorHandler
    
    ' Step 1: Read document info
    docInfo = GeometryUtils.GetDocumentInfo()
    
    ' Step 2: Read selection
    Set sel = doc.SelectionRange
    If sel Is Nothing Or sel.Count = 0 Then
        MsgBox "请先选择要报价的图形对象", vbExclamation, DOCKER_TITLE
        Exit Sub
    End If
    
    selInfo = GeometryUtils.GetSelectionInfo(sel)
    
    ' Step 3: Run preflight checks
    preflightJson = PreflightUtils.RunPreflightCheck(sel, selInfo)
    
    ' Check for blocking warnings
    If InStr(preflightJson, """ERROR""") > 0 Then
        Dim resp As VbMsgBoxResult
        resp = MsgBox("检测到阻断性警告，是否仍要继续？" & vbCrLf & preflightJson, vbYesNo + vbExclamation, DOCKER_TITLE)
        If resp = vbNo Then Exit Sub
    End If
    
    ' Step 4: Generate fingerprint
    fingerprint = FingerprintUtils.GenerateFingerprint(docInfo, selInfo)
    
    ' Step 5: Ensure logged in
    If Not g_LoggedIn Then
        If Not LoginToERP() Then Exit Sub
    End If
    
    ' Step 6: Submit to ERP
    Dim result As String
    result = ApiClient.SubmitCapture(g_CurrentToken, docInfo, selInfo, fingerprint, preflightJson)
    
    If result = "" Then
        MsgBox "提交失败：无法连接到 ERP 服务器" & vbCrLf & _
               "请检查网络连接和服务器状态", vbCritical, DOCKER_TITLE
        Exit Sub
    End If
    
    If InStr(result, """error""") > 0 Then
        MsgBox "提交失败：" & result, vbCritical, DOCKER_TITLE
        Exit Sub
    End If
    
    ' Step 7: Extract capture ID and open ERP quote page
    Dim captureId As String
    captureId = ApiClient.ExtractJSONValue(result, "id")
    
    MsgBox "图稿数据已成功发送到 ERP！" & vbCrLf & vbCrLf & _
           "请在 ERP 报价工作台中继续完成报价。" & vbCrLf & _
           "采集编号: " & captureId, vbInformation, DOCKER_TITLE
    
    Exit Sub
    
ErrorHandler:
    MsgBox "发生错误: " & Err.Description & vbCrLf & _
           "错误代码: " & Err.Number, vbCritical, DOCKER_TITLE
End Sub

' ── 登录 ─────────────────────────────────────────────────────

Private Function LoginToERP() As Boolean
    Dim username As String
    Dim password As String
    
    username = InputBox("请输入 ERP 用户名:", DOCKER_TITLE)
    If username = "" Then
        LoginToERP = False
        Exit Function
    End If
    
    password = InputBox("请输入密码:", DOCKER_TITLE)
    If password = "" Then
        LoginToERP = False
        Exit Function
    End If
    
    g_CurrentToken = ApiClient.LoginAndGetToken(username, password)
    
    If g_CurrentToken = "" Then
        MsgBox "登录失败，请检查用户名和密码", vbCritical, DOCKER_TITLE
        LoginToERP = False
        Exit Function
    End If
    
    g_LoggedIn = True
    LoginToERP = True
End Function

' ── 辅助功能 ────────────────────────────────────────────────

Public Sub ShowSelectionInfo()
    ' 诊断功能：查看当前选中对象的信息
    Dim doc As Document
    Dim sel As ShapeRange
    Dim msg As String
    
    Set doc = ActiveDocument
    If doc Is Nothing Then
        MsgBox "未打开文档", vbInformation, DOCKER_TITLE
        Exit Sub
    End If
    
    Set sel = doc.SelectionRange
    If sel Is Nothing Or sel.Count = 0 Then
        msg = "文档: " & doc.Name & vbCrLf
        msg = msg & "页面: " & doc.ActivePage.Name & vbCrLf
        msg = msg & "未选中任何对象"
    Else
        msg = "文档: " & doc.Name & vbCrLf
        msg = msg & "页面: " & doc.ActivePage.Name & vbCrLf
        msg = msg & "选中对象: " & sel.Count & " 个" & vbCrLf
        msg = msg & "宽度: " & GeometryUtils.ConvertToMM(sel.BoundingBox.Width) & " mm" & vbCrLf
        msg = msg & "高度: " & GeometryUtils.ConvertToMM(sel.BoundingBox.Height) & " mm" & vbCrLf
    End If
    
    MsgBox msg, vbInformation, DOCKER_TITLE
End Sub

Public Sub CheckERPAvailability()
    ' 诊断功能：检查 ERP 连接状态
    Dim http As Object
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    If http Is Nothing Then
        Set http = CreateObject("MSXML2.XMLHTTP")
    End If
    
    If http Is Nothing Then
        MsgBox "无法创建 HTTP 请求对象", vbCritical, DOCKER_TITLE
        Exit Sub
    End If
    
    On Error GoTo ConnError
    http.Open "GET", Config.ERP_BASE_URL & "/cdr/quotes?page=1&page_size=1", False
    http.SetTimeouts 3000, 3000, 3000, 5000
    http.Send
    
    If http.Status = 200 Then
        MsgBox "ERP 连接正常 ✅" & vbCrLf & vbCrLf & _
               "服务器: " & Config.ERP_BASE_URL, vbInformation, DOCKER_TITLE
    Else
        MsgBox "ERP 返回状态码: " & http.Status & vbCrLf & _
               "服务器: " & Config.ERP_BASE_URL, vbExclamation, DOCKER_TITLE
    End If
    Exit Sub
    
ConnError:
    MsgBox "无法连接到 ERP 服务器" & vbCrLf & _
           "地址: " & Config.ERP_BASE_URL & vbCrLf & _
           "错误: " & Err.Description, vbCritical, DOCKER_TITLE
End Sub
