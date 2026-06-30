#!/usr/bin/env python3
"""Generate AdCraft ERP User Manual PDF using reportlab with PingFang SC font."""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Register Chinese font
# ---------------------------------------------------------------------------
# Try multiple font sources in order of preference
CN_FONT = None
CANDIDATES = [
    # macOS system fonts (TrueType-based, reportlab-compatible)
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/62032b9b64a0e3a9121c50aeb2ed794e3e2c201f.asset/AssetData/Hei.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    # Windows
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
]

for path in CANDIDATES:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont("CJK", path))
            CN_FONT = "CJK"
            break
        except Exception:
            continue

if CN_FONT is None:
    # Last resort: CID font (built-in, always available but limited)
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    CN_FONT = "STSong-Light"

FONT_SIZE = 10
FONT_SIZE_H1 = 20
FONT_SIZE_H2 = 15
FONT_SIZE_H3 = 12
FONT_SIZE_SMALL = 8

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
PRIMARY = colors.HexColor("#1a56db")
DARK = colors.HexColor("#1e293b")
GRAY = colors.HexColor("#64748b")
LIGHT_GRAY = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#e2e8f0")
WHITE = colors.white

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
styles = getSampleStyleSheet()


def make_style(name, **kw):
    kw.setdefault("fontName", CN_FONT)
    kw.setdefault("fontSize", FONT_SIZE)
    kw.setdefault("leading", FONT_SIZE * 1.6)
    kw.setdefault("textColor", DARK)
    return ParagraphStyle(name, **kw)


style_body = make_style("CNBody", fontSize=FONT_SIZE, leading=FONT_SIZE * 1.7, alignment=TA_JUSTIFY)
style_h1 = make_style("CNH1", fontSize=FONT_SIZE_H1, leading=FONT_SIZE_H1 * 1.4, textColor=PRIMARY, spaceAfter=6 * mm, spaceBefore=12 * mm)
style_h2 = make_style("CNH2", fontSize=FONT_SIZE_H2, leading=FONT_SIZE_H2 * 1.4, textColor=PRIMARY, spaceAfter=4 * mm, spaceBefore=8 * mm)
style_h3 = make_style("CNH3", fontSize=FONT_SIZE_H3, leading=FONT_SIZE_H3 * 1.5, textColor=DARK, spaceAfter=2 * mm, spaceBefore=5 * mm)
style_code = make_style("CNCode", fontSize=8.5, leading=12, fontName="Courier", textColor=colors.HexColor("#334155"), backColor=LIGHT_GRAY, borderPadding=6)
style_note = make_style("CNNote", fontSize=FONT_SIZE_SMALL, leading=FONT_SIZE_SMALL * 1.5, textColor=GRAY, alignment=TA_JUSTIFY)
style_title = make_style("CNTitle", fontSize=24, leading=30, textColor=WHITE, alignment=TA_CENTER)
style_cover_sub = make_style("CNCoverSub", fontSize=13, leading=18, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER)
style_toc = make_style("CNTOC", fontSize=11, leading=22, textColor=DARK)
style_table_header = make_style("CNTH", fontSize=FONT_SIZE_SMALL, leading=13, textColor=WHITE, fontName=CN_FONT)
style_table_cell = make_style("CNTC", fontSize=FONT_SIZE_SMALL, leading=14, textColor=DARK, fontName=CN_FONT)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def h1(text):
    return Paragraph(text, style_h1)

def h2(text):
    return Paragraph(text, style_h2)

def h3(text):
    return Paragraph(text, style_h3)

def body(text):
    return Paragraph(text, style_body)

def note(text):
    return Paragraph(text, style_note)

def code(text):
    return Paragraph(text, style_code)

def spacer(h=3 * mm):
    return Spacer(1, h)

def bullet(items):
    from reportlab.platypus import ListFlowable, ListItem
    li_style = make_style("CNBullet", fontSize=FONT_SIZE, leading=FONT_SIZE * 1.7, leftIndent=12)
    return ListFlowable(
        [ListItem(Paragraph(i, li_style), bulletColor=PRIMARY) for i in items],
        bulletType="bullet",
        start="●",
        bulletFontName=CN_FONT,
        bulletFontSize=8,
        leftIndent=12 * mm,
        bulletOffsetY=-2,
    )


def _table(v_headers, rows, col_widths=None):
    """Create a styled table with header row + data rows."""
    header_cells = [Paragraph(h, style_table_header) for h in v_headers]
    data = [header_cells]
    for row in rows:
        data.append([Paragraph(str(c), style_table_cell) for c in row])

    w = col_widths or [None] * len(v_headers)
    t = Table(data, colWidths=w, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# ---------------------------------------------------------------------------
# Page templates
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4  # 210 x 297 mm


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(CN_FONT, 7)
    canvas.setFillColor(GRAY)
    # Header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, PAGE_H - 15 * mm, PAGE_W - 20 * mm, PAGE_H - 15 * mm)
    canvas.drawString(20 * mm, PAGE_H - 14 * mm, "AdCraft ERP — 广告制作安装工程管理系统")
    canvas.drawRightString(PAGE_W - 20 * mm, PAGE_H - 14 * mm, "使用说明书")
    # Footer
    canvas.line(20 * mm, 18 * mm, PAGE_W - 20 * mm, 18 * mm)
    canvas.drawCentredString(PAGE_W / 2, 10 * mm, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


def _cover_bg(canvas, doc):
    """Dark-blue background for the cover page."""
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0f172a"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Decorative accent bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, PAGE_H * 0.55, PAGE_W, 4 * mm, fill=1, stroke=0)
    canvas.restoreState()


frame_main = Frame(20 * mm, 20 * mm, PAGE_W - 40 * mm, PAGE_H - 40 * mm, id="main")
frame_cover = Frame(25 * mm, PAGE_H * 0.18, PAGE_W - 50 * mm, PAGE_H * 0.45, id="cover")

cover_template = PageTemplate(id="Cover", frames=[frame_cover], onPage=_cover_bg)
content_template = PageTemplate(id="Content", frames=[frame_main], onPage=_header_footer)

# ---------------------------------------------------------------------------
# Story content
# ---------------------------------------------------------------------------
story = []

# =========================== Cover Page ============================
story.append(NextPageTemplate("Cover"))
story.append(spacer(10 * mm))
story.append(Paragraph("<b>AdCraft ERP</b>", style_title))
story.append(spacer(3 * mm))
story.append(Paragraph("广告制作安装工程管理系统 · 用户使用说明书", style_cover_sub))
story.append(spacer(8 * mm))
story.append(Paragraph(f"版本 1.0  |  {datetime.now().strftime('%Y年%m月')}", make_style("CVer", fontSize=10, textColor=colors.HexColor("#64748b"), alignment=TA_CENTER)))
story.append(PageBreak())

# =========================== TOC placeholder ============================
story.append(NextPageTemplate("Content"))
story.append(h1("目  录"))
story.append(spacer(4 * mm))

toc_items = [
    ("1", "系统概述", "项目背景、技术架构、核心特性"),
    ("2", "部署与安装", "环境要求、Docker 部署、手动部署、初始化配置"),
    ("3", "登录与快速入门", "登录系统、默认账户、角色切换、页面导航"),
    ("4", "首页驾驶舱", "实时看板、关键指标、快捷入口"),
    ("5", "客户管理", "客户列表、Excel 批量导入、客户详情"),
    ("6", "产品 / 材质 / 工艺管理", "产品分类、产品库、材质库、工艺库、Excel 导入"),
    ("7", "报价管理", "创建报价、添加明细、自动计算、确认报价、转订单"),
    ("8", "订单管理", "订单列表、状态流转、成本核算"),
    ("9", "任务管理", "设计任务、制作任务（含看板）、安装任务、附件管理"),
    ("10", "外协管理", "外协商、外协任务、外协付款"),
    ("11", "库存管理", "库存项目、出入库记录、安全库存"),
    ("12", "财务管理", "收款记录、支出管理、客户欠款、对账单"),
    ("13", "报表中心", "销售日报、销售月报"),
    ("14", "系统管理", "操作日志、数据备份与恢复"),
    ("15", "AI 智能助手", "AI 报价、异常检测、知识库、经营报告、现场照片、收款 OCR"),
    ("16", "角色与权限", "七种角色、权限矩阵、功能可见性"),
    ("17", "典型业务流程", "从询价到回款的完整流程"),
    ("18", "常见问题（FAQ）", "登录、部署、数据、备份等常见问题"),
]

for num, title, desc in toc_items:
    story.append(Paragraph(f"<b>{num}.  {title}</b>  ………………  {desc}", style_toc))
    story.append(spacer(1 * mm))

story.append(PageBreak())

# =========================== Chapter 1: 系统概述 ============================
story.append(h1("1. 系统概述"))
story.append(h3("1.1 项目背景"))
story.append(body("AdCraft ERP 是一款专为广告制作、安装工程行业设计的企业资源管理（ERP）系统。"
    "系统覆盖从客户询价、报价、下单，到设计、制作、安装，再到收款、对账、利润核算的全业务流程，"
    "帮助广告工程公司实现标准化、数字化的项目管理与财务管控。"))
story.append(h3("1.2 技术架构"))
story.append(body("系统采用前后端分离的 B/S 架构，通过浏览器即可访问，支持局域网内部署。"
    "核心组件如下："))
story.append(_table(
    ["层级", "技术栈", "说明"],
    [
        ["前端", "Vue 3 + Vite + TypeScript + Element Plus", "响应式 SPA 单页应用，支持桌面与移动端"],
        ["后端", "FastAPI (Python) + SQLAlchemy Async", "RESTful API，异步高性能，自动生成 OpenAPI 文档"],
        ["数据库", "PostgreSQL 16", "关系型数据库，支持 JSONB、全文检索"],
        ["缓存", "Redis 7", "会话缓存（预留扩展）"],
        ["对象存储", "MinIO（可选）/ 本地文件系统", "文件上传存储，Docker 部署时使用 MinIO"],
        ["反向代理", "Nginx", "统一入口，静态资源服务，负载均衡"],
        ["备份", "Alpine Cron (每日 2:00 AM)", "自动备份数据库与上传文件"],
    ],
    col_widths=[3.5 * cm, 6.5 * cm, 6.5 * cm],
))
story.append(spacer(3 * mm))
story.append(h3("1.3 核心特性"))
story.append(bullet([
    "全流程覆盖：客户 → 报价 → 订单 → 设计/制作/安装 → 收款 → 对账，一站式管理",
    "智能辅助：内置 AI 报价助手、异常检测、经营报告、现场照片识别、收款截图 OCR",
    "角色权限：admin / sales / designer / production / installer / finance / warehouse 七种角色",
    "Excel 导入：支持客户、产品、材质等批量导入",
    "操作审计：全链路操作日志记录，数据变更可追溯",
    "Docker 一键部署：包含 Nginx + 后端 + 前端 + PostgreSQL + Redis + MinIO + 自动备份",
    "LAN 局域网部署：支持企业内网使用，无需公网暴露",
]))

story.append(PageBreak())

# =========================== Chapter 2: 部署与安装 ============================
story.append(h1("2. 部署与安装"))
story.append(h3("2.1 环境要求"))
story.append(_table(
    ["项目", "最低要求", "推荐配置"],
    [
        ["操作系统", "Linux / macOS / Windows (WSL2)", "Ubuntu 22.04 LTS"],
        ["CPU", "2 核", "4 核"],
        ["内存", "4 GB", "8 GB"],
        ["磁盘", "20 GB", "50 GB SSD"],
        ["Docker", "Docker 24.x + Docker Compose v2", "Docker 27.x"],
        ["浏览器", "Chrome 90+ / Edge 90+ / Safari 15+", "最新版 Chrome"],
    ],
    col_widths=[3 * cm, 5.5 * cm, 8 * cm],
))
story.append(spacer(3 * mm))
story.append(h3("2.2 Docker 一键部署（推荐）"))
story.append(body("第一步：克隆或解压项目到服务器"))
story.append(code("git clone <repository-url> adcraft-erp\ncd adcraft-erp"))
story.append(spacer(2 * mm))
story.append(body("第二步：配置环境变量"))
story.append(code("cp .env.example .env\n# 编辑 .env，修改 SECRET_KEY 和数据库密码\n# SECRET_KEY 生成命令：openssl rand -hex 32"))
story.append(spacer(2 * mm))
story.append(body("第三步：启动所有服务"))
story.append(code("docker compose up -d"))
story.append(spacer(2 * mm))
story.append(body("第四步：验证运行状态"))
story.append(code("docker compose ps\n# 所有服务状态应为 Up/healthy"))
story.append(spacer(2 * mm))
story.append(body("启动后可通过以下地址访问："))
story.append(_table(
    ["服务", "地址", "说明"],
    [
        ["Web 系统", "http://localhost", "主界面（Nginx 80 端口代理）"],
        ["API 文档", "http://localhost:8000/api/docs", "Swagger UI，可在线调试 API"],
        ["MinIO 管理", "http://localhost:9001", "对象存储管理控制台"],
    ],
    col_widths=[3.5 * cm, 6 * cm, 7 * cm],
))
story.append(spacer(3 * mm))
story.append(h3("2.3 手动部署（开发环境）"))
story.append(body("后端启动："))
story.append(code("cd backend\npython -m venv venv && source venv/bin/activate\npip install -e \".[dev]\"\nalembic upgrade head\nuvicorn app.main:app --reload --port 8000"))
story.append(spacer(2 * mm))
story.append(body("前端启动："))
story.append(code("cd frontend\nnpm install\nnpm run dev\n# 开发服务器默认 http://localhost:5173"))
story.append(spacer(2 * mm))
story.append(body("注意：手动部署需要自行安装并启动 PostgreSQL 和 Redis，并在 .env 中配置正确的连接地址。"))
story.append(h3("2.4 Docker 服务说明"))
story.append(_table(
    ["服务名", "镜像", "端口映射", "用途"],
    [
        ["nginx", "nginx:1.27-alpine", "80:80", "反向代理 + 前端静态资源"],
        ["frontend", "Custom Dockerfile", "—", "Vue SPA 构建产物"],
        ["backend", "Custom Dockerfile", "—", "FastAPI 后端应用"],
        ["postgres", "postgres:16-alpine", "5432:5432", "主数据库"],
        ["redis", "redis:7-alpine", "6379:6379", "缓存服务"],
        ["minio", "minio/minio:latest", "9000, 9001", "对象存储"],
        ["backup", "alpine:3.21", "—", "每日自动备份（2:00 AM）"],
    ],
    col_widths=[3 * cm, 3.5 * cm, 2.5 * cm, 7.5 * cm],
))
story.append(spacer(2 * mm))
story.append(note("提示：backup 服务每天凌晨 2 点自动执行备份任务，备份文件存放在 ./backups 目录。"
    "备份内容包括 PostgreSQL 数据库导出文件和 uploads 目录的打包压缩。"))

story.append(PageBreak())

# =========================== Chapter 3: 登录与快速入门 ============================
story.append(h1("3. 登录与快速入门"))
story.append(h3("3.1 访问系统"))
story.append(body("在浏览器地址栏输入系统地址（如 http://localhost），将自动跳转到登录页面。"))
story.append(h3("3.2 默认账户"))
story.append(_table(
    ["角色", "用户名", "密码", "说明"],
    [
        ["管理员", "admin", "admin123", "拥有全部权限，首次登录后请立即修改密码"],
    ],
    col_widths=[4 * cm, 4 * cm, 4 * cm, 4.5 * cm],
))
story.append(spacer(2 * mm))
story.append(body("首次登录后，管理员应尽快在系统内创建其他用户并分配角色。创建用户的路径：使用管理员账户登录后，通过 API 或数据库创建。"))
story.append(h3("3.3 页面布局"))
story.append(body("登录后进入主界面，布局分为三个区域："))
story.append(bullet([
    "左侧边栏：功能导航菜单，根据角色权限自动显示/隐藏菜单项",
    "顶部栏：显示当前模块路径和用户信息",
    "中央区域：各功能模块的具体操作页面",
]))
story.append(h3("3.4 修改密码"))
story.append(body("系统支持在线修改密码功能，用户可在登录后通过密码修改入口更新自己的登录密码。"))

story.append(PageBreak())

# =========================== Chapter 4: 首页驾驶舱 ============================
story.append(h1("4. 首页驾驶舱"))
story.append(body("首页驾驶舱（Dashboard）提供企业经营数据的实时概览，帮助管理者快速掌握业务动态。"))
story.append(h3("4.1 关键指标"))
story.append(bullet([
    "今日/本月订单数量和金额汇总",
    "待处理报价、待确认订单数量",
    "进行中的设计/制作/安装任务统计",
    "应收款项和已收款项对比",
    "客户欠款 Top N 排行榜",
]))
story.append(h3("4.2 可视化图表"))
story.append(body("驾驶舱集成了 ECharts 图表组件，展示销售额趋势、任务完成率、部门工作量等关键数据图表。"))

story.append(PageBreak())

# =========================== Chapter 5: 客户管理 ============================
story.append(h1("5. 客户管理"))
story.append(body("客户管理模块用于维护企业客户信息，包括客户基本信息、联系人、客户类型等。"))
story.append(h3("5.1 客户列表"))
story.append(body("客户列表页面支持以下操作："))
story.append(bullet([
    "分页浏览所有客户，支持关键词搜索（客户名称/电话/联系人）",
    "按客户类型（公司/个人/代理等）筛选",
    "新建客户：填写基本信息后保存",
    "编辑客户：点击客户行或详情页修改信息",
    "删除客户：管理员权限可删除（软删除，数据可恢复）",
    "批量导入：上传 Excel 文件批量创建客户",
]))
story.append(h3("5.2 Excel 批量导入"))
story.append(body("点击「批量导入」按钮，下载模板或直接上传 Excel 文件（.xlsx 或 .xls）。"
    "系统将自动解析每行数据并导入，失败的记录会返回具体错误原因。支持的列包括："
    "客户名称、客户类型、联系人、电话、地址、备注等。"))
story.append(h3("5.3 客户详情"))
story.append(body("点击客户进入详情页，可查看客户基本信息、关联的报价记录、订单记录、收款记录、联系人列表等。"))

story.append(PageBreak())

# =========================== Chapter 6: 产品/材质/工艺管理 ============================
story.append(h1("6. 产品 / 材质 / 工艺管理"))
story.append(body("产品管理是报价和订单的基础数据模块，包含产品分类、产品库、材质库和工艺库四个子模块。"))
story.append(h3("6.1 产品分类"))
story.append(body("产品分类用于对产品进行分组管理，例如：喷绘类、灯箱类、字牌类、展示器材类等。支持创建和删除分类。"))
story.append(h3("6.2 产品库"))
story.append(body("产品是报价的最小单位，每个产品包含以下属性："))
story.append(_table(
    ["字段", "说明", "示例"],
    [
        ["产品名称", "必填", "户外灯箱布"],
        ["所属分类", "选填，关联产品分类", "喷绘类"],
        ["单位", "计量单位", "㎡ / 个 / 套 / m"],
        ["计价方式", "area=按面积, quantity=按数量, length=按长度, word_count=按字数", "area"],
        ["默认价格", "默认单价（元）", "80.00"],
        ["最低收费", "最低起做价格（元）", "200.00"],
        ["备注", "附加说明", "含安装"],
    ],
    col_widths=[3 * cm, 5 * cm, 8.5 * cm],
))
story.append(spacer(2 * mm))
story.append(body("产品同样支持 Excel 批量导入功能。"))
story.append(h3("6.3 材质库"))
story.append(body("材质是产品制作所需的基础材料，用于生产管理和成本核算。核心字段包括："))
story.append(bullet([
    "材质名称（必填）、规格、单位",
    "采购价（进货成本）、销售价（报价参考）",
    "损耗率（百分比，生产损耗预估）",
    "安全库存（低于此数量时将触发库存预警）",
]))
story.append(h3("6.4 工艺库"))
story.append(body("工艺定义了制作过程中的工序标准，如：UV 打印、覆膜、裁切、打扣、焊接等。"
    "每个工艺可设置名称、描述、默认工时和默认工价。"))

story.append(PageBreak())

# =========================== Chapter 7: 报价管理 ============================
story.append(h1("7. 报价管理"))
story.append(body("报价管理是业务的核心环节，管理从询价到报价确认的全过程。"))
story.append(h3("7.1 创建报价"))
story.append(body("步骤："))
story.append(bullet([
    "点击「新建报价」，填写项目名称、选择客户、指定销售人员",
    "添加报价明细——选择产品或手动输入项目名称、规格尺寸、数量、单价",
    "系统根据计价方式（面积/数量/长度/字数）自动计算面积",
    "对每项明细可单独设置工艺费、安装费、设计费、运输费、其他费",
    "保存后进入「草稿」状态",
]))
story.append(h3("7.2 报价计算"))
story.append(body("点击「计算」按钮，系统将自动："))
story.append(bullet([
    "根据每项明细的数量和单价计算分项金额",
    "汇总所有分项金额得到报价总额",
    "应用折扣率和税率",
    "更新报价单的总金额",
]))
story.append(h3("7.3 确认报价"))
story.append(body("确认后报价从「草稿」变更为「已确认」状态。已确认的报价不可直接修改明细（如有需要请复制为新报价），"
    "但可以执行「转订单」操作。"))
story.append(h3("7.4 转订单"))
story.append(body("已确认的报价可直接转换为订单。系统将自动复制报价内容到订单，并生成订单编号。"
    "转换后报价状态更新为「已转订单」。"))

story.append(PageBreak())

# =========================== Chapter 8: 订单管理 ============================
story.append(h1("8. 订单管理"))
story.append(body("订单管理跟踪从合同签订到项目交付的全过程。"))
story.append(h3("8.1 订单列表"))
story.append(body("支持按状态（进行中/已完成/已取消）、客户、关键词等条件筛选。每条订单显示：订单编号、"
    "客户名称、项目名称、订单金额、成本金额、利润、当前状态。"))
story.append(h3("8.2 订单状态"))
story.append(_table(
    ["状态", "说明", "可执行操作"],
    [
        ["进行中", "订单正常执行中", "修改、拆分任务、变更状态"],
        ["已完成", "项目已交付验收", "查看归档（不可修改）"],
        ["已取消", "订单已取消", "查看归档"],
    ],
    col_widths=[3.5 * cm, 6.5 * cm, 6.5 * cm],
))
story.append(spacer(2 * mm))
story.append(h3("8.3 成本核算"))
story.append(body("订单支持两种成本设置方式："))
story.append(bullet([
    "手动设置：直接输入订单的总成本金额",
    "自动核算：系统根据关联的制作任务和外协任务汇总成本",
]))
story.append(body("利润 = 订单金额 - 成本金额，在订单列表和报表中均可查看。"))

story.append(PageBreak())

# =========================== Chapter 9: 任务管理 ============================
story.append(h1("9. 任务管理"))
story.append(body("任务管理将订单分解为设计、制作、安装三个环节的具体任务，实现精细化的项目管控。"))
story.append(h3("9.1 设计任务"))
story.append(body("设计任务用于管理广告物料的平面设计工作："))
story.append(bullet([
    "创建任务：关联订单，指派设计师，设定截止日期",
    "状态流转：待分配 → 设计中 → 待审核 → 审核通过 / 需修改",
    "附件上传：支持上传设计稿（图片、AI/CDR 源文件），客户确认记录",
    "任务详情：查看完整的设计进度和沟通记录",
]))
story.append(h3("9.2 制作任务"))
story.append(body("制作任务管理广告物料的工厂制作环节："))
story.append(bullet([
    "创建任务：关联订单或设计任务，指定制作人员",
    "制作看板（看板视图）：以看板形式展示各状态的制作任务，支持拖拽更新状态",
    "状态流转：待排产 → 制作中 → 质检 → 质检通过 / 需返工 → 已完成",
    "工艺关联：可关联具体的制作工艺标准",
]))
story.append(h3("9.3 安装任务"))
story.append(body("安装任务管理广告物料的现场安装工作："))
story.append(bullet([
    "创建任务：关联订单或制作任务，指定安装团队",
    "状态流转：待安排 → 安装中 → 已完成 → 已验收",
    "移动端支持：安装人员手机浏览器访问 /mobile/installation 查看任务和提交完工照片",
    "完工资料：上传安装现场照片，记录完工时间",
]))
story.append(h3("9.4 附件管理"))
story.append(body("所有任务均支持上传附件（图纸、照片、签名等），附件通过统一的上传接口管理，"
    "可根据关联类型和关联 ID 进行绑定和查询。"))

story.append(PageBreak())

# =========================== Chapter 10: 外协管理 ============================
story.append(h1("10. 外协管理"))
story.append(body("外协管理用于管理外包/外协供应商的任务派发和付款跟踪。"))
story.append(h3("10.1 外协商管理"))
story.append(body("维护外协供应商信息：公司名称、联系人、电话、地址、擅长工艺、合作状态等。"))
story.append(bullet([
    "新建/编辑/删除外协商（删除需管理员权限）",
    "支持分页浏览和关键词搜索",
]))
story.append(h3("10.2 外协任务"))
story.append(body("将制作任务的部分或全部工序外包给供应商："))
story.append(bullet([
    "创建外协任务：选择外协商、关联订单、填写任务描述、外包金额、截止日期",
    "状态管理：已派发 → 制作中 → 已交付 → 已验收",
    "实时查看外协任务的进度和交付状态",
]))
story.append(h3("10.3 外协付款"))
story.append(body("记录对外协商的付款明细：付款日期、金额、付款方式、关联任务、备注。支持分页浏览和新建。"))

story.append(PageBreak())

# =========================== Chapter 11: 库存管理 ============================
story.append(h1("11. 库存管理"))
story.append(body("库存管理模块用于跟踪广告制作材料的库存情况。"))
story.append(h3("11.1 库存项目"))
story.append(body("每个库存项目关联一种材质，记录当前库存数量和预警阈值："))
story.append(bullet([
    "支持新建、编辑库存项目",
    "显示当前库存数量和状态（正常 / 不足 / 缺货）",
    "低于安全库存时自动标记为预警状态",
]))
story.append(h3("11.2 出入库记录"))
story.append(body("所有库存变动均通过出入库单据记录："))
story.append(bullet([
    "入库操作（stock-in）：采购到货、退货入库、盘点盈余",
    "出库操作（stock-out）：生产领料、报废损耗、盘点亏损",
    "每条记录包含：操作时间、数量、操作人、关联任务/订单、备注",
    "库存记录页面支持按时间范围筛选查看全部出入库历史",
]))

story.append(PageBreak())

# =========================== Chapter 12: 财务管理 ============================
story.append(h1("12. 财务管理"))
story.append(body("财务管理模块覆盖收款、支出、欠款跟踪和对账四个核心财务环节。"))
story.append(h3("12.1 收款记录"))
story.append(body("记录客户回款情况："))
story.append(bullet([
    "新建收款：关联客户和订单，登记收款金额、收款方式、收款日期",
    "上传收款凭证：支持上传银行转账截图或扫码支付截图",
    "作废收款：对错误录入的收款记录可执行作废操作（非删除，保留审计痕迹）",
    "筛选：按客户、订单、是否已作废等条件筛选",
]))
story.append(h3("12.2 支出管理"))
story.append(body("记录企业的各类运营支出："))
story.append(bullet([
    "新建支出：登记金额、支出类别（材料采购/外协加工/运输物流/办公费用/其他）、日期、备注",
    "编辑/删除：可修改或删除支出记录（删除需管理员权限）",
    "筛选：按类别、日期范围筛选",
]))
story.append(h3("12.3 客户欠款"))
story.append(body("客户欠款页面展示每个客户的应收/已收/欠款余额汇总，帮助财务人员跟踪回款进度。"))
story.append(h3("12.4 对账单"))
story.append(body("对账单功能用于与客户进行定期对账："))
story.append(bullet([
    "新建对账单：选择客户和时间范围，系统自动汇总期间的收款和订单金额",
    "确认对账单：双方确认后标记为已确认状态",
    "查看对账单详情：展示明细分项和汇总金额",
]))

story.append(PageBreak())

# =========================== Chapter 13: 报表中心 ============================
story.append(h1("13. 报表中心"))
story.append(body("报表中心提供企业经营数据的多维度统计分析。"))
story.append(h3("13.1 销售日报"))
story.append(body("按日期查看每日的销售数据：订单数量、订单金额、收款金额、成本金额、利润等。"
    "支持日期范围筛选，以表格和图表形式展示。"))
story.append(h3("13.2 销售月报"))
story.append(body("按月汇总销售数据，提供月度销售趋势对比。包含月度订单总额、回款率、利润率等关键指标。"))

story.append(PageBreak())

# =========================== Chapter 14: 系统管理 ============================
story.append(h1("14. 系统管理"))
story.append(body("系统管理模块提供操作审计和数据安全保障功能，仅限管理员角色访问。"))
story.append(h3("14.1 操作日志"))
story.append(body("系统自动记录所有用户的关键操作，包括："))
story.append(bullet([
    "操作人、操作时间、IP 地址",
    "操作对象类型（客户/报价/订单/任务/收款 等）",
    "操作动作（创建/更新/删除/确认/转换状态 等）",
    "操作前后数据变更对比",
    "支持按用户、对象类型、操作动作、日期范围筛选查询",
]))
story.append(h3("14.2 数据备份与恢复"))
story.append(body("备份管理页面提供手动备份和恢复功能："))
story.append(bullet([
    "创建备份：手动触发完整备份（数据库 + 上传文件压缩包）",
    "备份列表：查看所有备份文件，包含文件大小和创建时间",
    "恢复备份：选择备份文件恢复到指定时间点的数据状态（注意：恢复操作会覆盖当前数据）",
    "删除备份：删除不需要的旧备份文件",
]))
story.append(spacer(2 * mm))
story.append(note("重要提示：执行恢复操作前，建议先创建一个当前状态的新备份，以防恢复失败造成数据丢失。"
    "此外，Docker 部署中的 backup 服务会在每天凌晨 2:00 自动执行备份任务。"))

story.append(PageBreak())

# =========================== Chapter 15: AI 智能助手 ============================
story.append(h1("15. AI 智能助手"))
story.append(body("AI 智能助手模块提供六个智能化功能，所有功能默认运行在「规则引擎模式」，无需外部 API 即可使用。"
    "当配置了 AI API Key 后，系统自动升级到「AI 增强模式」，提供更精准的智能化体验。"))
story.append(spacer(3 * mm))
story.append(h3("15.1 AI 报价助手"))
story.append(body("通过自然语言描述需求，系统自动生成报价草案："))
story.append(bullet([
    "规则模式：基于关键词提取和规则匹配，从历史报价中查找相似案例",
    "AI 增强模式：调用 LLM 大语言模型，理解复杂需求描述，生成结构化的报价项目明细",
    "生成的报价草案可一键保存为正式报价单，进入报价管理流程",
    "大幅缩短报价响应时间，减少人工计算错误",
]))
story.append(h3("15.2 智能异常检测"))
story.append(body("系统自动扫描六大类业务异常，帮助管理者及时发现经营风险："))
story.append(_table(
    ["检测类别", "检测内容", "示例"],
    [
        ["金额异常", "报价/订单金额超出正常范围", "单笔订单金额 > 历史平均 3 倍"],
        ["价格异常", "售价低于成本或无利润", "报价单价 < 材质采购价"],
        ["进度异常", "任务超期未完成", "设计任务超过截止日期 7 天仍未提交"],
        ["客户风险", "客户欠款过高等信用风险", "客户欠款超过 10 万元或超过 90 天未回款"],
        ["库存异常", "库存不足或库存积压", "安全库存预警 / 3 个月无出库记录"],
        ["操作异常", "可疑操作行为", "短时间内频繁删除/修改数据"],
    ],
    col_widths=[3 * cm, 5 * cm, 8.5 * cm],
))
story.append(spacer(2 * mm))
story.append(h3("15.3 报价知识库"))
story.append(body("基于历史报价数据的智能检索系统："))
story.append(bullet([
    "按关键词、面积范围、材质类型等多维度搜索历史报价",
    "通过自然语言描述自动提取关键词并匹配相似报价",
    "辅助销售人员快速找到同类型项目的报价参考",
    "规则模式基于关键词提取，AI 模式基于语义理解",
]))
story.append(h3("15.4 智能经营报告"))
story.append(body("自动生成周期性的企业经营分析报告："))
story.append(bullet([
    "规则模式：基于模板引擎生成数据驱动的结构化报告",
    "AI 增强模式：LLM 撰写具有洞察分析的叙事性经营报告",
    "报告内容涵盖：销售概况、客户分析、利润分析、趋势研判、改进建议",
    "支持周报和月报两种周期",
]))
story.append(h3("15.5 现场照片识别"))
story.append(body("安装人员上传施工现场照片后，系统自动分析并生成检查清单结果："))
story.append(bullet([
    "规则模式：基于图像基本属性（尺寸、格式）进行校验",
    "AI 增强模式：调用视觉模型识别安装质量、安全隐患、尺寸偏差等",
    "支持多张照片批量上传与分析",
]))
story.append(h3("15.6 收款截图 OCR"))
story.append(body("上传银行转账或扫码支付截图，系统自动提取支付信息："))
story.append(bullet([
    "规则模式：基于文件格式和元数据校验",
    "AI 增强模式：OCR 识别收款金额、付款方、收款方、交易时间",
    "提取结果可一键关联到对应的订单和客户收款记录",
    "显示识别置信度，便于人工复核",
]))
story.append(spacer(3 * mm))
story.append(h3("15.7 AI 功能配置"))
story.append(body("AI 增强模式需要在 .env 文件中配置以下参数："))
story.append(code("AI_ENABLED=true\nAI_PROVIDER=anthropic\nAI_API_KEY=sk-ant-...\nAI_API_BASE_URL=\nAI_MODEL=claude-sonnet-4-20250514"))
story.append(spacer(2 * mm))
story.append(note("注意：不配置 AI_ENABLED 或将其设为 false 时，所有 AI 功能将以规则引擎模式运行，无需外部依赖。"
    "规则模式完全离线可用，适合内网环境。"))

story.append(PageBreak())

# =========================== Chapter 16: 角色与权限 ============================
story.append(h1("16. 角色与权限"))
story.append(body("系统内置七种角色，每个角色拥有不同的功能访问权限。管理员可根据实际需要，通过数据库或未来版本的用户管理界面进行角色分配。"))
story.append(spacer(3 * mm))
story.append(_table(
    ["角色", "标识", "核心权限范围"],
    [
        ["管理员", "admin", "全部功能 + 系统管理（备份、日志、删除操作）"],
        ["销售", "sales", "客户管理、报价管理、订单管理、报表查看"],
        ["设计师", "designer", "设计任务、产品库、材质库、工艺库（只读）"],
        ["制作人员", "production", "制作任务、外协管理、库存管理、材质/工艺（只读）"],
        ["安装人员", "installer", "安装任务、移动端安装页面"],
        ["财务", "finance", "收款、支出、欠款、对账、报表"],
        ["仓库管理员", "warehouse", "材质管理、库存管理"],
    ],
    col_widths=[2.5 * cm, 2 * cm, 12 * cm],
))
story.append(spacer(3 * mm))
story.append(h3("16.1 权限矩阵速查"))
story.append(_table(
    ["模块", "admin", "sales", "designer", "production", "installer", "finance", "warehouse"],
    [
        ["首页驾驶舱", "✓", "✓", "✓", "✓", "✓", "✓", "✓"],
        ["客户管理", "✓", "✓", "—", "—", "—", "—", "—"],
        ["报价管理", "✓", "✓", "—", "—", "—", "—", "—"],
        ["订单管理", "✓", "✓", "—", "—", "—", "—", "—"],
        ["产品/材质/工艺", "✓", "—", "✓", "✓", "—", "—", "✓"],
        ["设计任务", "✓", "—", "✓", "—", "—", "—", "—"],
        ["制作任务", "✓", "—", "—", "✓", "—", "—", "—"],
        ["安装任务", "✓", "—", "—", "—", "✓", "—", "—"],
        ["外协管理", "✓", "—", "—", "✓", "—", "—", "—"],
        ["库存管理", "✓", "—", "—", "✓", "—", "—", "✓"],
        ["财务管理", "✓", "—", "—", "—", "—", "✓", "—"],
        ["报表中心", "✓", "✓", "—", "—", "—", "✓", "—"],
        ["系统管理", "✓", "—", "—", "—", "—", "—", "—"],
        ["AI 智能助手", "✓", "✓", "—", "—", "—", "✓", "—"],
    ],
    col_widths=[3.5 * cm, 1.6 * cm, 1.6 * cm, 2 * cm, 2 * cm, 2 * cm, 1.8 * cm, 2 * cm],
))

story.append(PageBreak())

# =========================== Chapter 17: 典型业务流程 ============================
story.append(h1("17. 典型业务流程"))
story.append(body("以下展示一个标准的广告工程项目的完整业务流程："))
story.append(spacer(4 * mm))
story.append(_table(
    ["步骤", "操作", "角色", "系统操作说明"],
    [
        ["1", "客户询价", "销售", "客户管理 → 新建客户（如为新客户）"],
        ["2", "制作报价", "销售", "报价管理 → 新建报价 → 添加明细 → 自动计算 → 保存"],
        ["3", "客户确认", "销售", "报价管理 → 确认报价"],
        ["4", "转订单", "销售", "报价管理 → 转订单 → 生成订单"],
        ["5", "设计任务", "设计师", "任务管理 → 创建设计任务 → 完成设计 → 上传设计稿"],
        ["6", "制作排产", "制作人员", "任务管理 → 创建制作任务 → 制作看板追踪进度"],
        ["7", "外协加工（可选）", "制作人员", "外协管理 → 创建外协任务 → 派发供应商"],
        ["8", "安装施工", "安装人员", "任务管理 → 创建安装任务 → 移动端查看 → 完工拍照"],
        ["9", "验收交付", "销售/管理员", "订单管理 → 变更状态为已完成"],
        ["10", "收款登记", "财务", "财务管理 → 新建收款 → 关联订单 → 上传凭证"],
        ["11", "对账确认", "财务", "财务管理 → 新建对账单 → 确认对账"],
        ["12", "利润核算", "管理员/财务", "报表中心 → 查看日/月报 → 利润分析"],
    ],
    col_widths=[1.2 * cm, 2.8 * cm, 2.3 * cm, 10.2 * cm],
))
story.append(spacer(4 * mm))
story.append(note("提示：上述流程为典型场景，实际操作中可根据项目复杂度和公司流程灵活调整。"
    "例如，简单项目可能跳过设计环节直接制作；外协加工为可选环节。"))

story.append(PageBreak())

# =========================== Chapter 18: 常见问题（FAQ） ============================
story.append(h1("18. 常见问题（FAQ）"))
story.append(spacer(2 * mm))

faqs = [
    ("Q1: 忘记密码怎么办？",
     "联系系统管理员重置密码。管理员可通过数据库直接更新用户的密码哈希值。未来版本将支持自助密码重置功能。"),
    ("Q2: 如何添加新用户？",
     "当前版本通过 API 或数据库创建用户。使用管理员账户访问 /api/docs Swagger 文档页面，调用 POST /api/v1/users 接口创建。需要先准备好 bcrypt 加密的密码哈希值。"),
    ("Q3: Docker 服务启动失败怎么办？",
     "按以下顺序排查：\n"
     "① 检查端口冲突：确保 80、5432、6379、9000、9001 端口未被占用\n"
     "② 检查 docker compose ps 查看各容器状态\n"
     "③ 检查 docker compose logs <service-name> 查看具体错误日志\n"
     "④ 确认 .env 文件已正确配置（特别是 SECRET_KEY）\n"
     "⑤ 尝试 docker compose down -v && docker compose up -d 重新创建"),
    ("Q4: 如何备份数据？",
     "两种方式：\n"
     "① 自动备份：Docker 部署中包含 backup 服务，每天凌晨 2:00 自动备份到 ./backups 目录\n"
     "② 手动备份：管理员登录系统，进入「系统管理 → 备份管理」，点击「创建备份」\n"
     "③ 手动导出：使用 pg_dump 导出数据库，再打包 uploads 目录"),
    ("Q5: 如何恢复数据？",
     "管理员在「系统管理 → 备份管理」中选择备份文件，点击「恢复」。注意恢复操作会覆盖当前数据库和上传文件。\n\n"
     "建议恢复前先创建当前状态的新备份。"),
    ("Q6: AI 功能需要联网吗？",
     "规则引擎模式的 AI 功能完全离线可用，不需要联网。只有启用 AI 增强模式（AI_ENABLED=true）时才需要访问外部 AI API。"),
    ("Q7: 可以在外网访问吗？",
     "系统设计为局域网内部部署使用。如需外网访问，建议通过 VPN 或配置 HTTPS 反向代理，并确保所有默认密码已修改。"
     "外网暴露存在安全风险，请务必配置好防火墙和 HTTPS 证书。"),
    ("Q8: 支持哪些浏览器？",
     "推荐使用最新版 Chrome、Edge 或 Safari。最低支持 Chrome 90+、Edge 90+、Safari 15+。不支持 IE 浏览器。"),
    ("Q9: 数据存储在哪里？",
     "业务数据存储在 PostgreSQL 数据库中。上传的文件存储在本地 uploads 目录（或 MinIO 对象存储）。"
     "Docker 部署时，数据通过 Docker volume 持久化存储，即使容器重启也不会丢失。"),
    ("Q10: 如何升级系统？",
     "升级步骤：\n"
     "① git pull 获取最新代码\n"
     "② docker compose build 重新构建镜像\n"
     "③ docker compose up -d 重启服务\n"
     "④ docker compose exec backend alembic upgrade head 执行数据库迁移\n\n"
     "升级前建议先创建备份。"),
]

for q, a in faqs:
    story.append(h3(q))
    story.append(body(a))
    story.append(spacer(2 * mm))

# =========================== Appendix ============================
story.append(PageBreak())
story.append(h1("附录：系统信息"))
story.append(spacer(4 * mm))
story.append(_table(
    ["项目", "内容"],
    [
        ["系统名称", "AdCraft ERP"],
        ["中文名称", "广告制作安装工程管理系统"],
        ["当前版本", "1.0"],
        ["技术架构", "Vue 3 + FastAPI + PostgreSQL"],
        ["API 规范", "RESTful, OpenAPI 3.0"],
        ["API 文档", "http://<host>:8000/api/docs"],
        ["部署方式", "Docker Compose 多容器"],
        ["数据库", "PostgreSQL 16"],
        ["测试用例数", "366"],
        ["前端语言", "TypeScript (strict mode)"],
    ],
    col_widths=[5 * cm, 11.5 * cm],
))
story.append(spacer(8 * mm))
story.append(body("— 全文完 —"))
story.append(spacer(2 * mm))
story.append(note(f"本文档生成于 {datetime.now().strftime('%Y年%m月%d日')}。"
    "如有疑问或需要技术支持，请联系系统管理员或开发团队。"))

# ---------------------------------------------------------------------------
# Build PDF
# ---------------------------------------------------------------------------
OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "AdCraft_ERP_用户使用说明书.pdf",
)

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=20 * mm,
    rightMargin=20 * mm,
    topMargin=20 * mm,
    bottomMargin=20 * mm,
    title="AdCraft ERP 用户使用说明书",
    author="AdCraft ERP Team",
    subject="广告制作安装工程管理系统 使用说明书",
)

doc.addPageTemplates([cover_template, content_template])
doc.build(story)
print(f"✅ PDF 已生成: {OUTPUT}")
print(f"   文件大小: {os.path.getsize(OUTPUT) / 1024:.1f} KB")
