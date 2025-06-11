#Requires AutoHotkey v2.0

#HotIf WinActive("ahk_class CabinetWClass") or WinActive("ahk_class ExploreWClass")

^+x::  ; Ctrl+Shift+X
{
    REPO_DIR := A_ScriptDir "\..\.."
    BIN_DIR := REPO_DIR "\.venv\Scripts"
    CLI := BIN_DIR "\quick-move.exe"
    ; "Hide" is needed to avoid showing a console window behind the app.
    Run('"' CLI '" --from-clipboard', , "Hide")
    ; PYTHON := BIN_DIR "\python.exe"
    ; Run('"' PYTHON '" -m quick_move --from-clipboard', , "Hide")

    A_TitleMatchMode := 3 ; Exact match
    ; The program runs but in the background, behind the file explorer window.
    ; Simply using WinActivate doesn't bring it to the front, it just makes the taskbar button flash.
    ; WinSetAlwaysOnTop makes it actually go on top (and stay on top), but sometimes errors without first using WinWait.
    WinWait("Quick Move", , 5)
    WinSetAlwaysOnTop(True, "Quick Move")
    WinActivate("Quick Move")
}

#HotIf

;--------------------------------------------------------
; AUTO RELOAD THIS SCRIPT on Ctrl+S
;--------------------------------------------------------
~^s:: {  ; Ctrl+S (passive, allowing other applications to handle it too)
    if WinActive(A_ScriptName) {
        SplashGui := MakeSplash("AHK Auto-Reload", "`n  Reloading " A_ScriptName "  `n")
        Sleep(500)
        SplashGui.Destroy()
        Reload
    }
}

MakeSplash(Title, Text) {
    SplashGui := Gui(, Title)
    SplashGui.Opt("+AlwaysOnTop +Disabled -SysMenu +Owner")  ; +Owner avoids a taskbar button.
    SplashGui.Add("Text", , Text)
    SplashGui.Show("NoActivate")  ; NoActivate avoids deactivating the currently active window.
    return SplashGui
}
