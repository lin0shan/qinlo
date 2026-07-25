; 个人商业助手 — NSIS 安装脚本
; 编译: makensis installer.nsi
; 支持：新装 + 覆盖升级（保护业务数据）

Unicode true
RequestExecutionLevel admin
SetCompress off
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ── 基本信息 ──────────────────────────────────
!define PRODUCT_NAME "个人商业助手"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "个人商业助手"
!define PRODUCT_WEB_SITE "http://localhost:8000"

Name "${PRODUCT_NAME} v${PRODUCT_VERSION}"
OutFile "build\${PRODUCT_NAME}_v${PRODUCT_VERSION}_setup.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "Software\${PRODUCT_NAME}" "InstallDir"

BrandingText "${PRODUCT_NAME} v${PRODUCT_VERSION}"

; ── 升级状态变量 ──────────────────────────────
Var IsUpgrade

; ── 安装程序初始化 ────────────────────────────
Function .onInit
    StrCpy $IsUpgrade "0"

    ; 检查注册表中是否记录过安装路径
    ReadRegStr $0 HKLM "Software\${PRODUCT_NAME}" "InstallDir"
    ${If} ${Errors}
        ; 注册表没有记录 → 全新安装
        Return
    ${EndIf}

    ; 检查实际目录和 exe 是否存在
    ${IfNot} ${FileExists} "$0\app\${PRODUCT_NAME}.exe"
        ; 注册表有记录但文件不在了 → 可能是残留，按全新安装处理
        Return
    ${EndIf}

    StrCpy $IsUpgrade "1"
    ; 已安装版本 → 使用注册表中的安装目录作为默认路径
    StrCpy $INSTDIR $0
FunctionEnd

; ── 界面设置 ──────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; -- 欢迎页（仅新装显示，升级跳过） --
!define MUI_PAGE_CUSTOMFUNCTION_PRE WelcomePre
!define MUI_WELCOMEPAGE_TITLE "欢迎安装 ${PRODUCT_NAME}"
!define MUI_WELCOMEPAGE_TEXT "本向导将引导您完成 ${PRODUCT_NAME} v${PRODUCT_VERSION} 的安装。$\r$\n$\r$\n${PRODUCT_NAME} 是美妆行业进销存 + 会员管理一体化工具，安装后即可使用。$\r$\n$\r$\n请关闭其他应用程序后再继续安装。"

; -- 安装完成页 --
!define MUI_FINISHPAGE_TITLE "安装完成"
!define MUI_FINISHPAGE_TEXT "${PRODUCT_NAME} 已成功安装。$\r$\n$\r$\n安装目录: $INSTDIR$\r$\n启动方式: 双击桌面快捷方式$\r$\n$\r$\n启动后系统托盘会出现图标，浏览器将自动打开。"
!define MUI_FINISHPAGE_LINK ""
!define MUI_FINISHPAGE_RUN "$INSTDIR\app\${PRODUCT_NAME}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "启动 ${PRODUCT_NAME}"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

; -- 卸载确认页 --
!define MUI_UNCONFIRMPAGE_TEXT_TOP "确认卸载 ${PRODUCT_NAME}？$\r$\n$\r$\n注意：卸载仅删除程序文件，业务数据（数据库、上传图片、日志）将被保留。"

; 插入页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

; ── 欢迎页预处理（升级时跳过欢迎页） ──────────
Function WelcomePre
    ${If} $IsUpgrade == "1"
        Abort  ; 跳过欢迎页，直接进入安装目录页
    ${EndIf}
FunctionEnd

; ── 安装区段 ──────────────────────────────────
Section "Install"
    ; ---- 第一步：检查并关闭正在运行的程序 ----
    ${If} $IsUpgrade == "1"
        DetailPrint "检测到已安装版本，正在停止运行中的程序..."
        nsExec::ExecToStack 'taskkill /f /im "${PRODUCT_NAME}.exe"'
        Pop $0
        Sleep 2000
    ${EndIf}

    ; ---- 第二步：覆盖/安装程序文件 ----
    ${If} $IsUpgrade == "1"
        DetailPrint "正在升级程序文件..."
        ; 删除旧版本的程序文件
        RMDir /r "$INSTDIR\app"
        RMDir /r "$INSTDIR\frontend"
    ${EndIf}

    ; 复制后端程序（PyInstaller 打包产物）
    SetOutPath "$INSTDIR\app"
    File /r "build\stage\app\*.*"

    ; 复制前端静态文件
    SetOutPath "$INSTDIR\frontend\dist"
    File /r "build\stage\frontend\dist\*.*"

    ; ---- 第三步：运行时目录（仅新装时创建） ----
    ${If} $IsUpgrade == "0"
        DetailPrint "正在创建运行时目录..."
        CreateDirectory "$INSTDIR\data"
        CreateDirectory "$INSTDIR\data\backups"
        CreateDirectory "$INSTDIR\uploads"
        CreateDirectory "$INSTDIR\logs"
    ${EndIf}

    ; ---- 第四步：注册表 ----
    WriteRegStr HKLM "Software\${PRODUCT_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayIcon" "$INSTDIR\app\${PRODUCT_NAME}.exe"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "NoRepair" 1
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; ---- 第五步：桌面快捷方式 ----
    SetOutPath "$INSTDIR\app"
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\app\${PRODUCT_NAME}.exe" "" \
        "$INSTDIR\app\${PRODUCT_NAME}.exe" 0

    ; ---- 完成提示 ----
    ${If} $IsUpgrade == "1"
        DetailPrint "升级完成！业务数据已保留。"
    ${EndIf}
SectionEnd

; ── 卸载区段（保留业务数据） ──────────────────
Section "Uninstall"
    ; 关闭正在运行的程序
    nsExec::ExecToStack 'taskkill /f /im "${PRODUCT_NAME}.exe"'
    Pop $0
    Sleep 2000

    ; 删除桌面快捷方式
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"

    ; 仅删除程序文件（保留业务数据目录：data/、uploads/、logs/、.env）
    RMDir /r "$INSTDIR\app"
    RMDir /r "$INSTDIR\frontend"

    ; 删除安装根目录的安装器残留
    Delete "$INSTDIR\uninstall.exe"

    ; 尝试删除安装目录（如果为空，即用户已手动移除数据目录）
    RMDir "$INSTDIR"

    ; 清理注册表
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
    DeleteRegKey HKLM "Software\${PRODUCT_NAME}"
SectionEnd
